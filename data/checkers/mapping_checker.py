import boto3
import json
import re

# Подключение к S3
s3 = boto3.client(
    "s3",
    endpoint_url="https://s3.cloud.ru",
    region_name="ru-central-1",
    aws_access_key_id="<access_key>",
    aws_secret_access_key="<secret_key>"
)

# Define validation requirements for each section type
SECTION_VALIDATION = {
    "titular": {
        "required_elements": [ 
            "doc_type", "doc_name", "footer"
        ]
    },
    "report": {
        "required_elements": ["title", "info"]
    },
    "content": {
        "required_elements": ["title", "section"]
    },
    "intro": {
        "required_elements": ["title", "info"]
    },
    "definition": {
        "required_elements": ["title", "preamble", "elements"]
    },
    "abbreviation": {
        "required_elements": ["title", "preamble", "elements"]
    },
    "main": {
        "required_elements": ["section", "info"]
    },
    "outro": {
        "required_elements": ["title", "info"]
    },
    "source": {
        "required_elements": ["title", "elements"]
    },
    "application": {
        "required_elements": ["title", "info"]
    }
}

REQUIRED_SECTIONS = []  


def check_element_names(json_data, file_key):
    if not isinstance(json_data, list):
        print(f"File {file_key}: Ошибка структуры — ожидался список (array), но найден {type(json_data).__name__}.")
        return False
    
    valid_elements = list(SECTION_VALIDATION.keys())
    
    valid = True
    for i, item in enumerate(json_data):
        if not isinstance(item, dict):
            print(f"File {file_key}: Ошибка структуры элемента {i} — ожидался объект, но найден {type(item).__name__}.")
            valid = False
            continue
            
        if len(item.keys()) != 1:
            print(f"File {file_key}: Ошибка структуры элемента {i} — ожидается ровно один ключ, найдено {len(item.keys())}.")
            valid = False
            continue
            
        element_key = list(item.keys())[0]
        if element_key not in valid_elements:
            print(f"File {file_key}: Неизвестный элемент '{element_key}' в элементе {i}.")
            valid = False
    
    return valid


def validate_section_content(section_name, content, file_key):
    # First check that content is an array
    if not isinstance(content, list):
        print(f"File {file_key}: Ошибка структуры секции '{section_name}' — ожидался список, но найден {type(content).__name__}.")
        return False
    
    if section_name not in SECTION_VALIDATION:
        print(f"File {file_key}: Отсутствуют правила валидации для секции '{section_name}'.")
        return False
    
    validation_rules = SECTION_VALIDATION[section_name]
    required_elements = validation_rules["required_elements"]
    
    valid = True
    found_elements = set()
    
    def collect_elements(item, inside_table=False):
        if isinstance(item, dict):
            for key in item.keys():
                if key in required_elements:
                    found_elements.add(key)
                
                if key == "table":
                    table_content = item[key]
                    if isinstance(table_content, list):
                        for table_item in table_content:
                            collect_elements(table_item, True)
                else:
                    collect_elements(item[key], inside_table)
        elif isinstance(item, list):
            for sub_item in item:
                collect_elements(sub_item, inside_table)
    
    for item in content:
        collect_elements(item)
    
    missing = [elem for elem in required_elements if elem not in found_elements]
    if missing:
        print(f"File {file_key}: В секции '{section_name}' отсутствуют обязательные элементы: {', '.join(missing)}")
        valid = False
    
    for item in content:
        if not isinstance(item, dict):
            print(f"File {file_key}: Элемент в секции '{section_name}' не является объектом.")
            valid = False
            continue
            
        for element_key, element_value in item.items():
            if element_key == "table":
                continue
                
            valid_content = False
            
            if isinstance(element_value, dict) and any(k in ["text", "image", "table", "formula"] for k in element_value.keys()):
                valid_content = True
            
            elif isinstance(element_value, list):
                valid_items = True
                for content_item in element_value:
                    if isinstance(content_item, dict) and "table" in content_item:
                        pass
                    elif not (isinstance(content_item, dict) and 
                           any(k in ["text", "image", "table", "formula"] for k in content_item.keys())):
                        if not isinstance(content_item, list):  
                            valid_items = False
                
                valid_content = valid_items
            
            if not valid_content and element_key not in required_elements:
                print(f"File {file_key}: Элемент '{element_key}' в секции '{section_name}' имеет некорректную структуру.")
                valid = False
    
    return valid


def process_s3_files(bucket_name, prefix):
    valid_count = 0
    invalid_count = 0
    
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                file_key = obj['Key']
                
                if not file_key.lower().endswith('.json'):
                    continue
                
                try:
                    response = s3.get_object(Bucket=bucket_name, Key=file_key)
                    file_content = response['Body'].read().decode('utf-8')
                    
                    try:
                        json_data = json.loads(file_content)
                        
                        if not check_element_names(json_data, file_key):
                            invalid_count += 1
                            continue
                        
                        section_counts = {}
                        for item in json_data:
                            if isinstance(item, dict) and len(item) == 1:
                                section_name = list(item.keys())[0]
                                section_counts[section_name] = section_counts.get(section_name, 0) + 1
                        
                        duplicate_sections = [section for section, count in section_counts.items() if count > 1]
                        if duplicate_sections:
                            print(f"File {file_key}: Найдены повторяющиеся секции: {', '.join(duplicate_sections)}")
                            invalid_count += 1
                            continue
                        
                        valid_section = True
                        found_sections = set(section_counts.keys())
                        
                        for item in json_data:
                            section_name = list(item.keys())[0]
                            section_content = item[section_name]
                            if not validate_section_content(section_name, section_content, file_key):
                                valid_section = False
                        
                        if REQUIRED_SECTIONS:
                            missing_sections = [section for section in REQUIRED_SECTIONS if section not in found_sections]
                            if missing_sections:
                                print(f"File {file_key}: Отсутствуют обязательные секции: {', '.join(missing_sections)}")
                                valid_section = False
                        
                        if not valid_section:
                            invalid_count += 1
                            continue
                        
                        print(f"File {file_key}: Валиден.")
                        valid_count += 1
                        
                    except json.JSONDecodeError as err:
                        print(f"File {file_key}: Ошибка синтаксиса JSON — {err}")
                        invalid_count += 1
                
                except Exception as e:
                    print(f"Error processing file {file_key}: {str(e)}")
                    invalid_count += 1
    
    print(f"\nИтого: Валидных файлов: {valid_count}, Невалидных файлов: {invalid_count}")


if __name__ == "__main__":
    bucket_name = 'xyle-net'
    directory_prefix = 'mapped/'
    process_s3_files(bucket_name, directory_prefix)