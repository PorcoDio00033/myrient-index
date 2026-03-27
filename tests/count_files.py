import csv
import re
import json
from pathlib import Path

def count_files():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    data_dir = Path(config['general']['data_dir'])
    csv_file = data_dir / config['general']['csv_file']
    json_file = data_dir / config['general']['json_file']
    tree_file = data_dir / config['general']['tree_file']

    csv_count = 0
    csv_malformed = 0
    with open(csv_file, 'r', encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) >= 3:
                try:
                    size = int(row[2])
                    if size >= 0:
                        csv_count += 1
                except ValueError:
                    csv_malformed += 1
    print(f"CSV valid file count: {csv_count}, malformed: {csv_malformed}")

    json_count = 0
    json_regex = re.compile(r'"Size":(\d+)')
    with open(json_file, 'r', encoding='utf-8') as f:
        for line in f:
            if json_regex.search(line):
                json_count += 1
    print(f"JSON valid file count: {json_count}")

    tree_count = 0
    tree_regex = re.compile(r'\[\s*(\d+)\s+[A-Z][a-z]{2}\s+\d+\s+(?:\d{4}|\d{2}:\d{2})\s*\]')
    with open(tree_file, 'r', encoding='utf-8') as f:
        for line in f:
            if tree_regex.search(line):
                tree_count += 1
    print(f"Tree valid file count: {tree_count}")

if __name__ == '__main__':
    count_files()