from flask import Flask, request, jsonify, send_file
import os
import io
import tempfile
from werkzeug.utils import secure_filename
import traceback
import json
from gost_formatter import GostFormatter
from flask_cors import CORS

# Import all classes and functions from ml_classifier.py
try:
    # Import dependencies that might be needed
    import numpy as np
    import torch
    import torch.nn as nn
    import re
    import pickle
    
    # Import everything from ml_classifier using wildcard
    from ml_classifier import *
    ML_IMPORTS_OK = True
except ImportError as e:
    print(f"Failed to import from ml_classifier.py: {e}")
    ML_IMPORTS_OK = False

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/format', methods=['POST'])
def format_document():
    """
    Format a document according to GOST standards
    
    Request can be either:
    1. Form data with a file upload
    2. JSON with text content
    
    Parameters (form or JSON):
    - file: (form only) The text file to format
    - text: (JSON only) The text content to format
    - title: Document title
    - author: Author name
    - institution: Institution name
    - city: City
    - year: Year
    - use_ml: Whether to use ML for section detection (default: True)
    
    Returns:
    - The formatted DOCX file
    """
    try:
        # Determine request type
        is_form_data = request.content_type and 'multipart/form-data' in request.content_type
        is_json = request.content_type and 'application/json' in request.content_type
        
        # Get parameters based on request type
        if is_form_data:
            title = request.form.get('title', '')
            author = request.form.get('author', '')
            institution = request.form.get('institution', '')
            city = request.form.get('city', '')
            year = request.form.get('year', '')
            use_ml_str = request.form.get('use_ml', 'true')
            use_ml = use_ml_str.lower() == 'true' if use_ml_str else True
            
            # Check for file or text in form
            if 'file' in request.files and request.files['file'].filename:
                # Handle file upload
                file = request.files['file']
                
                if not allowed_file(file.filename):
                    return jsonify({'error': f'Invalid file. Only {", ".join(ALLOWED_EXTENSIONS)} files are allowed'}), 400
                    
                # Read the file content
                input_text = file.read().decode('utf-8')
            elif request.form.get('text'):
                # Get text from form
                input_text = request.form.get('text')
            else:
                return jsonify({'error': 'No file or text content provided'}), 400
        elif is_json:
            # Handle JSON request
            if not request.json:
                return jsonify({'error': 'Invalid JSON data'}), 400
                
            title = request.json.get('title', '')
            author = request.json.get('author', '')
            institution = request.json.get('institution', '')
            city = request.json.get('city', '')
            year = request.json.get('year', '')
            use_ml = request.json.get('use_ml', True)
            
            if 'text' not in request.json:
                return jsonify({'error': 'No text content provided'}), 400
                
            input_text = request.json['text']
        else:
            # For other content types (like plain form data)
            title = request.form.get('title', '') if request.form else ''
            author = request.form.get('author', '') if request.form else ''
            institution = request.form.get('institution', '') if request.form else ''
            city = request.form.get('city', '') if request.form else ''
            year = request.form.get('year', '') if request.form else ''
            use_ml = True
            
            # Try to get file
            if request.files and 'file' in request.files and request.files['file'].filename:
                file = request.files['file']
                
                if not allowed_file(file.filename):
                    return jsonify({'error': f'Invalid file. Only {", ".join(ALLOWED_EXTENSIONS)} files are allowed'}), 400
                    
                # Read the file content
                input_text = file.read().decode('utf-8')
            else:
                return jsonify({'error': 'No file or text content provided'}), 400
        
        # Create a temporary file for the output
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        # Format the document
        formatter = GostFormatter(use_ml=use_ml)
        
        try:
            output_path = formatter.create_gost_document(
                input_text, 
                output_path,
                title,
                author,
                institution,
                city,
                year
            )
            
            # Send the file
            output_filename = secure_filename(title if title else 'document') + '.docx'
            return send_file(
                output_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        except Exception as e:
            app.logger.error(f"Error formatting document: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if 'output_path' in locals() and os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except:
                pass

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'GOST Formatter API is running'})

@app.route('/api/info', methods=['GET'])
def api_info():
    """Get API information and documentation"""
    info = {
        'name': 'GOST Formatter API',
        'version': '1.0.0',
        'description': 'API for formatting text documents according to GOST standards',
        'endpoints': [
            {
                'path': '/api/format',
                'method': 'POST',
                'description': 'Format a document according to GOST standards',
                'parameters': [
                    {'name': 'file', 'in': 'formData', 'type': 'file', 'required': 'false', 'description': 'Text file to format'},
                    {'name': 'text', 'in': 'body', 'type': 'string', 'required': 'false', 'description': 'Text content to format'},
                    {'name': 'title', 'in': 'formData/body', 'type': 'string', 'required': 'false', 'description': 'Document title'},
                    {'name': 'author', 'in': 'formData/body', 'type': 'string', 'required': 'false', 'description': 'Author name'},
                    {'name': 'institution', 'in': 'formData/body', 'type': 'string', 'required': 'false', 'description': 'Institution name'},
                    {'name': 'city', 'in': 'formData/body', 'type': 'string', 'required': 'false', 'description': 'City'},
                    {'name': 'year', 'in': 'formData/body', 'type': 'string', 'required': 'false', 'description': 'Year'},
                    {'name': 'use_ml', 'in': 'formData/body', 'type': 'boolean', 'required': 'false', 'description': 'Whether to use ML for section detection'}
                ]
            },
            {
                'path': '/api/health',
                'method': 'GET',
                'description': 'Health check endpoint'
            },
            {
                'path': '/api/info',
                'method': 'GET',
                'description': 'Get API information and documentation'
            }
        ]
    }
    return jsonify(info)

@app.route('/', methods=['GET'])
def root():
    """Root endpoint redirects to API info"""
    return jsonify({
        'status': 'ok',
        'message': 'GOST Formatter API is running',
        'help': 'See /api/info for available endpoints'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 