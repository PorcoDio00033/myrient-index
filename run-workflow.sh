#!/bin/bash
set -e

echo "Starting Myrient Index Workflow at $(date)"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is not set."
    exit 1
fi

if [ -z "$GITHUB_REPO" ]; then
    echo "Error: GITHUB_REPO environment variable is not set. (e.g., user/repo)"
    exit 1
fi

# Set default repo for gh commands
export GH_REPO="$GITHUB_REPO"

# Work in the data directory
mkdir -p /app/data
cd /app/data

DATE=$(date +'%Y-%m-%d')
echo "Current date: $DATE"

# 1. Generate Index
echo "Generating Indexes..."
echo "Starting JSON..."
/app/scripts/generate_index.sh json
echo "JSON completed!"
sleep 5
echo "Starting CSV..."
/app/scripts/generate_index.sh csv
echo "CSV completed!"
sleep 5
echo "Starting UNIXTREE..."
/app/scripts/generate_index.sh txt
echo "UNIXTREE completed!"

# 2. Compress Artifacts
echo "Compressing Artifacts..."
# The script outputs to scrape/ directory
mv scrape "${DATE} scrape"
7z a -t7z -m0=lzma2 -mx=9 "${DATE} scrape.7z" "${DATE} scrape"

# 3. Create Release for Daily Index
echo "Creating GitHub Release for Daily Index..."
gh release create "index-${DATE}" "${DATE} scrape.7z" \
    --title "Myrient Index - ${DATE}" \
    --notes "Automated index generation for Myrient." || echo "Release might already exist, skipping creation."

# 4. Update Database
echo "Downloading existing DB..."
gh release download latest-db -p "myrient_index.7z" || echo "No existing DB found."
if [ -f "myrient_index.7z" ]; then
    7z x myrient_index.7z -y
fi

echo "Running import script..."
python /app/import_scrape.py

echo "Renaming new_files.txt..."
if [ -f "new_files.txt" ]; then
    mv new_files.txt "new_files_${DATE}.txt"
else
    touch "new_files_${DATE}.txt"
fi

echo "Compressing Database..."
7z a -t7z -m0=lzma2 -mx=9 myrient_index.7z myrient_index.db

echo "Updating latest-db Release..."
gh release upload latest-db myrient_index.7z "new_files_${DATE}.txt" --clobber || \
gh release create latest-db myrient_index.7z "new_files_${DATE}.txt" \
    --title "Unified Myrient Database" \
    --notes "Continuously updated SQLite database of Myrient files."

# Cleanup
echo "Cleaning up temporary files..."
rm -rf "${DATE} scrape" "${DATE} scrape.7z" myrient_index.7z "new_files_${DATE}.txt"

echo "Workflow completed successfully at $(date)"
