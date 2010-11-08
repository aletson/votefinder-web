from django.conf.urls.defaults import *
from django.contrib.auth import *

urlpatterns = patterns('',
    (r'^create/*$', 'votefinder.auth.views.create_step_1'),
    (r'^create/2/*$', 'votefinder.auth.views.create_step_2'),
    (r'^create/done/*$', 'votefinder.auth.views.create_step_3'),
    (r'^login/*$',   'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^logout/*$',  'django.contrib.auth.views.logout', {'template_name': 'logged_out.html'}),
    (r'^password_change/*$', 'django.contrib.auth.views.password_change', {'template_name': 'password_change_form.html'}),
    (r'^password_change/done/*$', 'django.contrib.auth.views.password_change_done', {'template_name': 'password_change_done.html'}),
)
