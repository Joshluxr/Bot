#!/bin/bash

# Upload files to tmpfiles.org
# Usage: ./upload_to_tmpfiles.sh <file_path>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <file_path>"
    echo ""
    echo "Available files to upload:"
    echo "  - bitcoin_results/* (individual analysis files)"
    echo "  - server2_candidates_backup.zip (3.2M)"
    echo "  - Create archive of all results first"
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "Error: File '$FILE' not found"
    exit 1
fi

echo "Uploading: $FILE"
echo "File size: $(du -h "$FILE" | cut -f1)"
echo ""

# Upload to tmpfiles.org
# API endpoint: https://tmpfiles.org/api/v1/upload
response=$(curl -F "file=@$FILE" https://tmpfiles.org/api/v1/upload 2>/dev/null)

echo "Response: $response"
echo ""

# Extract download URL from JSON response
if command -v jq &> /dev/null; then
    download_url=$(echo "$response" | jq -r '.data.url // empty')
    if [ -n "$download_url" ]; then
        echo "✓ Upload successful!"
        echo "Download URL: $download_url"
        echo ""
        echo "Note: tmpfiles.org URLs expire and have download limits"
        echo "      Change '/dl/' in URL to download directly"
    else
        echo "✗ Upload failed or invalid response"
    fi
else
    echo "Note: Install 'jq' for better output parsing"
    echo "Raw response above contains the download URL"
fi
