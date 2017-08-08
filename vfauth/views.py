from votefinder.main.models import *
from votefinder.vfauth.models import *
from django.shortcuts import render_to_response
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template import RequestContext
from django.template.context_processors import csrf
from django.contrib.auth import *
from django.contrib import messages
import random

def create_step_1(request):
    profileKey = random.randint(10000000, 99999999)
    request.session['profileKey'] = profileKey
    return render_to_response('step1.html', { 'profileKey': profileKey }, context_instance=RequestContext(request))

def create_step_2(request):
    key = request.session['profileKey']
    if not key: 
        return HttpResponseRedirect('/auth/create')

    form = CreateUserForm()
    return render_to_response('step2.html', { 'form': form }, context_instance=RequestContext(request))

def create_step_3(request):
    key = request.session['profileKey']
    if not key or request.method != 'POST': 
        return HttpResponseRedirect('/auth/create')

    c = {}
    c.update(csrf(request))
    
    form = CreateUserForm(request.POST)
    form.required_key = key
    if form.is_valid():
        user = CreateUser(form.cleaned_data['login'], form.cleaned_data['email'], form.cleaned_data['password'], form.userid)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        messages.add_message(request, messages.SUCCESS, '<strong>Done!</strong> Your account was created and you are now logged in.')
        return HttpResponseRedirect('/')
    else:
        return render_to_response('step2.html', { 'form': form }, context_instance=RequestContext(request))

def CreateUser(login, email, password, userid):
    u = User.objects.create_user(login, email, password)
    u.save()
    
    p, created = Player.objects.get_or_create(uid=userid, defaults={'name': login})
        
    profile = UserProfile(player=p, user=u)
    profile.save()
    
    return u
