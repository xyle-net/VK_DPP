import json
import pandas as pd
import boto3
from io import StringIO

S3_BUCKET_NAME = 'xyle-net'

s3_client = boto3.client(
    "s3",
    endpoint_url="https://s3.cloud.ru",
    region_name="ru-central-1",
    aws_access_key_id="<access_key>",
    aws_secret_access_key="<secret_key>"
)


def flatten_json(json_data: dict, doc_id: str):
    rows = []

    def _flatten(element, section_name, part_name=None):
        if isinstance(element, dict):
            for key, value in element.items():
                if key in ["text", "image", "table", "formula"]:
                    rows.append({
                        "document_id": doc_id,
                        "section_name": section_name,
                        "part_name": part_name,
                        "content_type": key,
                        "content_value": value
                    })
                else:
                    _flatten(value, section_name, key)
        elif isinstance(element, list):
            for item in element:
                _flatten(item, section_name, part_name)

    for section in json_data:
        for section_name, content in section.items():
            _flatten(content, section_name)

    return rows


def json_to_table(json_data: dict, doc_id: str):
    all_data = []
    rows = flatten_json(json_data, doc_id)
    all_data.extend(rows)
    df = pd.DataFrame(all_data)
    return df


def process_files_from_s3(input_prefix: str, output_prefix: str):
    all_dfs = []

    response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=input_prefix)
    if 'Contents' not in response:
        print(f"Файлы в директории {input_prefix} не найдены.")
        return

    for obj in response['Contents']:
        file_key = obj['Key']
        if not file_key.endswith('.json'):
            continue

        obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=file_key)
        json_data = json.loads(obj['Body'].read().decode('utf-8'))

        doc_id = file_key.split("/")[-1].split(".")[0]
        df = json_to_table(json_data, doc_id)
        all_dfs.append(df)

    final_df = pd.concat(all_dfs, ignore_index=True)

    csv_buffer = StringIO()
    final_df.to_csv(csv_buffer, index=False, encoding="utf-8")
    s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=f"{output_prefix}/mapping_dataset.csv", Body=csv_buffer.getvalue())

    print(f"Датасет сохранен в S3: {output_prefix}/mapping_dataset.csv")
    # print(final_df)


if __name__ == "__main__":
    input_prefix = "mapped"
    output_prefix = "data"
    process_files_from_s3(input_prefix, output_prefix)