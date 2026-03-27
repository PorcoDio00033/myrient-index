import re
import csv
import json
from pathlib import Path

def diagnose():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    data_dir = Path(config['general']['data_dir'])
    csv_file = data_dir / config['general']['csv_file']
    json_file = data_dir / config['general']['json_file']
    tree_file = data_dir / config['general']['tree_file']

    print("Diagnosing CSV...")
    csv_negatives = 0
    with open(csv_file, 'r', encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) >= 3:
                try:
                    size = int(row[2])
                    if size < 0:
                        csv_negatives += size
                except ValueError:
                    pass
    print(f"CSV Negative sizes sum: {csv_negatives}")

    print("Diagnosing JSON...")
    json_regex = re.compile(r'"Size":(\d+)')
    json_false_positives = 0
    json_dir_sizes = 0
    with open(json_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = json_regex.search(line)
            if match:
                regex_size = int(match.group(1))
                try:
                    data = json.loads(line)
                    actual_size = data.get('Size', 0)
                    if data.get('IsDir'):
                        if regex_size > 0:
                            json_dir_sizes += regex_size
                    elif actual_size != regex_size and actual_size >= 0:
                        json_false_positives += regex_size
                except:
                    pass
    print(f"JSON Regex false positives sum: {json_false_positives}")
    print(f"JSON Directory sizes sum: {json_dir_sizes}")

    print("Diagnosing Tree...")
    tree_regex = re.compile(r'\[\s*(\d+)\s+[A-Z][a-z]{2}\s+\d+\s+(?:\d{4}|\d{2}:\d{2})\s*\]')
    tree_false_positives = 0
    with open(tree_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = tree_regex.search(line)
            if match:
                name_match = re.search(r'"(.*)"$', line)
                if name_match and match.group(0) in name_match.group(1):
                    tree_false_positives += int(match.group(1))
    print(f"Tree Regex false positives sum: {tree_false_positives}")

if __name__ == '__main__':
    diagnose()