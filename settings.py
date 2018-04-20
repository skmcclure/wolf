#
# $Id$
#

# Put items in here if there is a chance that they might be modified in different installations
# that way the main application module doesn't accidentally get checked in with changes that
# could make the app break in different places.

# When you add an item, make the production value the default and add an example of possible
# alternate values when installed in a test environment.

# --- Begin Flask configuration ---

# the database is local
import os
SQLALCHEMY_DATABASE_URI = 'sqlite:////Users/smcclure/Projects/Wolf/wolf.db'
#DEBUG = False
# use this setting so that tracebacks show up in the web page or the httpd logs
DEBUG = True

PORT=9876

import os
#SECRET_KEY = os.urandom(16)
# when testing, use a static secret key so that sessions will live over restarts and the
# debugging can pick up right where it left off instead of logging in again and starting over
SECRET_KEY = 'development key'

#SESSION_TIMEOUT = 600
# during development, set the timeout to 0 so that the session will survive and not force you
# to login over and over
SESSION_TIMEOUT = 0

# --- End Flask configuration ---

# --- Begin application configuration ---

# logging configuration
LOG_LEVEL='ERROR'
LOG_FILE_PATH = 'error.log'

# --- End application configuration ---
