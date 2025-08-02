#!/usr/bin/env python3
"""
Background task to refresh the meta knowledge graph cache every hour.
This script should be run as a cron job or systemd service.
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
    """Handle shutdown signals gracefully"""
    print(f"[{datetime.now()}] Received signal {signum}, shutting down...")
    sys.exit(0)

def refresh_meta_kg():
    """Refresh the meta knowledge graph cache"""
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
    """Main function to run the background refresh task"""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"[{datetime.now()}] Starting meta knowledge graph background refresh service")
    
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