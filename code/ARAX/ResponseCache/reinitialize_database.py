#!/bin/env python3
# Reinitialize the Message/Feedback MySQL database

import os
import sys
import json
import ast

from response_cache import ResponseCache

if len(sys.argv) < 2:
    print("DANGER! Run reinitialize_database.pl with the parameter 'yes' if you really want to delete and re-create the Response database")
    sys.exit(0)

if sys.argv[1] != 'yes':
    print("If you really want to delete and re-create the feedback/Message database, use:")
    print("  python reinitialize_database.py yes")
    sys.exit(0)

#### Create an RTX Feedback management object
response_cache = ResponseCache()

#### Purge and re-create the database
response_cache.create_database()
response_cache.prepopulate_database()

#### Connect to the database
response_cache.connect()

