#!/bin/bash

# Create a compressed archive of all Bitcoin analysis results

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_NAME="bitcoin_analysis_results_${TIMESTAMP}.tar.gz"

echo "Creating archive: $ARCHIVE_NAME"
echo ""

cd /root/repo

# Create archive with bitcoin_results directory and key documentation
tar -czf "$ARCHIVE_NAME" \
    bitcoin_results/ \
    CHECKPOINT_AND_BLOOM_FILTER_DESIGN.md \
    GPU_SERVER_SETUP.md \
    OPTIMIZATION_PLAN.md \
    TECHNICAL_DOCUMENTATION.md \
    VANITYSEARCH_FORKS_COMPARISON.md \
    server2_candidates_backup.zip \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Archive created successfully!"
    echo ""
    echo "Archive: $ARCHIVE_NAME"
    echo "Size: $(du -h "$ARCHIVE_NAME" | cut -f1)"
    echo ""
    echo "Contents:"
    tar -tzf "$ARCHIVE_NAME" | head -20

    total_files=$(tar -tzf "$ARCHIVE_NAME" | wc -l)
    if [ $total_files -gt 20 ]; then
        echo "... and $((total_files - 20)) more files"
    fi

    echo ""
    echo "To upload to tmpfiles.org:"
    echo "  ./upload_to_tmpfiles.sh $ARCHIVE_NAME"
else
    echo "✗ Archive creation failed"
    exit 1
fi
