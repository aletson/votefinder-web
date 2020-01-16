# from django.contrib.auth import *
import django.contrib.auth.views
from django.conf.urls import *

import votefinder.vfauth.views

urlpatterns = [
    url(r'^create/*$', votefinder.vfauth.views.create_step_1),
    url(r'^create/2/*$', votefinder.vfauth.views.create_step_2),
    url(r'^create/done/*$', votefinder.vfauth.views.create_step_3),
    url(r'^login/*$', django.contrib.auth.views.LoginView, {'template_name': 'login.html'}),
    url(r'^logout/*$', django.contrib.auth.views.LogoutView.as_view(template_name='logged_out.html')),
    url(r'^password_change/*$', django.contrib.auth.views.PasswordChangeView,
        {'template_name': 'password_change_form.html', 'post_change_redirect': 'done/'}),
    url(r'^password_change/done/*$', django.contrib.auth.views.PasswordChangeDoneView,
        {'template_name': 'password_change_done.html'}),
    url(r'^password_reset/$',
        django.contrib.auth.views.PasswordResetView,
        {'post_reset_redirect': 'done/', 'template_name': 'password_reset_form.html'}),
    url(r'^password_reset/done/$',
        django.contrib.auth.views.PasswordResetDoneView, {'template_name': 'password_reset_done.html'}),
    url(r'^password_reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        django.contrib.auth.views.PasswordResetConfirmView,
        {'post_reset_redirect': '/auth/password_reset/complete/', 'template_name': 'password_reset_confirm.html'},
        name="password_reset_confirm"),
    url(r'^password_reset/complete/$',
        django.contrib.auth.views.PasswordResetCompleteView, {'template_name': 'password_reset_complete.html'}),
]
