import os
import argparse
import json
import re
import glob
import time
import sqlite3
from datetime import datetime
from tqdm import tqdm

def tqdm_file_wrapper(f, pbar):
    for line in f:
        pbar.update(len(line.encode('utf-8')))
        yield line

def parse_database(db_path):
    print(f"Querying database: {db_path}")
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        print(f"Error: Could not connect to database at {db_path}")
        return

    cur = con.cursor()

    # Get total count for progress bar
    cur.execute("SELECT COUNT(id) FROM files WHERE is_dir = 0")
    total_files = cur.fetchone()[0]

    cur.execute("SELECT path, size FROM files WHERE is_dir = 0")

    with tqdm(total=total_files, unit='files', desc=f"Parsing DB") as pbar:
        for path, size in cur:
            yield path, size
            pbar.update(1)

    con.close()

def parse_csv(filepath):
    file_size = os.path.getsize(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Parsing {os.path.basename(filepath)}") as pbar:
            for line in tqdm_file_wrapper(f, pbar):
                parts = line.strip().split(',', 3)
                if len(parts) == 4:
                    mime_type = parts[1]
                    try:
                        size = int(parts[2])
                    except ValueError:
                        size = 0
                    path = parts[3]
                    if mime_type != 'inode/directory':
                        path = path.strip('"')
                        if not path.startswith('/'):
                            path = '/' + path
                        yield path, size

def parse_json(filepath):
    file_size = os.path.getsize(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Parsing {os.path.basename(filepath)}") as pbar:
            for line in tqdm_file_wrapper(f, pbar):
                line = line.strip().rstrip(',')
                if line.startswith('{') and line.endswith('}'):
                    try:
                        obj = json.loads(line)
                        if not obj.get('IsDir', False):
                            path = obj.get('Path')
                            size = obj.get('Size', 0)
                            if path:
                                path = path.strip('"')
                                if not path.startswith('/'):
                                    path = '/' + path
                                yield path, size
                    except json.JSONDecodeError:
                        pass

def parse_txt(filepath):
    file_size = os.path.getsize(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Parsing {os.path.basename(filepath)}") as pbar:
            for line in tqdm_file_wrapper(f, pbar):
                # Extract bracket content to determine if it's a file or directory
                bracket_match = re.search(r'\[(.*?)\]', line)
                if bracket_match:
                    content = bracket_match.group(1).strip()
                    # Files have a date in the brackets (e.g., 'Dec 15 2025'), directories only have size
                    if re.search(r'[A-Za-z]', content):
                        size_match = re.match(r'^\s*(\d+)', content)
                        size = int(size_match.group(1)) if size_match else 0
                        
                        start_idx = line.find('"')
                        end_idx = line.rfind('"')
                        if start_idx != -1 and end_idx != -1 and start_idx != end_idx:
                            path = line[start_idx+1:end_idx].strip('"')
                            if not path.startswith('/'):
                                path = '/' + path
                            yield path, size

def get_files_in_dir(scrape_dir):
    for root, _, files in os.walk(scrape_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.csv', '.json', '.txt']:
                yield os.path.join(root, file)

def format_size(size_in_bytes):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PiB"

def matches_filters(path, dir_keywords, file_keywords, logic='AND', combine_logic='AND'):
    """
    Checks if a file path matches the specified directory and file filters.
    
    Args:
        path (str): The file path to check.
        dir_keywords (list): List of lowercase keywords for directory filtering.
        file_keywords (list): List of lowercase keywords for filename filtering.
        logic (str): 'AND' or 'OR' logic for multiple keywords within a filter.
        combine_logic (str): 'AND' or 'OR' logic to combine dir and file filters.
    """
    # Normalize path separators to forward slashes for consistent filtering
    normalized_path = path.replace('\\', '/')
    dirname, filename = os.path.split(normalized_path)
    dirname = dirname.lower()
    filename = filename.lower()
    
    has_dir_filter = bool(dir_keywords)
    has_file_filter = bool(file_keywords)
    
    dir_match = False
    if has_dir_filter:
        if logic == 'AND':
            dir_match = all(k in dirname for k in dir_keywords)
        else:
            dir_match = any(k in dirname for k in dir_keywords)
            
    file_match = False
    if has_file_filter:
        if logic == 'AND':
            file_match = all(k in filename for k in file_keywords)
        else:
            file_match = any(k in filename for k in file_keywords)
            
    if has_dir_filter and has_file_filter:
        if combine_logic == 'OR':
            return dir_match or file_match
        else:
            return dir_match and file_match
    elif has_dir_filter:
        return dir_match
    elif has_file_filter:
        return file_match
    else:
        return True

def main():
    start_time = time.time()
    print(f"Started at: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    
    parser = argparse.ArgumentParser(description="Generate a file list from scrape data.")
    parser.add_argument('--dir-filter', nargs='*', help="Keywords to filter directories")
    parser.add_argument('--file-filter', nargs='*', help="Keywords to filter file names")
    parser.add_argument('--logic', choices=['AND', 'OR'], default='AND', help="Logic for multiple keywords (default: AND)")
    parser.add_argument('--combine-logic', choices=['AND', 'OR'], default='AND', help="Logic to combine dir-filter and file-filter (default: AND)")
    parser.add_argument('--output', default='file.txt', help="Output file path (default: file.txt)")
    parser.add_argument('--scrape-dir', default='scrape', help="Directory containing source files (default: scrape)")
    parser.add_argument('--db-path', help="Path to the SQLite database file. If provided, --scrape-dir is ignored.")
    
    args = parser.parse_args()
    
    dir_keywords = [k.lower() for k in args.dir_filter] if args.dir_filter else []
    file_keywords = [k.lower() for k in args.file_filter] if args.file_filter else []
    
    existing_paths = set()
    
    # Read existing paths if the output file already exists to support appending/deduplication
    if os.path.exists(args.output):
        print(f"Reading existing paths from {args.output}...")
        with open(args.output, 'r', encoding='utf-8') as f:
            for line in f:
                path = line.strip()
                if path:
                    existing_paths.add(path)
        print(f"Loaded {len(existing_paths)} existing paths.")
        
    initial_existing_count = len(existing_paths)
    unique_new_paths = {}
    existing_paths_sizes = {}
    
    if args.db_path:
        if not os.path.exists(args.db_path):
            print(f"Error: Database file not found at '{args.db_path}'.")
            return
        
        for path, size in parse_database(args.db_path):
            if path in existing_paths:
                existing_paths_sizes[path] = size
            elif matches_filters(path, dir_keywords, file_keywords, args.logic, args.combine_logic):
                if path not in unique_new_paths:
                    unique_new_paths[path] = size if size is not None else 0
    else:
        scrape_dirs = glob.glob(args.scrape_dir)
        if not scrape_dirs:
            print(f"Error: No directories found matching '{args.scrape_dir}'.")
            return

        for s_dir in scrape_dirs:
            if not os.path.isdir(s_dir):
                continue
                
            print(f"Scanning directory: {s_dir}")
            
            for filepath in get_files_in_dir(s_dir):
                print(f"Processing: {filepath}")
                ext = os.path.splitext(filepath)[1].lower()
                
                parser_func = None
                if ext == '.csv':
                    parser_func = parse_csv
                elif ext == '.json':
                    parser_func = parse_json
                elif ext == '.txt':
                    parser_func = parse_txt
                    
                if parser_func:
                    for path, size in parser_func(filepath):
                        if path in existing_paths:
                            existing_paths_sizes[path] = size
                        elif matches_filters(path, dir_keywords, file_keywords, args.logic, args.combine_logic):
                            if path not in unique_new_paths:
                                unique_new_paths[path] = size
                                
    total_new_size = sum(unique_new_paths.values())
    total_existing_size = sum(existing_paths_sizes.values())
    total_size = total_new_size + total_existing_size
                    
    print(f"Found {len(unique_new_paths)} new matching files ({format_size(total_new_size)}).")
    
    if initial_existing_count > 0:
        missing_sizes = initial_existing_count - len(existing_paths_sizes)
        if missing_sizes > 0:
            print(f"Total size of all files in {args.output}: > {format_size(total_size)} (missing size info for {missing_sizes} older files)")
        else:
            print(f"Total size of all files in {args.output}: {format_size(total_size)}")
    else:
        print(f"Total size of all files in {args.output}: {format_size(total_new_size)}")
    
    with open(args.output, 'a', encoding='utf-8') as f:
        for path in sorted(unique_new_paths.keys()):
            f.write(f"{path}\n")
            
    print(f"Successfully appended {len(unique_new_paths)} paths to {args.output}")
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nFinished at: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
    
    hours, rem = divmod(total_time, 3600)
    minutes, seconds = divmod(rem, 60)
    print(f"Total execution time: {int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}")

if __name__ == '__main__':
    main()
