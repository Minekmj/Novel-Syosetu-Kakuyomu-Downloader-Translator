import os
import re

import src.site.base_data as base_data
import src.site.down as down

SPLIT_POINT = "+---+"

def extract_number(filename):
    match = re.search(r'(\d+)번', filename)
    return int(match.group(1)) if match else 9999

def process_text_line(line):
    cleaned = line.strip()
    cleaned = cleaned.replace('「', '“').replace('」', '”')
    return cleaned

def create_merged_txt(folder_path, output_txt_path, book_title, extract_number_fn=extract_number):
    if not os.path.exists(folder_path):
        return False

    all_files = os.listdir(folder_path)

    txt_files = [
        f for f in all_files
        if f.endswith('.txt') and not os.path.isdir(os.path.join(folder_path, f))
    ]

    sort_key = extract_number_fn if extract_number_fn else extract_number
    txt_files.sort(key=sort_key)

    if not txt_files:
        return False

    parts = book_title.split("|")

    main_title = parts[0].strip() if len(parts) > 0 else book_title
    sub_title = parts[1].strip() if len(parts) > 1 else ""

    delimiter = SPLIT_POINT

    if base_data.EXPORT_TEXT:
        with open(output_txt_path, "w", encoding="utf-8") as out_f:
            out_f.write(f"{main_title}\n")
            out_f.write(f"{sub_title}\n")
            out_f.write("(raw)\n")
            out_f.write(f"+---+\n{main_title} | {sub_title}\n\n")

            for file_name in txt_files:
                file_path = os.path.join(folder_path, file_name)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="cp949") as f:
                        lines = f.readlines()

                if not lines:
                    continue

                out_f.write(f"\n{'=' * 30}\n")
                subtitle = lines[0].strip()
                out_f.write(f"{subtitle}\n")
                out_f.write(f"{'=' * 30}\n\n")

                for line in lines[1:]:
                    if line:
                        processed_text = process_text_line(line)
                        if processed_text != '':
                            out_f.write(f"{processed_text}\n")
                        else:
                            out_f.write("\n")
                
                out_f.write("\n")
        return True

    with open(output_txt_path, "w", encoding="utf-8") as out_f:
        
        out_f.write(f"{main_title}\n")

        if sub_title:
            out_f.write(f"{sub_title}\n")

        
        for file_name in txt_files:
            file_path = os.path.join(folder_path, file_name)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="cp949") as f:
                    lines = f.readlines()

            if not lines:
                continue

            out_f.write(f"{delimiter}\n")

            
            subtitle = lines[0].strip()
            subtitle = subtitle.replace('「', '“').replace('」', '”')
            out_f.write(f"{subtitle}\n")

            
            for line in lines[1:]:
                stripped_line = line.strip()

                if not stripped_line:
                    continue

                clean_text = re.sub(r'<[^>]+>', '', stripped_line)

                if clean_text:
                    processed_text = process_text_line(clean_text)
                    out_f.write(f"{processed_text}\n")

    return True

down.set_base_data(base_data, create_merged_txt)
CheckTitle = down.CheckTitle
Download = down.Download
new_number = down.new_number