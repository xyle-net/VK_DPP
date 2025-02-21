import json
import pandas as pd
import sys


def flatten_json(json_data, doc_id):
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


def json_to_table(file_path):
    all_data = []
    doc_id = file_path.split("/")[-1].split(".")[0]
    
    with open(file_path, "r", encoding="utf-8") as file:
        json_data = json.load(file)
    
    rows = flatten_json(json_data, doc_id)
    all_data.extend(rows)
    
    df = pd.DataFrame(all_data)
    return df


if __name__ == "__main__":
    #if len(sys.argv) != 2:
    #    print("Использование: python script.py <путь_к_файлу>")
    #    sys.exit(1)
    
    #file_path = sys.argv[1]
    files = ['/content/diploma_4.json', '/content/diploma_5.json']
    all_dfs = []
    for file in files:
        df = json_to_table(file)
        all_dfs.append(df)
    
    # Объединяем все DataFrame в один
    final_df = pd.concat(all_dfs, ignore_index=True)
    #print(final_df)

    output_csv = "data_mapping.csv"
    final_df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Датасет сохранен в файл: {output_csv}")
