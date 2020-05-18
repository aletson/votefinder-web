from django.conf.urls import url
from django.contrib.auth import views as django_views
from votefinder.vfauth import views as auth_views

urlpatterns = [
    url(r'^create/*$', auth_views.give_user_profile_key),
    url(r'^create/2/*$', auth_views.get_votefinder_account_info),
    url(r'^create/done/*$', auth_views.validate_and_create_user),
    url(r'^login/*$', django_views.LoginView.as_view(template_name='login.html')),
    url(r'^logout/*$', django_views.LogoutView.as_view(template_name='logged_out.html')),
    url(r'^password_change/*$', django_views.PasswordChangeView.as_view(template_name='password_change_form.html', success_url='done/')),
    url(r'^password_change/done/*$', django_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html')),
    url(r'^password_reset/$',
        django_views.PasswordResetView.as_view(success_url='done/', template_name='password_reset_form.html')),
    url(r'^password_reset/done/$',
        django_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html')),
    url(r'^password_reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        django_views.PasswordResetConfirmView.as_view(success_url='/auth/password_reset/complete/', template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    url(r'^password_reset/complete/$',
        django_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html')),
]
