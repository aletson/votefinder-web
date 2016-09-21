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
    (r'^password_reset/$',
        'django.contrib.auth.views.password_reset',
        {'post_reset_redirect' : 'done/','template_name': 'password_reset_form.html'}),
    (r'^password_reset/done/$',
        'django.contrib.auth.views.password_reset_done', {'template_name': 'password_reset_done.html'}),
    (r'^password_reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'post_reset_redirect' : '/password_reset/complete/', 'template_name': 'password_reset_confirm.html'}),
    (r'^password_reset/complete/$',
        'django.contrib.auth.views.password_reset_complete', {'template_name': 'password_reset_complete.html'}),
)

