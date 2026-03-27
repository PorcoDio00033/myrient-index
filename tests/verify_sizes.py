import re
import csv
import json
from pathlib import Path

def get_files_csv(filepath):
    files = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        # format is tmsp: time, mimetype, size, path
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                try:
                    size = int(row[2])
                    # Ignore directories which have size -1
                    if size >= 0:
                        # Reconstruct path if it contained commas and was split
                        path = ",".join(row[3:]).lstrip('/')
                        files[path] = size
                except ValueError:
                    pass
    return files

def get_files_json(filepath):
    files = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.endswith(','):
                line = line[:-1]
            if line.startswith('{') and line.endswith('}'):
                try:
                    data = json.loads(line)
                    if not data.get('IsDir', False):
                        size = data.get('Size', 0)
                        if size >= 0:
                            path = data.get('Path', '').lstrip('/')
                            files[path] = size
                except:
                    pass
    return files

def get_files_tree(filepath):
    files = {}
    # Tree format: ├── [       1602 Dec 15  2025]  "file.txt"
    # Matches files by requiring a timestamp inside the brackets, and extract the path
    tree_pattern = re.compile(r'\[\s*(\d+)\s+[A-Z][a-z]{2}\s+\d+\s+(?:\d{4}|\d{2}:\d{2})\s*\]\s+"(.*)"$')
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            match = tree_pattern.search(line)
            if match:
                size = int(match.group(1))
                path = match.group(2).lstrip('/')
                files[path] = size
    return files

def bytes_to_tib(bytes_size):
    return bytes_size / (1024**4)

if __name__ == "__main__":
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    data_dir = Path(config['general']['data_dir'])
    csv_file = data_dir / config['general']['csv_file']
    json_file = data_dir / config['general']['json_file']
    tree_file = data_dir / config['general']['tree_file']

    print("Parsing files and calculating sizes (this might take a minute for massive files)...")
    
    csv_files = {}
    json_files = {}
    tree_files = {}
    
    try:
        csv_files = get_files_csv(csv_file)
        csv_size = sum(csv_files.values())
        print(f"CSV Total:  {bytes_to_tib(csv_size):.2f} TiB ({csv_size} bytes)")
    except FileNotFoundError:
        print("CSV Total:  File not found")
        csv_size = -1

    try:
        json_files = get_files_json(json_file)
        json_size = sum(json_files.values())
        print(f"JSON Total: {bytes_to_tib(json_size):.2f} TiB ({json_size} bytes)")
    except FileNotFoundError:
        print("JSON Total: File not found")
        json_size = -2

    try:
        tree_files = get_files_tree(tree_file)
        tree_size = sum(tree_files.values())
        print(f"Tree Total: {bytes_to_tib(tree_size):.2f} TiB ({tree_size} bytes)")
    except FileNotFoundError:
        print("Tree Total: File not found")
        tree_size = -3

    if csv_size == json_size == tree_size and csv_size > 0:
        print("\nSUCCESS: All three files report the exact same total size!")
    else:
        print("\nWARNING: Sizes do not match or files are missing!")
        print("\nAnalyzing mismatched files...")
        
        csv_set = set(csv_files.keys())
        json_set = set(json_files.keys())
        tree_set = set(tree_files.keys())
        
        missing_in_csv = (json_set | tree_set) - csv_set
        missing_in_json = (csv_set | tree_set) - json_set
        missing_in_tree = (csv_set | json_set) - tree_set
        
        if missing_in_csv:
            print(f"\nFiles missing in CSV: {len(missing_in_csv)}")
            for p in list(missing_in_csv):
                print(f"  - {p}")

        if missing_in_json:
            print(f"\nFiles missing in JSON: {len(missing_in_json)}")
            for p in list(missing_in_json):
                print(f"  - {p}")

        if missing_in_tree:
            print(f"\nFiles missing in Tree: {len(missing_in_tree)}")
            for p in list(missing_in_tree):
                print(f"  - {p}")