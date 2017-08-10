from django.conf.urls import *
from django.conf import settings

from django.contrib import admin
import votefinder.vfauth.urls
import votefinder.main.urls
import django.views.static
admin.autodiscover()

urlpatterns = [
    url(r'^auth/',     include(votefinder.vfauth.urls)),
    url(r'^admin/',    include(admin.site.urls)),
    url(r'',           include(votefinder.main.urls)),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', django.views.static.serve, {'document_root': settings.STATIC_ROOT}),
    ]
