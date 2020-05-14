import random

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.context_processors import csrf
from votefinder.main.models import Player, UserProfile
from votefinder.vfauth.models import CreateUserForm


def create_step_1(request):
    profileKey = random.randint(10000000, 99999999)
    request.session['profileKey'] = profileKey
    return render(request, 'step1.html', {'profileKey': profileKey})


def create_step_2(request):
    key = request.session['profileKey']
    if not key:
        return HttpResponseRedirect('/auth/create')

    form = CreateUserForm()
    return render(request, 'step2.html', {'form': form})


def create_step_3(request):
    key = request.session['profileKey']
    if not key or request.method != 'POST':
        return HttpResponseRedirect('/auth/create')

    c = {}
    c.update(csrf(request))

    form = CreateUserForm(request.POST)
    form.required_key = key
    if form.is_valid():
        user = CreateUser(form.cleaned_data['login'], form.cleaned_data['email'], form.cleaned_data['password'],
                          form.userid)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        messages.add_message(request, messages.SUCCESS,
                             '<strong>Done!</strong> Your account was created and you are now logged in.')
        return HttpResponseRedirect('/')
    return render(request, 'step2.html', {'form': form})


def CreateUser(login, email, password, userid):
    u = User.objects.create_user(login, email, password)
    u.save()

    p, created = Player.objects.get_or_create(uid=userid, defaults={'name': login})

    profile = UserProfile(player=p, user=u)
    profile.save()

    return u
