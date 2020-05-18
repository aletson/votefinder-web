import random

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.context_processors import csrf
from votefinder.main.models import Player, UserProfile
from votefinder.vfauth.models import CreateUserForm


def give_user_profile_key(request):
    profile_key = random.randint(10000000, 99999999)  # noqa: S311
    request.session['profileKey'] = profile_key
    return render(request, 'step1.html', {'profileKey': profile_key})


def get_votefinder_account_info(request):
    key = request.session['profileKey']
    if not key:
        return HttpResponseRedirect('/auth/create')

    form = CreateUserForm()
    return render(request, 'step2.html', {'form': form})


def validate_and_create_user(request):
    key = request.session['profileKey']
    if not key or request.method != 'POST':
        return HttpResponseRedirect('/auth/create')

    csrf_resp = {}
    csrf_resp.update(csrf(request))

    form = CreateUserForm(request.POST)
    form.required_key = key
    if form.is_valid():
        user = create_user(form.cleaned_data['login'], form.cleaned_data['email'], form.cleaned_data['password'],
                           form.userid)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        messages.add_message(request, messages.SUCCESS,
                             '<strong>Done!</strong> Your account was created and you are now logged in.')
        return HttpResponseRedirect('/')
    return render(request, 'step2.html', {'form': form})


def create_user(login, email, password, userid):
    user = User.objects.create_user(login, email, password)
    user.save()

    player, created = Player.objects.get_or_create(uid=userid, defaults={'name': login})

    profile = UserProfile(player=player, user=user)
    profile.save()

    return user
