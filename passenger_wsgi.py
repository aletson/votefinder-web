import sys, os

cwd = os.getcwd()
sys.path.insert(0, cwd + '/votefinder')

os.environ['DJANGO_SETTINGS_MODULE'] = "votefinder.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
