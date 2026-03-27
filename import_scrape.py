import os
import csv
import json
import re
import time
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import func, text
from tqdm import tqdm

DB_NAME = 'sqlite:///myrient_index.db'
BATCH_SIZE = 3000

class FileRecord(SQLModel, table=True):
    __tablename__ = "files"
    id: Optional[int] = Field(default=None, primary_key=True)
    path: str = Field(unique=True, index=True)
    name: Optional[str] = None
    is_dir: Optional[bool] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None
    mod_time: Optional[datetime] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = Field(default=None, index=True)
    source_file: Optional[str] = None

engine = create_engine(DB_NAME)

def init_db():
    SQLModel.metadata.create_all(engine)

def parse_date(date_str):
    if not date_str:
        return None
    try:
        if 'T' in date_str:
            date_str = re.sub(r'\.\d+Z$', '', date_str)
            date_str = date_str.replace('Z', '')
            return datetime.fromisoformat(date_str)
        else:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None

def normalize_path(path, is_dir):
    if not path.startswith('/'):
        path = '/' + path
    if is_dir and not path.endswith('/'):
        path = path + '/'
    return path

def extract_date_from_folder(folder_name):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', folder_name)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d')
    return datetime.now()

def tqdm_file_wrapper(f, pbar):
    for line in f:
        pbar.update(len(line.encode('utf-8')))
        yield line

def upsert_batch(session, batch):
    if not batch:
        return
    
    stmt = sqlite_insert(FileRecord).values(batch)
    
    update_dict = {
        "last_seen": stmt.excluded.last_seen,
        "source_file": stmt.excluded.source_file
    }
    
    for col in ["name", "is_dir", "mime_type", "size", "mod_time"]:
        update_dict[col] = func.coalesce(stmt.excluded[col], getattr(FileRecord, col))
        
    stmt = stmt.on_conflict_do_update(
        index_elements=['path'],
        set_=update_dict
    )
    session.exec(stmt)
    session.commit()

def process_csv(session, file_path, scrape_date, is_legacy):
    file_size = os.path.getsize(file_path)
    batch = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"  Processing CSV") as pbar:
            if is_legacy:
                for line in tqdm_file_wrapper(f, pbar):
                    line = line.rstrip('\n')
                    if not line:
                        continue
                    parts = line.split(',', 3)
                    if len(parts) == 4:
                        mod_time_str, mime_type, size_str, path = parts
                        try:
                            size = int(size_str)
                            if size == -1:
                                size = None
                        except ValueError:
                            size = None
                        
                        is_dir = (size is None or mime_type == 'inode/directory')
                        name = os.path.basename(path.rstrip('/'))
                        
                        batch.append({
                            "path": normalize_path(path, is_dir),
                            "name": name,
                            "is_dir": is_dir,
                            "mime_type": mime_type,
                            "size": size,
                            "mod_time": parse_date(mod_time_str),
                            "first_seen": scrape_date,
                            "last_seen": scrape_date,
                            "source_file": file_path
                        })
                        count += 1
                    
                    if len(batch) >= BATCH_SIZE:
                        upsert_batch(session, batch)
                        batch = []
            else:
                reader = csv.reader(tqdm_file_wrapper(f, pbar))
                for row in reader:
                    if not row:
                        continue
                    if len(row) >= 4:
                        mod_time_str, mime_type, size_str, path = row[0], row[1], row[2], row[3]
                        try:
                            size = int(size_str)
                            if size == -1:
                                size = None
                        except ValueError:
                            size = None
                            
                        is_dir = (size is None or mime_type == 'inode/directory')
                        name = os.path.basename(path.rstrip('/'))
                        
                        batch.append({
                            "path": normalize_path(path, is_dir),
                            "name": name,
                            "is_dir": is_dir,
                            "mime_type": mime_type,
                            "size": size,
                            "mod_time": parse_date(mod_time_str),
                            "first_seen": scrape_date,
                            "last_seen": scrape_date,
                            "source_file": file_path
                        })
                        count += 1
                    
                    if len(batch) >= BATCH_SIZE:
                        upsert_batch(session, batch)
                        batch = []
                    
    upsert_batch(session, batch)
    print(f"    Processed {count} records from CSV.")

def process_json(session, file_path, scrape_date):
    file_size = os.path.getsize(file_path)
    batch = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"  Processing JSON") as pbar:
            for line in tqdm_file_wrapper(f, pbar):
                line = line.strip()
                if line in ('[', ']', '[]'):
                    continue
                if line.endswith(','):
                    line = line[:-1]
                if not line:
                    continue
                
                try:
                    obj = json.loads(line)
                    path = obj.get('Path')
                    if not path:
                        continue
                    
                    is_dir = obj.get('IsDir', False)
                        
                    batch.append({
                        "path": normalize_path(path, is_dir),
                        "name": obj.get('Name'),
                        "is_dir": is_dir,
                        "mime_type": obj.get('MimeType'),
                        "size": None if obj.get('Size') in (-1, None) else obj.get('Size'),
                        "mod_time": parse_date(obj.get('ModTime')),
                        "first_seen": scrape_date,
                        "last_seen": scrape_date,
                        "source_file": file_path
                    })
                    count += 1
                    
                    if len(batch) >= BATCH_SIZE:
                        upsert_batch(session, batch)
                        batch = []
                except json.JSONDecodeError:
                    pass
                
    upsert_batch(session, batch)
    print(f"    Processed {count} records from JSON.")

def process_tree(session, file_path, scrape_date):
    file_size = os.path.getsize(file_path)
    batch = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"  Processing TREE") as pbar:
            for line in tqdm_file_wrapper(f, pbar):
                line = line.rstrip('\n')
                if not line or line == '.':
                    continue
                    
                match = re.search(r'\[\s*(\d+)(.*?)\]\s+"([^"]+)"$', line)
                if not match:
                    continue
                    
                size_str = match.group(1)
                date_str = match.group(2).strip()
                path = match.group(3)
                
                name = os.path.basename(path.rstrip('/'))
                is_dir = len(date_str) == 0
                
                try:
                    size = int(size_str)
                    if size == -1:
                        size = None
                except ValueError:
                    size = None
                
                batch.append({
                    "path": normalize_path(path, is_dir),
                    "name": name,
                    "is_dir": is_dir,
                    "size": size,
                    "first_seen": scrape_date,
                    "last_seen": scrape_date,
                    "source_file": file_path
                })
                count += 1
                
                if len(batch) >= BATCH_SIZE:
                    upsert_batch(session, batch)
                    batch = []
                
    upsert_batch(session, batch)
    print(f"    Processed {count} records from TREE.")

def main():
    start_time = time.time()
    print(f"Started at: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    
    init_db()
    
    folders = [f for f in os.listdir('.') if os.path.isdir(f) and f.endswith(' scrape')]
    folders.sort()
    
    print(f"Found {len(folders)} scrape folders: {folders}")
    
    latest_scrape_date = None
    
    with Session(engine) as session:
        for folder in folders:
            print(f"\nProcessing folder: {folder}")
            scrape_date = extract_date_from_folder(folder)
            latest_scrape_date = scrape_date
            
            csv_path = os.path.join(folder, 'myrient_index.csv')
            if os.path.exists(csv_path):
                is_legacy = '2026-03-02' in folder
                process_csv(session, csv_path, scrape_date, is_legacy)
            else:
                print(f"  CSV not found: {csv_path}")
                
            json_path = os.path.join(folder, 'myrient_index.json')
            if os.path.exists(json_path):
                process_json(session, json_path, scrape_date)
            else:
                print(f"  JSON not found: {json_path}")
                
            tree_path = os.path.join(folder, 'myrient_index_tree.txt')
            if os.path.exists(tree_path):
                process_tree(session, tree_path, scrape_date)
            else:
                print(f"  TREE not found: {tree_path}")

    print("\nDatabase import complete.")
    
    if latest_scrape_date:
        print(f"Exporting new files for date: {latest_scrape_date.strftime('%Y-%m-%d')}")
        with Session(engine) as session:
            new_files = session.exec(select(FileRecord.path).where(FileRecord.first_seen == latest_scrape_date)).all()
            with open('new_files.txt', 'w', encoding='utf-8') as f:
                for path in new_files:
                    f.write(f"{path}\n")
        print(f"Exported {len(new_files)} new files to new_files.txt")
    else:
        # Ensure the file exists so the GitHub Action doesn't fail
        with open('new_files.txt', 'w', encoding='utf-8') as f:
            pass
    
    print("Vacuuming database...")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM"))
    print("Vacuum complete.")
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nFinished at: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
    
    hours, rem = divmod(total_time, 3600)
    minutes, seconds = divmod(rem, 60)
    print(f"Total execution time: {int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}")

if __name__ == '__main__':
    main()
