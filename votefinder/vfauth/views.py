import random

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.context_processors import csrf
from votefinder.main.models import Player, UserProfile
from votefinder.vfauth.models import CreateUserForm, LinkProfileForm


def give_user_profile_key(request):
    profile_key = random.randint(10000000, 99999999)  # noqa: S311
    request.session['profileKey'] = profile_key
    return render(request, 'step1.html', {'profileKey': profile_key})


def create_votefinder_account(request):
    form = CreateUserForm()
    return render(request, 'create_user_form.html', {'form': form})


@login_required
def link_profile(request):
    key = request.session['profileKey']
    if not key:
        return HttpResponseRedirect('auth/link_profile')
    form = LinkProfileForm()
    return render(request, 'link_profile_form.html', {'form': form})


def create_user(login, email, password, userid):
    user = User.objects.create_user(login, email, password)
    user.save()
    return user


def validate_and_create_user(request):
    if request.method != 'POST':
        return HttpResponseRedirect('/auth/create')

    csrf_resp = {}
    csrf_resp.update(csrf(request))

    form = CreateUserForm(request.POST)

    if form.is_valid():
        user = create_user(form.cleaned_data['email'], form.cleaned_data['password'],
                           form.userid)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        player, created = Player.objects.get_or_create(defaults={'name': request.user.name})
        profile = UserProfile(player=player, user=request.user)
        profile.save()
        messages.add_message(request, messages.SUCCESS,
                             '<strong>Done!</strong> Your account was created and you are now logged in.')
        return HttpResponseRedirect('/')
    return render(request, 'create_user_form.html', {'form': form})


@login_required
def link_user_to_profile(request):
    key = request.session['profileKey']
    if not key or request.method != 'POST':
        return HttpResponseRedirect('/auth/link_profile')
    csrf_resp = {}
    csrf_resp.update(csrf(request))

    form = LinkProfileForm(request.POST)
    form.required_key = key
    if form.is_valid():
        player = request.user.profile.player
        if player is not None:
            if form.cleaned_data['home_forum'] == 'sa':
                player.sa_uid = form.userid
            elif form.cleaned_data['home_forum'] == 'bnr':
                player.bnr_uid = form.userid
            player.save()
        messages.add_message(request, messages.SUCCESS, '<strong>Done!</strong> Your forum profile was successfully linked.')
        return HttpResponseRedirect('/profile')
    return render(request, 'link_profile_form.html', {'form': form})
