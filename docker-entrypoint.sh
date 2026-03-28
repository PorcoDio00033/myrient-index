#!/bin/bash
set -e

if [ "$1" = "run" ]; then
    echo "Running workflow manually..."
    exec /app/run-workflow.sh
fi

echo "Setting up cron schedule: $CRON_SCHEDULE"

# Setup cron job
# We need to pass environment variables to cron
env > /etc/environment
echo "$CRON_SCHEDULE root . /etc/environment; /app/run-workflow.sh >> /proc/1/fd/1 2>&1" > /etc/cron.d/myrient-cron
chmod 0644 /etc/cron.d/myrient-cron
crontab /etc/cron.d/myrient-cron

# Start cron in foreground
echo "Starting cron daemon..."
exec cron -f
