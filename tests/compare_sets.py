import csv
import json
import re
from pathlib import Path

def get_csv_files(filepath):
    files = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) >= 4:
                try:
                    size = int(row[2])
                    if size >= 0:
                        # Reconstruct the path if it was split by commas
                        path = ",".join(row[3:]).lstrip('/')
                        files[path] = size
                except ValueError:
                    pass
    return files

def get_json_files(filepath):
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

def get_tree_files(filepath):
    files = {}
    tree_regex = re.compile(r'\[\s*(\d+)\s+[A-Z][a-z]{2}\s+\d+\s+(?:\d{4}|\d{2}:\d{2})\s*\]\s+"(.*)"$')
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            match = tree_regex.search(line)
            if match:
                size = int(match.group(1))
                path = match.group(2).lstrip('/')
                files[path] = size
    return files

def compare():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    data_dir = Path(config['general']['data_dir'])
    csv_file = data_dir / config['general']['csv_file']
    json_file = data_dir / config['general']['json_file']
    tree_file = data_dir / config['general']['tree_file']

    print("Loading CSV...")
    csv_files = get_csv_files(csv_file)
    print(f"CSV loaded: {len(csv_files)} files")
    
    print("Loading JSON...")
    json_files = get_json_files(json_file)
    print(f"JSON loaded: {len(json_files)} files")
    
    print("Loading Tree...")
    tree_files = get_tree_files(tree_file)
    print(f"Tree loaded: {len(tree_files)} files")
    
    csv_set = set(csv_files.keys())
    json_set = set(json_files.keys())
    tree_set = set(tree_files.keys())
    
    print("\n--- JSON vs Tree ---")
    in_json_not_tree = json_set - tree_set
    print(f"Files in JSON but not in Tree: {len(in_json_not_tree)}")
    for p in list(in_json_not_tree)[:10]:
        print(f"  {p} (Size: {json_files[p]})")
        
    in_tree_not_json = tree_set - json_set
    print(f"Files in Tree but not in JSON: {len(in_tree_not_json)}")
    for p in list(in_tree_not_json)[:10]:
        print(f"  {p} (Size: {tree_files[p]})")

    print("\n--- Tree vs CSV ---")
    in_tree_not_csv = tree_set - csv_set
    print(f"Files in Tree but not in CSV: {len(in_tree_not_csv)}")
    for p in list(in_tree_not_csv)[:10]:
        print(f"  {p} (Size: {tree_files[p]})")
        
    in_csv_not_tree = csv_set - tree_set
    print(f"Files in CSV but not in Tree: {len(in_csv_not_tree)}")
    for p in list(in_csv_not_tree)[:10]:
        print(f"  {p} (Size: {csv_files[p]})")

    print("\n--- Size Differences for Common Files ---")
    common_files = csv_set & json_set & tree_set
    diff_count = 0
    for p in common_files:
        if not (csv_files[p] == json_files[p] == tree_files[p]):
            diff_count += 1
            if diff_count <= 10:
                print(f"  {p}: CSV={csv_files[p]}, JSON={json_files[p]}, Tree={tree_files[p]}")
    print(f"Total common files with size differences: {diff_count}")

if __name__ == '__main__':
    compare()