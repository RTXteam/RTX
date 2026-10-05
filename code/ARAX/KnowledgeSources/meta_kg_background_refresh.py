#!/usr/bin/env python3
"""
Meta Knowledge Graph Background Refresh Module

This module provides two modes of operation:

1. FUNCTION MODE (Primary use in ARAX):
   - The refresh_meta_kg() function is called by ARAXBackgroundTasker
   - No signal handling or main loop - managed by ARAXBackgroundTasker
   - Used in production ARAX deployments

2. STANDALONE MODE (Testing/Debugging):
   - The main() function runs as a standalone service
   - Includes signal handling and infinite loop
   - Useful for testing meta KG refresh independently
   - Can be run as: python meta_kg_background_refresh.py

USAGE:
- In ARAX: ARAXBackgroundTasker calls refresh_meta_kg() function
- Standalone: Run this script directly for testing/debugging
- Cron/Systemd: Can be configured as a standalone service
"""

import os
import sys
import time
import signal
from datetime import datetime

# Add the necessary paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")

from knowledge_source_metadata import KnowledgeSourceMetadata

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully - ONLY used in standalone mode"""
    print(f"[{datetime.now()}] Received signal {signum}, shutting down...")
    sys.exit(0)

def refresh_meta_kg():
    """
    Refresh the meta knowledge graph cache
    
    This function is the primary entry point used by ARAXBackgroundTasker.
    It performs a single refresh operation and returns success/failure.
    
    Returns:
        bool: True if refresh was successful, False otherwise
    """
    try:
        print(f"[{datetime.now()}] Starting meta knowledge graph refresh...")
        ksm = KnowledgeSourceMetadata()
        
        # Force refresh by clearing cache
        KnowledgeSourceMetadata.cached_meta_knowledge_graph = None
        KnowledgeSourceMetadata.cache_timestamp = None
        
        # Build the meta knowledge graph
        meta_kg = ksm.get_meta_knowledge_graph()
        
        if meta_kg:
            print(f"[{datetime.now()}] Successfully refreshed meta knowledge graph")
            print(f"[{datetime.now()}] Meta KG contains {len(meta_kg.get('edges', []))} edges and {len(meta_kg.get('nodes', {}))} node types")
            
            # Check if backup was created
            backup_dir = os.path.dirname(os.path.abspath(__file__))
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith("meta_kg_backup_") and f.endswith(".json")]
            if backup_files:
                latest_backup = sorted(backup_files, reverse=True)[0]
                print(f"[{datetime.now()}] Backup created: {latest_backup}")
        else:
            print(f"[{datetime.now()}] ERROR: Failed to refresh meta knowledge graph")
            return False
            
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: Exception during meta KG refresh: {e}")
        return False
    
    return True

def main():
    """
    Main function to run the background refresh task as a standalone service
    
    This function is ONLY used when running this module directly (standalone mode).
    It sets up signal handlers and runs an infinite loop with hourly refreshes.
    
    USAGE:
    - For testing: python meta_kg_background_refresh.py
    - For standalone deployment: Configure as systemd service or cron job
    
    NOTE: This function is NOT used by the main ARAX application, which uses
    ARAXBackgroundTasker to call refresh_meta_kg() function instead.
    """
    # Set up signal handler for SIGTERM (graceful shutdown)
    signal.signal(signal.SIGTERM, signal_handler)
    # Note: SIGINT is handled by KeyboardInterrupt exception in the main loop
    
    print(f"[{datetime.now()}] Starting meta knowledge graph background refresh service (STANDALONE MODE)")
    
    # Initial refresh
    if not refresh_meta_kg():
        print(f"[{datetime.now()}] Initial refresh failed, exiting")
        sys.exit(1)
    
    # Run refresh every hour
    while True:
        try:
            # Sleep for 1 hour
            time.sleep(3600)  # 3600 seconds = 1 hour
            
            # Refresh the cache
            refresh_meta_kg()
            
        except KeyboardInterrupt:
            print(f"[{datetime.now()}] Received keyboard interrupt, shutting down...")
            break
        except Exception as e:
            print(f"[{datetime.now()}] Unexpected error in main loop: {e}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main() 