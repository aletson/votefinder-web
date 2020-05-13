# Django settings for votefinder project.

import os

# Import sensitive data from envvars
VF_MYSQL_HOST = os.environ.get('VF_MYSQL_HOST') or 'MySQL database server'
VF_MYSQL_USER = os.environ.get('VF_MYSQL_USER') or 'MySQL database user'
VF_MYSQL_PASS = os.environ.get('VF_MYSQL_PASS') or 'MySQL database password'
VF_MYSQL_NAME = os.environ.get('VF_MYSQL_NAME') or 'MySQL database name'
VF_SA_USER = os.environ.get('VF_SA_USER') or 'SA forums account name'
VF_SA_PASS = os.environ.get('VF_SA_PASS') or 'SA forums account password'
VF_EMAIL_HOST = os.environ.get('VF_EMAIL_HOST') or 'Email server'
VF_EMAIL_USER = os.environ.get('VF_EMAIL_USER') or 'Email user'
VF_EMAIL_PASS = os.environ.get('VF_EMAIL_PASS') or 'Email password'
VF_DOMAINS = os.environ.get('VF_DOMAINS') or '127.0.0.1 localhost'
VF_FROM_EMAIL = os.environ.get('VF_FROM_EMAIL') or 'reset@votefinder.org'
VF_ADMIN_NAME = os.environ.get('VF_ADMIN_NAME') or 'Your Name'
VF_ADMIN_EMAIL = os.environ.get('VF_ADMIN_EMAIL') or 'you@yourname.com'
VF_DEBUG_STR = os.environ.get('VF_DEBUG_STR') or False
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL') or ''
PRIMARY_DOMAIN = VF_DOMAINS.split(' ', 1)[0]

if VF_DEBUG_STR == 'True':
    DEBUG = True
else:
    DEBUG = False

ALLOWED_HOSTS = VF_DOMAINS.split()

ADMINS = (
    (VF_ADMIN_NAME, VF_ADMIN_EMAIL)
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': VF_MYSQL_NAME,
        'USER': VF_MYSQL_USER,
        'PASSWORD': VF_MYSQL_PASS,
        'HOST': VF_MYSQL_HOST,
        'PORT': 3306,
		'OPTIONS': {'charset': 'utf8mb4'},
    }
}

LOGIN_URL = '/auth/login'
LOGIN_REDIRECT_URL = '/'

SA_LOGIN = VF_SA_USER
SA_PASSWORD = VF_SA_PASS

EMAIL_HOST = VF_EMAIL_HOST
EMAIL_PORT = 25
EMAIL_HOST_USER = VF_EMAIL_USER
EMAIL_HOST_PASSWORD = VF_EMAIL_PASS
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = VF_FROM_EMAIL

WEB_ROOT = 'votefinder/'
REGULAR_FONT_PATH = 'votefinder/static/MyriadPro-Regular.otf'
BOLD_FONT_PATH =    'votefinder/static/MyriadPro-Bold.otf'
STATIC_ROOT = 'votefinder/static/'

# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York' # Set to the time zone set on the SA forums account.

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

# Absolute path to the directory that holds media. Example: "/home/media"
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
            'votefinder/main/templates'
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
                'django.template.context_processors.request',
            ],
        },
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher'
]

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
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
