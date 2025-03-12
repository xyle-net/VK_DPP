import pandas as pd
import boto3
from io import StringIO

s3_client = boto3.client(
    "s3",
    endpoint_url="https://s3.cloud.ru",
    region_name="ru-central-1",
    aws_access_key_id="<access_key>",
    aws_secret_access_key="<secret_key>"
)


def load_csv_from_s3(bucket_name, file_key):
    """
    Загружает CSV-файл из S3.
    """
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content = response['Body'].read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_content))
    return df


def check_dataset(df):
    """
    Проверяет датасет на пустые поля и корректность иерархии.
    """
    # Проверка на пустые поля
    if df.isnull().values.any():
        print("В датасете есть пустые поля.")
    else:
        print("Пустых полей в датасете нет.")

    # Проверка иерархии между section_name и part_name
    hierarchy = {
        'titular': ['department_name', 'organization_name', 'approver_info', 'doc_type', 'doc_name', 'worker_info', 'manager_info', 'footer'],
        'report': ['title', 'info'],
        'content': ['title', 'section', 'subsection'],
        'intro': ['title', 'info'],
        'definition': ['title', 'preamble', 'elements'],
        'abbreviation': ['title', 'preamble', 'elements'],
        'main': ['section', 'subsection', 'info'],
        'outro': ['title', 'info'],
        'source': ['title', 'elements'],
        'application': ['title', 'info']
    }

    incorrect_hierarchy = []

    for index, row in df.iterrows():
        section = row['section_name']
        part = row['part_name']
        document_id = row['document_id']  # Добавляем document_id
        
        if section in hierarchy:
            if part not in hierarchy[section]:
                incorrect_hierarchy.append((index, document_id, section, part))
        else:
            incorrect_hierarchy.append((index, document_id, section, part))

    if incorrect_hierarchy:
        print("Найдены некорректные иерархии:")
        for item in incorrect_hierarchy:
            print(f"Строка {item[0]}: {item[1]} => {item[2]} => {item[3]}")
    else:
        print("Все иерархии между section_name и part_name корректны.")


if __name__ == "__main__":
    bucket_name = "xyle-net"
    file_key = "data/mapping_dataset.csv"
    df = load_csv_from_s3(bucket_name, file_key)
    check_dataset(df)
