# from django.contrib.auth import *
import django.contrib.auth.views
from django.conf.urls import *

import votefinder.vfauth.views

urlpatterns = [
    url(r'^create/*$', votefinder.vfauth.views.create_step_1),
    url(r'^create/2/*$', votefinder.vfauth.views.create_step_2),
    url(r'^create/done/*$', votefinder.vfauth.views.create_step_3),
    url(r'^login/*$', django.contrib.auth.views.LoginView.as_view(template_name='login.html')),
    url(r'^logout/*$', django.contrib.auth.views.LogoutView.as_view(template_name='logged_out.html')),
    url(r'^password_change/*$', django.contrib.auth.views.PasswordChangeView.as_view(template_name='password_change_form.html', success_url='done/')),
    url(r'^password_change/done/*$', django.contrib.auth.views.PasswordChangeDoneView.as_view(template_name='password_change_done.html')),
    url(r'^password_reset/$',
        django.contrib.auth.views.PasswordResetView.as_view(success_url='done/', template_name='password_reset_form.html')),
    url(r'^password_reset/done/$',
        django.contrib.auth.views.PasswordResetDoneView.as_view(, {'template_name': 'password_reset_done.html')),
    url(r'^password_reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        django.contrib.auth.views.PasswordResetConfirmView.as_view(success_url='/auth/password_reset/complete/', template_name='password_reset_confirm.html')),
    url(r'^password_reset/complete/$',
        django.contrib.auth.views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html')),
]
