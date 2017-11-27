# votefinder-web
![Coverity Build Status](https://img.shields.io/coverity/scan/14207.svg)

SA web-based vote parser

## Installation

[Wiki](https://www.samafia.net/wiki/Votefinder)

## Usage
`pip install -r requirements.txt && python -Wall manage.py runserver`

You may also run using Passenger with the included `passenger_wsgi.py` (you will need to move `settings.py` into the `votefinder` directory.

Add `curl -s https://your.host/autoupdate` to your crontab.

