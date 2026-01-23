Server 2 K3 Search Backup - 20260123_223401
========================================

CURRENT SEARCH STATUS:
- 4 GPUs running BloomSearch32K3
- Each GPU has independent start position
- State files preserve exact current positions
- Total: ~463.86T keys searched (as of backup time)

FILES IN THIS BACKUP:
- launch_k3_4gpu.sh: Original launch script with start positions
- saved_positions.txt: Position record from Jan 21
- gpu*.state: Binary state files with EXACT current positions (33MB each)
- gpu*_search.log: Last 1000 lines of each GPU log
- running_processes.txt: Process info at backup time

TO RESUME THIS SEARCH:
1. Stop any new searches if needed
2. Restore state files: cp gpu*.state /tmp/
3. Run: ./launch_k3_4gpu.sh
4. Each GPU will resume from its saved state automatically

IMPORTANT:
The state files are the most critical - they contain the exact position.
Without them, search will restart from the positions in launch_k3_4gpu.sh
