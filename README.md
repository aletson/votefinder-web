# votefinder-web
SA web-based vote parser


# Usage
`pip install -r requirements.txt && python -Wall manage.py runserver`

Add `curl -s https://your.host/autoupdate` to your crontab.

# Troubleshooting
- If you get an error saying that `votefinder.settings could not be loaded`, you may need to move `manage.py` up a directory. YMMV.
- Works with passenger-wsgi if you'd rather.
