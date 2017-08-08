from django.conf.urls import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^auth/',     include('votefinder.vfauth.urls')),
    (r'^admin/',    include(admin.site.urls)),
    (r'',           include('votefinder.main.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
    )
