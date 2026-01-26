#!/bin/bash
# Deploy new search ranges to servers

SERVER1="root@5.161.93.179"
SERVER2="root@5.78.98.156"
SERVER3="root@173.180.134.131"
SERVER3_PORT="35952"

echo "=== Deploying New K3 Search Ranges ==="
echo ""

# Check which server to deploy to
if [ -z "$1" ]; then
    echo "Usage: $0 <server1|server2|server3> <range1|range2|range3|range4>"
    echo ""
    echo "Available ranges:"
    echo "  range1: 11494219...556744305000000000"
    echo "  range2: 11494219...506744305000000000"
    echo "  range3: 81979563...961496311613000000000"
    echo "  range4: 81979563...960496311613000000000"
    echo ""
    echo "Available servers:"
    echo "  server1: 5.161.93.179 (GPU search server)"
    echo "  server2: 5.78.98.156 (GPU search server)"
    echo "  server3: 173.180.134.131:35952 (New server)"
    echo ""
    echo "Example: $0 server3 range1"
    exit 1
fi

SERVER_NAME=$1
RANGE=$2

# Select server
if [ "$SERVER_NAME" == "server1" ]; then
    SERVER=$SERVER1
    SSH_OPTS=""
elif [ "$SERVER_NAME" == "server2" ]; then
    SERVER=$SERVER2
    SSH_OPTS=""
elif [ "$SERVER_NAME" == "server3" ]; then
    SERVER=$SERVER3
    SSH_OPTS="-p $SERVER3_PORT"
else
    echo "Error: Invalid server. Use 'server1', 'server2', or 'server3'"
    exit 1
fi

# Check range file exists
RANGE_CONFIG="/root/repo/new_ranges/${RANGE}_config.txt"
if [ ! -f "$RANGE_CONFIG" ]; then
    echo "Error: Range configuration not found: $RANGE_CONFIG"
    exit 1
fi

echo "Deploying $RANGE to $SERVER_NAME ($SERVER)..."
echo ""

# Create new K3 directory for this range
RANGE_DIR="K3_${RANGE}"
echo "1. Creating directory: $RANGE_DIR"
ssh $SSH_OPTS $SERVER "mkdir -p ~/$RANGE_DIR"

# Copy bloom filter from existing K3 directory
echo "2. Copying bloom filter..."
ssh $SSH_OPTS $SERVER "cp ~/K3/bloom.bin ~/$RANGE_DIR/ 2>/dev/null || echo 'Note: bloom.bin not found in K3, you may need to copy it manually'"

# Copy K3 executable
echo "3. Copying K3 executable..."
ssh $SSH_OPTS $SERVER "cp ~/K3/K3_OpenCL ~/$RANGE_DIR/"
ssh $SSH_OPTS $SERVER "chmod +x ~/$RANGE_DIR/K3_OpenCL"

# Upload new config
echo "4. Uploading range configuration..."
if [ -n "$SSH_OPTS" ]; then
    scp $SSH_OPTS "$RANGE_CONFIG" $SERVER:~/$RANGE_DIR/config.txt
else
    scp "$RANGE_CONFIG" $SERVER:~/$RANGE_DIR/config.txt
fi

# Create launch script
echo "5. Creating launch script..."
ssh $SSH_OPTS $SERVER "cat > ~/$RANGE_DIR/start_search.sh << 'EOFLAUNCH'
#!/bin/bash
cd ~/K3_${RANGE}
nohup ./K3_OpenCL > search.log 2>&1 &
echo \"K3 search started for ${RANGE}\"
echo \"PID: \\\$!\"
echo \"View logs: tail -f ~/K3_${RANGE}/search.log\"
EOFLAUNCH
"

ssh $SSH_OPTS $SERVER "chmod +x ~/$RANGE_DIR/start_search.sh"

echo ""
echo "=== Deployment Complete ==="
echo "Range deployed to: $SERVER:~/$RANGE_DIR"
echo ""
echo "To start the search:"
echo "  ssh $SERVER"
echo "  cd $RANGE_DIR"
echo "  ./start_search.sh"
echo ""
echo "To monitor:"
echo "  ssh $SERVER 'tail -f $RANGE_DIR/search.log'"
echo ""
