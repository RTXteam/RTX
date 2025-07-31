#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import inspect
import csv
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

from RTXConfiguration import RTXConfiguration


class KnowledgeSourceMetadata:

    #### Define a class variable to cache the meta_knowledge_graph between objects
    cached_meta_knowledge_graph = None
    cached_simplified_meta_knowledge_graph = None
    cache_timestamp = None
    cache_duration = timedelta(hours=1)  # Refresh every hour

    #### Constructor
    def __init__(self):
        self.predicates = None
        self.meta_knowledge_graph = KnowledgeSourceMetadata.cached_meta_knowledge_graph
        self.simplified_meta_knowledge_graph = KnowledgeSourceMetadata.cached_simplified_meta_knowledge_graph
        self.RTXConfig = RTXConfiguration()

    def _is_cache_valid(self) -> bool:
        """Check if the cached meta knowledge graph is still valid"""
        if (KnowledgeSourceMetadata.cached_meta_knowledge_graph is None or 
            KnowledgeSourceMetadata.cache_timestamp is None):
            return False
        
        return datetime.now() - KnowledgeSourceMetadata.cache_timestamp < self.cache_duration

    def _fetch_ploverdb_meta_kg(self) -> Optional[Dict[str, Any]]:
        """Fetch meta knowledge graph from PloverDB"""
        try:
            plover_url = getattr(self.RTXConfig, 'plover_url', "https://kg2cplover.rtx.ai:9990")
            response = requests.get(f"{plover_url}/meta_knowledge_graph", timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                eprint(f"ERROR: PloverDB returned status {response.status_code}")
                return None
        except Exception as e:
            eprint(f"ERROR: Failed to fetch from PloverDB: {e}")
            return None

    def _merge_kp_info(self, base_meta_kg: Dict[str, Any]) -> Dict[str, Any]:
        """Merge additional KP information from the KP info cacher"""
        try:
            # Import here to avoid circular dependencies
            sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery/Expand")
            from kp_info_cacher import KPInfoCacher
            
            kp_cacher = KPInfoCacher()
            if kp_cacher.cache_file_present():
                # Create a simple mock ARAXResponse for logging
                class MockARAXResponse:
                    def error(self, msg): eprint(f"ERROR: {msg}")
                    def debug(self, msg): eprint(f"DEBUG: {msg}")
                
                smart_api_info, meta_map = kp_cacher.load_kp_info_caches(MockARAXResponse())
                
                if meta_map:
                    eprint(f"Merging data from {len(meta_map)} knowledge providers")
                    
                    # Merge additional predicates from KP meta map
                    for kp_name, kp_data in meta_map.items():
                        if 'predicates' in kp_data:
                            for subject, objects in kp_data['predicates'].items():
                                for obj, predicates in objects.items():
                                    # Add new edges if they don't exist
                                    existing_predicates = set()
                                    
                                    # Check existing edges
                                    for edge in base_meta_kg.get('edges', []):
                                        if edge['subject'] == subject and edge['object'] == obj:
                                            existing_predicates.add(edge['predicate'])
                                    
                                    # Add new predicates
                                    for predicate in predicates:
                                        if predicate not in existing_predicates:
                                            new_edge = {
                                                "subject": subject,
                                                "object": obj,
                                                "predicate": predicate,
                                                "attributes": [
                                                    {
                                                        "attribute_type_id": "biolink:knowledge_source",
                                                        "value": kp_name,
                                                        "value_type_id": "biolink:InformationResource"
                                                    }
                                                ],
                                                "qualifiers": []
                                            }
                                            base_meta_kg['edges'].append(new_edge)
                    
                    # Merge additional node prefixes
                    for kp_name, kp_data in meta_map.items():
                        if 'prefixes' in kp_data:
                            for node_type, prefixes in kp_data['prefixes'].items():
                                if node_type in base_meta_kg.get('nodes', {}):
                                    existing_prefixes = set(base_meta_kg['nodes'][node_type].get('id_prefixes', []))
                                    new_prefixes = set(prefixes)
                                    base_meta_kg['nodes'][node_type]['id_prefixes'] = list(existing_prefixes | new_prefixes)
                                else:
                                    # Add new node type if it doesn't exist
                                    base_meta_kg.setdefault('nodes', {})[node_type] = {
                                        "id_prefixes": list(prefixes)
                                    }
                else:
                    eprint("No KP meta map data available for merging")
                                
        except Exception as e:
            eprint(f"WARNING: Failed to merge KP info: {e}")
        
        return base_meta_kg

    def _add_reasoner_api_info(self, meta_kg: Dict[str, Any]) -> Dict[str, Any]:
        """Add information from ReasonerAPI documentation"""
        # Add standard TRAPI attributes and qualifiers
        standard_attributes = [
            {
                "attribute_type_id": "biolink:original_predicate",
                "constraint_name": "kg2 ids",
                "constraint_use": True
            },
            {
                "attribute_type_id": "biolink:knowledge_level",
                "constraint_name": "knowledge level",
                "constraint_use": True
            },
            {
                "attribute_type_id": "biolink:agent_type",
                "constraint_name": "agent type",
                "constraint_use": True
            }
        ]
        
        # Add standard attributes to all edges if not present
        for edge in meta_kg.get('edges', []):
            if 'attributes' not in edge:
                edge['attributes'] = []
            
            # Add standard attributes if not already present
            existing_attr_types = {attr.get('attribute_type_id') for attr in edge['attributes']}
            for attr in standard_attributes:
                if attr['attribute_type_id'] not in existing_attr_types:
                    edge['attributes'].append(attr)
        
        return meta_kg

    def _get_backup_meta_kg_path(self) -> str:
        """Get the path for the backup meta knowledge graph file"""
        backup_dir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.now().strftime("%Y%m%d_%H")
        return os.path.join(backup_dir, f"meta_kg_backup_{timestamp}.json")

    def _save_backup_meta_kg(self, meta_kg: Dict[str, Any]) -> bool:
        """Save the meta knowledge graph as a backup file"""
        try:
            backup_path = self._get_backup_meta_kg_path()
            with open(backup_path, 'w') as f:
                json.dump(meta_kg, f, indent=2)
            eprint(f"Backup saved to: {backup_path}")
            
            # Clean up old backups (keep last 24 hours)
            self._cleanup_old_backups(keep_hours=24)
            
            return True
        except Exception as e:
            eprint(f"ERROR: Failed to save backup: {e}")
            return False

    def _cleanup_old_backups(self, keep_hours: int = 24):
        """Clean up old backup files, keeping only the last N hours"""
        try:
            backup_dir = os.path.dirname(os.path.abspath(__file__))
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith("meta_kg_backup_") and f.endswith(".json")]
            
            if len(backup_files) <= keep_hours:
                return  # Keep all if we have fewer than the limit
            
            # Sort by timestamp (oldest first)
            backup_files.sort()
            
            # Remove old files (keep the most recent ones)
            files_to_remove = backup_files[:-keep_hours]
            for old_file in files_to_remove:
                old_file_path = os.path.join(backup_dir, old_file)
                try:
                    os.remove(old_file_path)
                    eprint(f"Removed old backup: {old_file}")
                except Exception as e:
                    eprint(f"Failed to remove old backup {old_file}: {e}")
                    
        except Exception as e:
            eprint(f"ERROR: Failed to cleanup old backups: {e}")

    def _load_latest_backup_meta_kg(self) -> Optional[Dict[str, Any]]:
        """Load the most recent backup meta knowledge graph"""
        try:
            backup_dir = os.path.dirname(os.path.abspath(__file__))
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith("meta_kg_backup_") and f.endswith(".json")]
            
            if not backup_files:
                eprint("No backup files found")
                return None
            
            # Sort by timestamp (newest first)
            backup_files.sort(reverse=True)
            latest_backup = os.path.join(backup_dir, backup_files[0])
            
            with open(latest_backup, 'r') as f:
                backup_data = json.load(f)
            
            eprint(f"Loaded backup from: {latest_backup}")
            return backup_data
            
        except Exception as e:
            eprint(f"ERROR: Failed to load backup: {e}")
            return None

    def _build_dynamic_meta_kg(self) -> Optional[Dict[str, Any]]:
        """Build the meta knowledge graph dynamically from multiple sources"""
        eprint("Building dynamic meta knowledge graph...")
        
        # Step 1: Fetch from PloverDB
        plover_meta_kg = self._fetch_ploverdb_meta_kg()
        if not plover_meta_kg:
            eprint("WARNING: Failed to fetch meta knowledge graph from PloverDB, using backup")
            # Try to load from backup
            backup_meta_kg = self._load_latest_backup_meta_kg()
            if backup_meta_kg:
                eprint("Using backup meta knowledge graph")
                return backup_meta_kg
            eprint("ERROR: No backup available, cannot provide meta knowledge graph")
            return None
        
        # Step 2: Merge KP information
        merged_meta_kg = self._merge_kp_info(plover_meta_kg)
        
        # Step 3: Add ReasonerAPI information
        final_meta_kg = self._add_reasoner_api_info(merged_meta_kg)
        
        # Step 4: Save backup
        self._save_backup_meta_kg(final_meta_kg)
        
        # Step 5: Cache the result
        KnowledgeSourceMetadata.cached_meta_knowledge_graph = final_meta_kg
        KnowledgeSourceMetadata.cache_timestamp = datetime.now()
        
        eprint("Successfully built dynamic meta knowledge graph")
        return final_meta_kg

    #### Get a list of all supported subjects, predicates, and objects and reformat to /predicates format
    def get_kg_predicates(self):
        method_name = inspect.stack()[0][3]

        #### If we've already loaded the predicates, just return it
        if self.predicates is not None:
            return self.predicates

        # We always furnish KG2C results
        kg_prefix = 'KG2C'

        # Verify that the source data file exists
        input_filename = os.path.dirname(os.path.abspath(__file__)) + f"/{kg_prefix}_allowed_predicate_triples.csv"
        if not os.path.exists(input_filename):
            eprint(f"ERROR [{method_name}]: File '{input_filename}' not found")
            return None

        # Read the data and fill the predicates dict
        predicates = {}
        iline = 0
        with open(input_filename) as infile:
            rows = csv.reader(infile, delimiter=',', quotechar='"')
            for columns in rows:
                iline += 1

                # Ensure there are exactly 3 columns
                if len(columns) != 3:
                    eprint(f"ERROR [{method_name}]: input file {input_filename} line '{iline} does not have 3 columns")
                    continue

                subject_category = columns[0]
                predicate = columns[1]
                object_category = columns[2]

                if subject_category not in predicates:
                    predicates[subject_category] = {}

                if object_category not in predicates[subject_category]:
                    predicates[subject_category][object_category] = []

                predicates[subject_category][object_category].append(predicate)

        self.predicates = predicates

        return predicates

    #### Get a list of all supported subjects, predicates, and objects and return in /meta_knowledge_graph format
    def get_meta_knowledge_graph(self, format_='full'):
        method_name = inspect.stack()[0][3]

        # Check if we have a valid cached version
        if self._is_cache_valid():
            if format_ == 'simple':
                return self.simplified_meta_knowledge_graph
            else:
                return self.meta_knowledge_graph

        # Build the dynamic meta knowledge graph
        self.meta_knowledge_graph = self._build_dynamic_meta_kg()
        
        if self.meta_knowledge_graph is None:
            eprint(f"ERROR [{method_name}]: Failed to build meta knowledge graph and no backup available")
            return None
        
        # Create simplified version
        self.create_simplified_meta_knowledge_graph()
        KnowledgeSourceMetadata.cached_simplified_meta_knowledge_graph = self.simplified_meta_knowledge_graph
        
        if format_ == 'simple':
            return self.simplified_meta_knowledge_graph
        else:
            return self.meta_knowledge_graph

    #### Get a list of all supported subjects, predicates, and objects and return in /meta_knowledge_graph format
    def create_simplified_meta_knowledge_graph(self):
        method_name = inspect.stack()[0][3]

        self.simplified_meta_knowledge_graph = {
            'predicates_by_categories': {},
            'supported_predicates': {}
        }

        for edge in self.meta_knowledge_graph['edges']:
            if edge['subject'] not in self.simplified_meta_knowledge_graph['predicates_by_categories']:
                self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']] = {}
            if edge['object'] not in self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']]:
                self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']][edge['object']] = {}
            self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']][edge['object']][edge['predicate']] = True
            self.simplified_meta_knowledge_graph['supported_predicates'][edge['predicate']] = True

        for subject_category,subject_dict in self.simplified_meta_knowledge_graph['predicates_by_categories'].items():
            for object_category,object_dict in subject_dict.items():
                self.simplified_meta_knowledge_graph['predicates_by_categories'][subject_category][object_category] = sorted(list(object_dict))

        self.simplified_meta_knowledge_graph['supported_predicates'] = sorted(list(self.simplified_meta_knowledge_graph['supported_predicates']))


##########################################################################################
def main():

    ksm = KnowledgeSourceMetadata()
    #predicates = ksm.get_kg_predicates()
    #print(json.dumps(predicates,sort_keys=True,indent=2))

    meta_knowledge_graph = ksm.get_meta_knowledge_graph(format='simple')
    print(json.dumps(meta_knowledge_graph,sort_keys=True,indent=2))

if __name__ == "__main__": main()
