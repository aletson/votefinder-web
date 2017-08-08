# Django settings for votefinder project.

DEBUG = True 

import os

#VF_MYSQL_HOST = os.environ['VF_MYSQL_PORT_3306_TCP_ADDR'] or ''
#VF_MYSQL_PORT = os.environ['VF_MYSQL_PORT_3306_TCP_PORT'] or ''

ALLOWED_HOSTS = ['domain.com']

ADMINS = (
    ('Your Name', 'you@yourname.com')
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db_name',                      # Replace with your votefinder database
        'USER': 'db_user',                      # Replace with your votefinder user
        'PASSWORD': 'db_pass',                  # Replace with votefinder password
        'HOST': VF_MYSQL_HOST,                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': VF_MYSQL_PORT,                      # Set to empty string for default. Not used with sqlite3.
    }
}

LOGIN_URL = '/auth/login'
LOGIN_REDIRECT_URL = '/'

SA_LOGIN = 'Replace with the account name'
SA_PASSWORD = 'Replace with the account password'

if DEBUG:
        # These are defaults; change to reflect your settings
        EMAIL_HOST = 'localhost'
        EMAIL_PORT = 25
        EMAIL_HOST_USER = ''
        EMAIL_HOST_PASSWORD = ''
        EMAIL_USE_TLS = True
        DEFAULT_FROM_EMAIL = 'reset@votefinder.org'

WEB_ROOT = '/home/ubuntu/vf-app/app/votefinder/'
REGULAR_FONT_PATH = '/home/ubuntu/vf-app/app/votefinder/static/MyriadPro-Regular.otf'
BOLD_FONT_PATH =    '/home/ubuntu/vf-app/app/votefinder/static/MyriadPro-Bold.otf'
STATIC_ROOT = '/home/ubuntu/vf-app/app/votefinder/static/'
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# Site ID for this Django site. Properties of this site can be edited in
# the admin section.
SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://media.votefinder.org/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = 'http://media.votefinder.org/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'insert your secret key here'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            '/home/ubuntu/vf-app/app/votefinder/main/templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware'
)

ROOT_URLCONF = 'votefinder.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django_comments',
    'votefinder.main',
    'votefinder.vfauth',
)
