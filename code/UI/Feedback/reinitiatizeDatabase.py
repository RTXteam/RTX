#!/usr/bin/python3
# Some example test code for the RTX feedback system

import os
import sys
import json
import ast

from RTXFeedback import RTXFeedback

#### Create an RTX Feedback management object
rtxFeedback = RTXFeedback()

#### Purge and re-create the database
rtxFeedback.createDatabase()
rtxFeedback.prepopulateDatabase()

#### Connect to the database
rtxFeedback.connect()

