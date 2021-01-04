#!/bin/env python3
# Reinitialize the Message/Feedback MySQL database

import os
import sys
import json
import ast

from RTXFeedback import RTXFeedback

if len(sys.argv) < 2:
    print("Run reinitializeDatabase.pl with the parameter 'yes' if you really want to delete and re-create the feedback/Message database")
    sys.exit(0)

if sys.argv[1] != 'yes':
    print("If you really want to delete and re-create the feedback/Message database, use:")
    print("  python reinitializeDatabase.py yes")
    sys.exit(0)

#### Create an RTX Feedback management object
rtxFeedback = RTXFeedback()

#### Purge and re-create the database
rtxFeedback.createDatabase()
rtxFeedback.prepopulateDatabase()

#### Connect to the database
rtxFeedback.connect()

