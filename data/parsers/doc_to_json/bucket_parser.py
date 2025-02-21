import boto3
import os
import subprocess
import logging

S3_BUCKET = "xyle-net"
OLD_FOLDER = "raw/"
NEW_FOLDER = "parsered/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = boto3.client(
    "s3",
    endpoint_url="https://s3.cloud.ru",
    region_name="ru-central-1",
    aws_access_key_id="<access_key>",
    aws_secret_access_key="<secret_key>"
)


def list_files_in_s3_folder(bucket, folder):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=folder)
    return [obj["Key"] for obj in response.get("Contents", []) if obj["Key"] != folder and not obj["Key"].endswith("/")]


def download_file_from_s3(bucket, s3_path, local_path):
    try:
        s3.download_file(bucket, s3_path, local_path)
    except boto3.exceptions.S3UploadFailedError as e:
        logger.error(f"Ошибка загрузки файла {s3_path}: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при скачивании {s3_path}: {e}")


def upload_file_to_s3(bucket, local_path, s3_path):
    s3.upload_file(local_path, bucket, s3_path, ExtraArgs={'ContentType': 'application/json'})


def process_files():
    files = list_files_in_s3_folder(S3_BUCKET, OLD_FOLDER)
    
    if not files:
        logger.warning("Нет файлов для обработки.")
        return
    
    for file_key in files:
        if not file_key.lower().endswith(".docx"):
            continue  # Пропускаем файлы, которые не DOCX
        
        local_docx = os.path.basename(file_key)
        local_json = local_docx.replace(".docx", ".json")
        local_docx_path = f"/tmp/{local_docx}"
        local_json_path = f"/tmp/{local_json}"
        
        logger.info(f"Скачивание {file_key}...")
        download_file_from_s3(S3_BUCKET, file_key, local_docx_path)
        
        logger.info(f"Обработка {local_docx_path}...")
        subprocess.run(["python3", "parser.py", local_docx_path, local_json_path], check=True)
        
        new_s3_key = NEW_FOLDER + local_json
        logger.info(f"Загрузка {new_s3_key}...")
        upload_file_to_s3(S3_BUCKET, local_json_path, new_s3_key)
        
        if os.path.exists(local_docx_path):
            os.remove(local_docx_path)
        if os.path.exists(local_json_path):
            os.remove(local_json_path)
    
    logger.info("Обработка завершена.")


if __name__ == "__main__":
    process_files()
