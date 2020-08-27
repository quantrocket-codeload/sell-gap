# Crontab syntax cheat sheet
# .------------ minute (0 - 59)
# |   .---------- hour (0 - 23)
# |   |   .-------- day of month (1 - 31)
# |   |   |   .------ month (1 - 12) OR jan,feb,mar,apr ...
# |   |   |   |   .---- day of week (0 - 6) (Sunday=0 or 7)  OR sun,mon,tue,wed,thu,fri,sat
# |   |   |   |   |
# *   *   *   *   *   command to be executed

# ---------------
# DATA COLLECTION
# ---------------

# Collect usstock-1min each weekday morning
30 7 * * mon-fri quantrocket zipline ingest 'usstock-1min'

# -------
# TRADING
# -------

# Trade Zipline strategy at 9:29
29 9 * * mon-fri quantrocket master isopen 'XNYS' --in '10min' && quantrocket zipline trade 'sell-gap'

# -----------
# MAINTENANCE
# -----------

# drop old ticks from the real-time database (but preserve the aggregate database) to avoid
# filling up your disk
0 6 * * sun quantrocket realtime drop-ticks 'us-stk-tick' --older-than '30d'
