import zipfile
import xml.etree.ElementTree as ET
import json
import sys
import os
import shutil


def extract_relationships(zipf, rels_path):
    relationships = {}
    try:
        with zipf.open(rels_path) as rels_file:
            tree = ET.parse(rels_file)
            root = tree.getroot()
            for rel in root.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                rId = rel.get('Id')
                target = rel.get('Target')
                relationships[rId] = target
    except KeyError:
        print(f"Relationship file {rels_path} not found in the archive.")
    return relationships


def get_media_path(rel_target):
    return f"folder.zip/word/{rel_target}" if rel_target.startswith('media/') else rel_target


def parse_text(run):
    texts = []
    for node in run.iter():
        if node.tag.endswith('}t'):
            texts.append(node.text)
        elif node.tag.endswith('}br'):
            texts.append('\n')
    return ''.join(texts) if texts else ""


def parse_math_element_to_string(elem):
    """
    Convert the XML element of the math object to a string.
    """
    return ET.tostring(elem, encoding='unicode', method='xml')


def parse_formula(oMath):
    return parse_math_element_to_string(oMath)


def parse_cell(cell, namespaces, relationships):
    cell_content = []
    for paragraph in cell.findall('.//w:p', namespaces):
        para_content = []
        for run in paragraph.findall('.//w:r', namespaces):
            text = parse_text(run)
            if text:
                para_content.append({"text": text})
            
            drawing = run.find('.//w:drawing', namespaces)
            if drawing is not None:
                blip = drawing.find('.//a:blip', namespaces)
                if blip is not None:
                    rEmbed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    media_target = relationships.get(rEmbed, "")
                    image_path = get_media_path(media_target)
                    para_content.append({"image": image_path})
        
        oMath = paragraph.find('.//m:oMath', namespaces)
        if oMath is not None:
            formula_xml = parse_formula(oMath)
            para_content.append({"formula_xml": formula_xml})
        
        if para_content:
            cell_content.extend(para_content)
    
    return cell_content


def parse_table(tbl, namespaces, relationships):
    table = []
    for row in tbl.findall('.//w:tr', namespaces):
        current_row = []
        for cell in row.findall('.//w:tc', namespaces):
            cell_content = parse_cell(cell, namespaces, relationships)
            current_row.append(cell_content)
        table.append(current_row)
    return table


def get_localname(tag):
    return tag.split('}', 1)[-1] if '}' in tag else tag


def main(input_docx, output_json):
    temp_dir = 'temp_docx'
    with zipfile.ZipFile(input_docx, 'r') as zipf:
        zipf.extractall(temp_dir)

    with zipfile.ZipFile(input_docx) as zipf:
        # Извлекаем отношения для изображений
        rels_path = 'word/_rels/document.xml.rels'
        relationships = extract_relationships(zipf, rels_path)

        document_xml = 'word/document.xml'
        try:
            with zipf.open(document_xml) as doc_file:
                tree = ET.parse(doc_file)
                root = tree.getroot()
        except KeyError:
            print(f"{document_xml} not found in the archive.")
            return

    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
        'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'
    }

    json_structure = []

    body = root.find('w:body', namespaces)
    for child in body:
        tag = get_localname(child.tag)

        if tag == 'p':
            drawing = child.find('.//w:drawing', namespaces)
            oMath = child.find('.//m:oMath', namespaces)
            if drawing is not None:
                blip = drawing.find('.//a:blip', namespaces)
                if blip is not None:
                    rEmbed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    media_target = relationships.get(rEmbed, "")
                    image_path = get_media_path(media_target)
                    json_structure.append({
                        "image": image_path
                    })
            elif oMath is not None:
                formula_xml = parse_formula(oMath)
                json_structure.append({
                    "formula_xml": formula_xml
                })
            else:
                texts = []
                for run in child.findall('.//w:r', namespaces):
                    texts.append(parse_text(run))
                paragraph_text = ''.join(texts).strip()
                if paragraph_text:
                    json_structure.append({
                        "text": paragraph_text
                    })
        elif tag == 'tbl':
            table = parse_table(child, namespaces, relationships)
            json_structure.append({
                "table": table
            })

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(json_structure, f, ensure_ascii=False, indent=4)

    shutil.make_archive('folder', 'zip', temp_dir)
    shutil.rmtree(temp_dir)  # Удаление временной директории после создания архива

    #print(f"JSON успешно сохранен в {output_json}")
    #print(f"ZIP архив успешно сохранен как folder.zip")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python parser.py <input.docx> <output.json>")
    else:
        input_docx = sys.argv[1]
        output_json = sys.argv[2]
        if not os.path.isfile(input_docx):
            print(f"Файл {input_docx} не найден.")
        else:
            main(input_docx, output_json)
