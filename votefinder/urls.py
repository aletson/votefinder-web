from django.views import static
from django.conf import settings
from django.conf.urls import *
from django.contrib import admin

from votefinder.main import urls
from votefinder.vfauth import urls

admin.autodiscover()

urlpatterns = [
    url(r'^auth/', include(votefinder.vfauth.urls)),
    url(r'^admin/', admin.site.urls),
    url(r'', include(votefinder.main.urls)),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', django.views.static.serve, {'document_root': settings.STATIC_ROOT}),
    ]
