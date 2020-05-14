import os
import sys

from django.core.wsgi import get_wsgi_application

VENV = os.environ['ENVIRONMENT']
PYTHON_BIN = '{}/bin/python'.format(VENV)

if sys.executable != PYTHON_BIN:
    os.execl(PYTHON_BIN, PYTHON_BIN, *sys.argv)

cwd = os.getcwd()
sys.path.append(cwd)
sys.path.append(os.path.join(cwd, '/votefinder'))
sys.path.insert(0, '{v}/lib/python3.7/site-packages'.format(v=VENV))

os.environ['DJANGO_SETTINGS_MODULE'] = 'votefinder.settings'

application = get_wsgi_application()
