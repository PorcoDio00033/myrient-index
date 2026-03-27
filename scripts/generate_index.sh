#!/bin/sh
set -e

START_TIME=$(date +%s)
echo "Started at: $(date)"

FORMAT=$1

# Configure rclone
mkdir -p ~/.config/rclone
cat << EOF > ~/.config/rclone/rclone.conf
[myrient]
type = http
url = https://myrient.erista.me
EOF

mkdir -p scrape

case "$FORMAT" in
  json)
    echo "Generating JSON Index..."
    rclone lsjson "myrient:/" --fast-list --checkers 8 --metadata --recursive > scrape/myrient_index.json
    ;;
  csv)
    echo "Generating CSV Index..."
    rclone lsf "myrient:/" --fast-list --recursive --checkers 8 --format "tmsp" --separator "," --absolute --time-format max --csv > scrape/myrient_index.csv
    ;;
  txt)
    echo "Generating TXT Index..."
    rclone tree "myrient:/" --fast-list --checkers 8 --all --full-path --modtime --quote --size --output scrape/myrient_index_tree.txt
    ;;
  *)
    echo "Usage: $0 {json|csv|txt}"
    exit 1
    ;;
esac

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))
HOURS=$((TOTAL_TIME / 3600))
MINUTES=$(((TOTAL_TIME % 3600) / 60))
SECONDS=$((TOTAL_TIME % 60))

echo ""
echo "Finished at: $(date)"
printf "Total execution time: %02d:%02d:%02d\n" $HOURS $MINUTES $SECONDS
