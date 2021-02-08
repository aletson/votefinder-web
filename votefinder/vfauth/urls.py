from django.urls import path, re_path
from django.contrib.auth import views as django_views
from votefinder.vfauth import views as auth_views

urlpatterns = [
    path('link_profile', auth_views.give_user_profile_key),
    re_path(r'link_profile/2/*$', auth_views.link_profile),
    re_path(r'link_profile/done/*$', auth_views.link_user_to_profile),
    path('create', auth_views.create_votefinder_account),
    re_path(r'create/done/*$', auth_views.validate_and_create_user),
    path('login', django_views.LoginView.as_view(template_name='login.html')),
    path('logout', django_views.LogoutView.as_view(template_name='logged_out.html')),
    path('password_change', django_views.PasswordChangeView.as_view(template_name='password_change_form.html', success_url='done')),
    path('password_change/done', django_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html')),
    path('password_reset/',
         django_views.PasswordResetView.as_view(success_url='done/', template_name='password_reset_form.html')),
    path('password_reset/done',
         django_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html')),
    re_path(r'^password_reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
            django_views.PasswordResetConfirmView.as_view(success_url='/auth/password_reset/complete', template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset/complete',
         django_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html')),
]
