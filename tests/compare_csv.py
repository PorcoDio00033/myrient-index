import csv
import sys
import json

def load_data(filepath, is_escaped=True):
    data = {}
    print(f"Loading {filepath} (escaped={is_escaped})...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if is_escaped:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 4:
                        date_time = row[0]
                        file_type = row[1]
                        size = row[2]
                        path = row[3]
                        data[path] = {'date': date_time, 'type': file_type, 'size': size}
            else:
                for line in f:
                    parts = line.rstrip('\n').split(',', 3)
                    if len(parts) == 4:
                        date_time, file_type, size, path = parts
                        data[path] = {'date': date_time, 'type': file_type, 'size': size}
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)
    print(f"Loaded {len(data)} unique paths.")
    return data

def main():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    file1 = config['compare_csv']['file1']
    file2 = config['compare_csv']['file2']

    data1 = load_data(file1, is_escaped=False)
    data2 = load_data(file2, is_escaped=True)

    paths1 = set(data1.keys())
    paths2 = set(data2.keys())

    only_in_1 = paths1 - paths2
    only_in_2 = paths2 - paths1
    common_paths = paths1.intersection(paths2)

    print("\n--- Comparison Results ---")
    print(f"Total paths in {file1}: {len(paths1)}")
    print(f"Total paths in {file2}: {len(paths2)}")
    print(f"Paths only in {file1} (Missing in new scrape): {len(only_in_1)}")
    print(f"Paths only in {file2} (New in new scrape): {len(only_in_2)}")

    if only_in_1:
        print(f"\nSample of paths only in {file1}:")
        for p in list(only_in_1)[:10]:
            print(f"  {p}")
            
    if only_in_2:
        print(f"\nSample of paths only in {file2}:")
        for p in list(only_in_2)[:10]:
            print(f"  {p}")

    print("\nChecking for differences in common files (size or date)...")
    differences = []
    for path in common_paths:
        d1 = data1[path]
        d2 = data2[path]
        if d1['size'] != d2['size'] or d1['date'] != d2['date']:
            differences.append((path, d1, d2))

    print(f"Files with different size or date: {len(differences)}")
    if differences:
        print("\nSample of modified files:")
        for path, d1, d2 in differences[:10]:
            print(f"  {path}:")
            if d1['size'] != d2['size']:
                print(f"    Size: {d1['size']} -> {d2['size']}")
            if d1['date'] != d2['date']:
                print(f"    Date: {d1['date']} -> {d2['date']}")

if __name__ == "__main__":
    main()
