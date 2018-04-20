#!/usr/bin/env python3

# Copyright (C) 2017, Racemi, All rights reserved.
#
# Creates the data base for the license application.
#
# $Id$
#

from wolf import db
import glob
import re
import os

# create the database
# drop_all doesn't work when there is data with relationships
db.drop_all()
db.session.commit()

db.create_all()

# save everything
db.session.commit()
