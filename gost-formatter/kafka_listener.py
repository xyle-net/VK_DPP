#!/usr/bin/env python3
import os
import json
import time
import requests
from kafka import KafkaConsumer, KafkaProducer
import io
import logging
from minio import Minio
from minio.error import S3Error
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
DOC_UPLOADED_TOPIC = 'doc-uploaded'
DOC_PROCESSING_TOPIC = 'doc-processing'
DOC_PROCESSED_TOPIC = 'doc-processed'

GOST_FORMATTER_API = os.getenv('GOST_FORMATTER_API', 'http://gost-formatter-api:5000/api/format')

# MinIO configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'ITdiakon')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'diakon-minio')
MINIO_RAW_BUCKET = 'raw-documents'
MINIO_FORMATTED_BUCKET = 'formatted-document'

def get_kafka_consumer():
    """Create and return a Kafka consumer"""
    for _ in range(10):
        try:
            consumer = KafkaConsumer(
                DOC_UPLOADED_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='gost-formatter-group',
                value_deserializer=lambda x: x.decode('utf-8')
            )
            return consumer
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            time.sleep(5)
    
    raise Exception("Failed to connect to Kafka after multiple attempts")

def get_kafka_producer():
    """Create and return a Kafka producer"""
    for _ in range(10):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda x: x.encode('utf-8')
            )
            return producer
        except Exception as e:
            logger.error(f"Failed to connect to Kafka producer: {e}")
            time.sleep(5)
    
    raise Exception("Failed to connect to Kafka producer after multiple attempts")

def get_minio_client():
    """Create and return a MinIO client"""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False  # Set to True if TLS is enabled
    )

def ensure_buckets_exist(minio_client):
    """Ensure that the required buckets exist in MinIO"""
    try:
        if not minio_client.bucket_exists(MINIO_RAW_BUCKET):
            minio_client.make_bucket(MINIO_RAW_BUCKET)
            logger.info(f"Created bucket: {MINIO_RAW_BUCKET}")
        
        if not minio_client.bucket_exists(MINIO_FORMATTED_BUCKET):
            minio_client.make_bucket(MINIO_FORMATTED_BUCKET)
            logger.info(f"Created bucket: {MINIO_FORMATTED_BUCKET}")
    except S3Error as e:
        logger.error(f"Error checking/creating buckets: {e}")
        raise

def process_document(doc_id, user_id, file_path):
    """Process the document using the GOST formatter API"""
    try:
        # Initialize MinIO client
        minio_client = get_minio_client()
        ensure_buckets_exist(minio_client)
        
        # Initialize Kafka producer
        producer = get_kafka_producer()
        
        # Notify that processing is starting
        producer.send(DOC_PROCESSING_TOPIC, doc_id)
        producer.flush()
        logger.info(f"Sent processing notification for document {doc_id}")
        
        # Create temporary file for downloaded document
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_input_file:
            input_path = temp_input_file.name
        
        # Download the document from MinIO
        try:
            minio_client.fget_object(
                MINIO_RAW_BUCKET, 
                file_path, 
                input_path
            )
            logger.info(f"Downloaded document {file_path} to {input_path}")
        except S3Error as e:
            logger.error(f"Error downloading document from MinIO: {e}")
            producer.send(DOC_PROCESSED_TOPIC, f"{doc_id}:ERROR")
            producer.flush()
            return
        
        # Read the document content
        with open(input_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
        
        # Create temporary file for formatted document
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_output_file:
            output_path = temp_output_file.name
        
        # Call the GOST formatter API
        try:
            # Get the original filename from the file path
            original_filename = file_path.split('/')[-1].replace(f"{user_id}_", "", 1)
            
            # Prepare data for the API call
            data = {
                'text': document_text,
                'title': original_filename.replace('.txt', ''),
                'author': user_id,
                'institution': 'Generated by GOST Formatter API',
                'city': 'Moscow',
                'year': '2024',
                'use_ml': True
            }
            
            # Make POST request to the API
            response = requests.post(
                GOST_FORMATTER_API,
                json=data,
                timeout=120  # Increase timeout for large documents
            )
            
            # Check response
            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                producer.send(DOC_PROCESSED_TOPIC, f"{doc_id}:ERROR")
                producer.flush()
                return
            
            # Save the response content to the output file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Formatted document saved to {output_path}")
            
            # Upload the formatted document to MinIO
            formatted_path = f"{user_id}/{user_id}_{original_filename.replace('.txt', '.docx')}"
            minio_client.fput_object(
                MINIO_FORMATTED_BUCKET, 
                formatted_path, 
                output_path
            )
            
            logger.info(f"Uploaded formatted document to MinIO at {formatted_path}")
            
            # Notify that processing is complete
            producer.send(DOC_PROCESSED_TOPIC, f"{doc_id}:SUCCESS")
            producer.flush()
            logger.info(f"Sent success notification for document {doc_id}")
            
        except Exception as e:
            logger.error(f"Error calling GOST formatter API: {e}")
            producer.send(DOC_PROCESSED_TOPIC, f"{doc_id}:ERROR")
            producer.flush()
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error processing document: {e}")

def main():
    """Main function to listen for Kafka messages and process documents"""
    logger.info("Starting GOST Formatter Kafka Listener")
    
    # Connect to Kafka
    consumer = get_kafka_consumer()
    logger.info("Connected to Kafka")
    
    # Process messages
    for message in consumer:
        try:
            logger.info(f"Received message: {message.value}")
            
            # Parse message
            parts = message.value.split(':')
            if len(parts) >= 3:
                doc_id = parts[0]
                user_id = parts[1]
                file_path = ':'.join(parts[2:])  # Join remaining parts in case filepath contains colons
                
                logger.info(f"Processing document: ID={doc_id}, User={user_id}, Path={file_path}")
                
                # Process the document
                process_document(doc_id, user_id, file_path)
            else:
                logger.warning(f"Invalid message format: {message.value}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

if __name__ == "__main__":
    main() 