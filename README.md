# Myrient File List Generator

A Python utility designed to parse file index data (CSV, JSON, TXT) from the Myrient HTTP server and generate a filtered list of file paths. This generated text file can then be fed directly into `rclone` to facilitate easy, targeted backups of specific files or directories.

## Features

- **Multiple Input Formats:** Parses index files in CSV, JSON, and TXT (Unix tree) formats.
- **SQLite Database Support:** Directly queries a SQLite database for significantly faster processing.
- **Advanced Filtering:** Filter files based on directory names (`--dir-filter`) and/or file names (`--file-filter`).
- **Flexible Logic:** Supports `AND` / `OR` logic for multiple keywords and for combining directory and file filters.
- **Deduplication & Appending:** Automatically deduplicates paths and can append to existing output files without adding duplicates.
- **Size Calculation:** Calculates and displays the total size of the newly matched files and the overall output list.

## Recommended Usage: SQLite Database

For the fastest and most efficient experience, it is **highly recommended** to use the pre-generated SQLite database. This method avoids the need for manual scraping and is a lot faster than parsing text-based index files.

1.  **Download the Database:** Go to the [**Releases**](https://github.com/PorcoDio00033/myrient-index/releases/tag/latest-db) page and download the `myrient_index.7z` file from the `latest-db` release.
2.  **Extract the Database:** Unzip the `myrient_index.db` file.
3.  **Install Deps**: `pip install -r requirements.txt`
3.  **Run the Script:** Use the `--db-path` argument to point to the database file.

```bash
python generate_file_list.py --db-path /path/to/myrient_index.db [OPTIONS]
```

## Alternative Usage: Manual Scraping

If you prefer to generate the index files yourself, you can use the following `rclone` commands.

### Prerequisites

- Python 3.x
- `rclone`

### Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--db-path` | Path to the SQLite database file. If provided, other input methods are ignored. | None |
| `--dir-filter` | One or more keywords to filter directories. | None |
| `--file-filter` | One or more keywords to filter file names. | None |
| `--logic` | Logic for multiple keywords within a filter (`AND` or `OR`). | `AND` |
| `--combine-logic` | Logic to combine `--dir-filter` and `--file-filter` (`AND` or `OR`). | `AND` |
| `--output` | Path to the output text file. | `file.txt` |
| `--scrape-dir` | Directory containing the source index files (CSV, JSON, TXT). Supports glob patterns. | `scrape` |

### Examples

**1. Extract all files containing "firmware" in the filename:**
```bash
python generate_file_list.py --file-filter "firmware" --output firmwares.txt
```

**2. Extract files from directories containing "bios" AND "xbox":**
```bash
python generate_file_list.py --dir-filter "bios" "xbox" --logic AND --output xbox_bios.txt
```

**3. Extract files containing "update" OR "dlc" from directories containing "ps3":**
```bash
python generate_file_list.py --dir-filter "ps3" --file-filter "update" "dlc" --logic OR --combine-logic AND --output ps3_updates_dlc.txt
```

## Rclone Integration

This tool is designed to work seamlessly with `rclone` index dumps.

### 1. Rclone Configuration

Create a `myrient` remote with the following command:
```bash
rclone config create myrient http url https://myrient.erista.me
```
**Important:** Ensure there is no trailing slash `/` at the end of the Myrient URL in your `rclone.conf`.
```ini
[myrient]
type = http
url = https://myrient.erista.me
```

### 2. Creating Indexes (Scraping)

> **Note:** Using the pre-generated **[SQLite database](https://github.com/PorcoDio00033/myrient-index/releases/tag/latest-db) is strongly recommended** over manual scraping.

Different scrape runs may contain slightly different files. This is due to the HTTP server changing or connection issues during the scrape. If you prefer not to scrape the server yourself, you can download pre-generated scrape files from the [**Releases**](https://github.com/PorcoDio00033/myrient-index/releases) section of this repository.

**JSON Format:**
```bash
rclone lsjson "myrient:/" --fast-list --checkers 16 --metadata --recursive > scrape/myrient_index.json
```

**CSV Format:**
```bash
rclone lsf "myrient:/" --fast-list --recursive --checkers 16 --format "tmsp" --separator "," --absolute --time-format max --csv > scrape/myrient_index.csv
```

**UNIXTREE (TXT) Format:**
```bash
rclone tree "myrient:/" --fast-list --checkers 16 --all --full-path --modtime --quote --size --output scrape/myrient_index_tree.txt
```

### 3. Downloading Files

Once you have generated your filtered text file (e.g., `dlc.txt`) using `generate_file_list.py`, you can feed it into `rclone` to download only those specific files.

**Example Download Command:**
```bash
rclone copy "myrient:" "remote:path/myrient-bkp" \
  --files-from-raw dlc.txt \
  --log-file myrient-dlc-full.log \
  --log-level NOTICE \
  -P \
  --tpslimit 12 \
  --tpslimit-burst 0 \
  --transfers 10 \
  --multi-thread-streams 0 \
  --no-traverse
```
*(Note: Adjust the destination `remote:path/myrient-bkp` to your preferred local or remote storage path.)*
