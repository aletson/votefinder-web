from votefinder.main.models import *
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.http import HttpResponseForbidden
from django.http import HttpResponse
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from django.core.context_processors import csrf
from django.contrib import messages
from datetime import timedelta, datetime
from django.db.models import Q
from django.core.cache import cache
from pytz import timezone, common_timezones
from math import ceil

from PageParser import PageParser
from GameListDownloader import GameListDownloader
from VotecountFormatter import VotecountFormatter
import re
from django.db.models import Max

def index(request):
	game_list = Game.objects.select_related(depth=1).filter(closed=False).order_by("name").extra(select={'size': "select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.spectator=0 and main_playerstate.moderator=0", 'day': 'select dayNumber from main_gameday where main_gameday.game_id=main_game.id order by dayNumber desc limit 1', 'alive': 'select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.alive=1'})

	big_games = filter(lambda g: g.size > 15, game_list)
	mini_games = filter(lambda g: g.size <= 15, game_list)
	
	posts = BlogPost.objects.all().order_by("-timestamp")[:5]

	game_count = Game.objects.count()
	post_count = Post.objects.count()
	vote_count = Vote.objects.count()
	player_count = Player.objects.count()

	return render_to_response("index.html", 
							{'big_games': big_games, 'mini_games': mini_games, 
							'total': len(big_games) + len(mini_games), 'posts': posts,
							'game_count': game_count, 'post_count': post_count, 'vote_count': vote_count,
							'player_count': player_count }, 
							context_instance=RequestContext(request))

@login_required
def add(request):
	defaultUrl = "http://forums.somethingawful.com/showthread.php?threadid=3069667"
	return render_to_response("add.html", { 'defaultUrl': defaultUrl }, context_instance=RequestContext(request))

@login_required
def add_game(request, threadid):
	data = { 'success': True, 'message': 'Success!', 'url': ''}
	
	try:
		game = Game.objects.get(threadId=threadid)
		data['url'] = game.get_absolute_url()
	except Game.DoesNotExist:
		p = PageParser()
		p.user = request.user
		game = p.Add(threadid)
		if game:
			data['url'] = game.get_absolute_url()
			game.status_update("A new game was created by %s!" % game.moderator)
		else:
			data['success'] = False
			data['message'] = "Couldn't download or parse the forum thread.  Sorry!"

	return HttpResponse(simplejson.dumps(data), mimetype='application/json')

@login_required
def game_list(request, page):
	p = GameListDownloader()
	p.GetGameList("http://forums.somethingawful.com/forumdisplay.php?forumid=103&pagenumber=%s" % page)
	return HttpResponse(simplejson.dumps(p.GameList), mimetype='application/json')

def game(request, slug):
	game = get_object_or_404(Game, slug=slug)
	players = game.players.select_related().all()

	moderator = game.is_user_mod(request.user)
	form = AddPlayerForm()
	try:
		comment = Comment.objects.get(game=game)
		comment_form = AddCommentForm(initial={'comment':comment.comment})
	except Comment.DoesNotExist:
		comment_form = AddCommentForm()

	moderators = [ps.player for ps in game.moderators()]
	templates = VotecountTemplate.objects.select_related(depth=1).filter(Q(creator__in=moderators) | Q(shared=True))
	updates = GameStatusUpdate.objects.filter(game=game).order_by('-timestamp')

	gameday = game.days.select_related(depth=1).all().order_by('-dayNumber')[:1][0]
	manual_votes = Vote.objects.filter(game=game, manual=True, post__id__gte=gameday.startPost.id).order_by('id')

	if game.deadline:
		tz = timezone(game.timezone)
		tzone = tz.zone
		deadline = timezone('UTC').localize(game.deadline).astimezone(tz)
	else:
		deadline = timezone(game.timezone).localize(datetime.now() + timedelta(days=3))
		tzone = game.timezone

	return render_to_response('game.html', 
							{ 'game': game, 'players': players, 'moderator': moderator, 'form': form,
								'comment_form': comment_form, 'gameday': gameday,
								'nextDay': gameday.dayNumber + 1, 'deadline': deadline, 'templates': templates,
								'manual_votes': manual_votes, 'timezone': tzone, 'common_timezones': common_timezones,
								'updates': updates }, 
							context_instance=RequestContext(request))

def update(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	if game.is_locked():
		return HttpResponse(simplejson.dumps({ 'success': False, 'message': 'Someone else is updating that game right now.  Please wait.'}), mimetype='application/json')
	else:
		game.lock()
	try:
		p = PageParser()
		newGame = p.Update(game)
		if newGame:
			return HttpResponse(simplejson.dumps({ 'success': True, 'curPage': newGame.currentPage, 'maxPages': newGame.maxPages}), mimetype='application/json')
		else:
			game.save()
			return HttpResponse(simplejson.dumps({ 'success': False, 'message': 'There was a problem either downloading or parsing the forum page.  Please try again later.'}), mimetype='application/json')
	except:
		game.save()
		raise
		#return HttpResponse(simplejson.dumps({ 'success': False, 'message': 'There was a problem updating the thread.  Please try again later.'}), mimetype='application/json')

@login_required
def profile(request):
	player = request.user.get_profile().player
	games = player.games.select_related().all()

	return render_to_response('profile.html', 
							  { 'player': player, 'games': games, 'profile': request.user.get_profile(),
								'show_delete': True }, 
							  context_instance=RequestContext(request))

def player(request, slug):
	try:
		player = Player.objects.get(slug=slug)
		games = player.games.select_related().all()
	except Player.DoesNotExist:
		return HttpResponseNotFound
	
	try:
		aliases = Alias.objects.filter(player=player)
	except Alias.DoesNotExist:
		pass

	show_delete = False
	if request.user.is_superuser or (request.user.is_authenticated() and request.user.get_profile().player == player):
		show_delete = True
	
	return render_to_response('player.html', 
							  { 'player': player, 'games': games, 'aliases': aliases, 'show_delete': show_delete }, context_instance=RequestContext(request))

def player_id(request, playerid):
	player = get_object_or_404(Player, id=playerid)
	return HttpResponseRedirect(player.get_absolute_url())

@login_required
def player_state(request, gameid, playerid, state):
	game = get_object_or_404(Game, id=gameid)
	player = get_object_or_404(Player, id=playerid)
	current_state = get_object_or_404(PlayerState, game=game, player=player)

	if not game.is_user_mod(request.user) or game.moderator == player:
		return HttpResponseNotFound
	
	if state == 'dead':
		current_state.set_dead()
	elif state == 'alive':
		current_state.set_alive()
	elif state == 'spectator':
		current_state.set_spectator()
	elif state == 'mod':
		current_state.set_moderator()
	else:
		return HttpResponseNotFound
		
	current_state.save()
	return HttpResponse(simplejson.dumps({ 'success': True }))

def player_list(request):
	results = []
	try:
		for player in Player.objects.filter(name__icontains=request.GET['term']):
			results.append(player.name)
	except Player.DoesNotExist:
		pass
	
	return HttpResponse(simplejson.dumps(results), mimetype='application/json')

@login_required
def add_player(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	if request.method != 'POST' or not game.is_user_mod(request.user):
		return HttpResponseNotFound
	
	c = {}
	c.update(csrf(request))
	form = AddPlayerForm(request.POST)
	if form.is_valid():
		current_state, created = PlayerState.objects.get_or_create(player=form.player, game=game)
		if not current_state.moderator:
			current_state.set_alive()
			current_state.save()
		if created:
			messages.add_message(request, messages.SUCCESS, '<strong>%s</strong> was added to the game.' % form.player)
		else:
			messages.add_message(request, messages.SUCCESS, '<strong>%s</strong> was already in the game, but they have been set to alive.' % form.player)
	else:
		messages.add_message(request, messages.ERROR, 'Unable to find a player named <strong>%s</strong>.' % form.data['name'])
		
	return HttpResponseRedirect(game.get_absolute_url())

@login_required	
def delete_spectators(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound

	for p in game.spectators():
		PlayerState.delete(p)
		
	messages.add_message(request, messages.SUCCESS, 'All spectators were deleted from the game.')
	return HttpResponseRedirect(game.get_absolute_url())

def votecount(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	try:
		votes = Vote.objects.select_related(depth=2).filter(game=game, target=None, unvote=False, ignored=False, nolynch=False)
		if votes:
			players = sorted(game.all_players(), key=lambda p: p.player.name.lower())
			return render_to_response('unresolved.html', 
								  { 'game': game, 'votes': votes, 'players': players }, context_instance=RequestContext(request))
	except Vote.DoesNotExist:
		pass

	v = VotecountFormatter(game)
	v.go()
	
	return render_to_response('votecount.html',
							{ 'html_votecount': v.html_votecount, 'bbcode_votecount': v.bbcode_votecount }, 
							context_instance=RequestContext(request))
	
def resolve(request, voteid, resolution):
	vote = get_object_or_404(Vote, id=voteid)
	votes = Vote.objects.filter(game=vote.game, targetString__iexact=vote.targetString, target=None, unvote=False, ignored=False)

	if resolution == '-1':
		vote.ignored = True
		vote.save()
	elif resolution == '-2':
		vote.nolynch = True
		vote.save()
	else:
		player = get_object_or_404(Player, id=int(resolution))
		for v in votes:
			v.target = player
			v.save()
		
		alias, created = Alias.objects.get_or_create(player=player, alias=vote.targetString)
		if created:
			alias.save()

	key = "%s-vc-image" % v.game.slug
	cache.delete(key)

	newVotes = Vote.objects.filter(game=vote.game, targetString__iexact=vote.targetString, target=None, unvote=False, ignored=False, nolynch=False)
	
	if len(votes) == 1 and len(newVotes) > 0:
		refreh = False
	else:
		refresh = True
	return HttpResponse(simplejson.dumps({ 'success': True, 'refresh': refresh }))

def posts(request, gameid, page):
	game = get_object_or_404(Game, id=gameid)
	posts = game.posts.select_related(depth=2).filter(pageNumber=page).order_by('id')
	page = int(page)
	gameday = game.days.select_related(depth=1).all().order_by('-dayNumber')[:1][0]
	moderator = game.is_user_mod(request.user)

	return render_to_response('posts.html',
						{ 'game': game, 'posts': posts,
							'prevPage': page - 1, 'nextPage': page + 1, 'page': page, 'pageNumbers': range(1, game.currentPage + 1),
							'currentDay': gameday.dayNumber, 'nextDay': gameday.dayNumber + 1, 'moderator': moderator
						}, context_instance=RequestContext(request))

@login_required
def add_comment(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	if request.method != 'POST' or not game.is_user_mod(request.user):
		return HttpResponseNotFound
	
	c = {}
	c.update(csrf(request))
	form = AddCommentForm(request.POST)
	if form.is_valid():
		comments = Comment.objects.filter(game=game)
		if len(comments) > 0:
			comments.delete()
		
		if len(form.cleaned_data['comment']) > 1:
			comment = Comment(comment=form.cleaned_data['comment'], player=request.user.get_profile().player, game=game)
			comment.save()
			game.status_update_noncritical("%s added a comment: %s" % (request.user.get_profile().player, form.cleaned_data['comment']))

		messages.add_message(request, messages.SUCCESS, 'Your comment was added successfully.')
	else:
		messages.add_message(request, messages.ERROR, 'Unable to add your comment.  Was it empty?')
	return HttpResponseRedirect(game.get_absolute_url())

@login_required
def delete_comment(request, commentid):
	c = get_object_or_404(Comment, id=commentid)
	if not c.game.is_user_mod(request.user):
		return HttpResponseNotFound

	url = c.game.get_absolute_url()
	Comment.delete(c)
	messages.add_message(request, messages.SUCCESS, 'The comment was deleted successfully.')
	return HttpResponseRedirect(url)

@login_required
def deadline(request, gameid, month, day, year, hour, min, ampm, tzname):
	game = get_object_or_404(Game, id=gameid)
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound

	hour = int(hour)
	if ampm == 'AM' and hour == 12:
		hour = hour - 12
	if ampm == 'PM' and hour != 12:
		hour = hour + 12

	prev_deadline = game.deadline
	dl = timezone(tzname).localize(datetime(int(year), int(month), int(day), int(hour), int(min)))
	game.timezone = tzname
	game.deadline = dl.astimezone(timezone('UTC')).replace(tzinfo=None)
	game.save()

	if not prev_deadline:
		game.status_update_noncritical("A deadline has been set for %s." % (dl.strftime("%A, %B %d at %I:%M %p ") + dl.tzname()))

	messages.add_message(request, messages.SUCCESS, 'The deadline was set successfully.')
	return HttpResponseRedirect(game.get_absolute_url())
	

@login_required
def close_game(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound
	
	game.closed = True
	game.save()

	game.status_update("The game is over.")

	messages.add_message(request, messages.SUCCESS, 'The game was <strong>closed</strong>!  Make sure to add it to the wiki!')
	
	return HttpResponseRedirect(game.get_absolute_url())

@login_required
def reopen_game(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound
	
	game.closed = False
	game.save()

	game.status_update("The game is re-opened!")
	
	messages.add_message(request, messages.SUCCESS, 'The game was <strong>re-opened</strong>!')
	
	return HttpResponseRedirect(game.get_absolute_url())

@login_required
def new_day(request, gameid, day):
	game = get_object_or_404(Game, id=gameid)
	post = game.posts.all().order_by('-id')[:1][0]
	return start_day(request, day, post.id)

@login_required
def replace(request, gameid, clear, outgoing, incoming):	
	game = get_object_or_404(Game, id=gameid)
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound

	playerOut = get_object_or_404(Player, id=outgoing)
	try:
		playerIn = Player.objects.get(name__iexact=incoming)
	except Player.DoesNotExist:
		messages.add_message(request, messages.ERROR, 'No player by the name <strong>%s</strong> was found!' % incoming)
		return HttpResponseRedirect(game.get_absolute_url())
	
	clearVotes = True if clear == 'true' else False

	try:
		playerState = PlayerState.objects.get(game=game, player=playerOut)
	except PlayerState.DoesNotExist:
		messages.add_message(request, messages.ERROR, 'The player <strong>%s</strong> is not in that game!' % playerOut)

	try:
		newPlayerState = PlayerState.objects.get(game=game, player=playerIn)
		if newPlayerState.spectator:
			newPlayerState.delete()
		else:
			messages.add_message(request, messages.ERROR, 'The player <strong>%s</strong> is already in that game!' % playerIn)
			return HttpResponseRedirect(game.get_absolute_url())
	except PlayerState.DoesNotExist:
		pass
	
	playerState.player = playerIn
	playerState.save()
	votesAffected = 0
	
	voteList = game.votes.filter(Q(author=playerOut) | Q(target=playerOut))
	votesAffected = len(voteList)
	
	if clearVotes:
		voteList.delete()
	else:
		for v in voteList:
			if v.author == playerOut:
				v.author = playerIn
			else:
				v.target = playerIn
			v.save()

	game.status_update_noncritical("%s is replaced by %s." % (playerOut, playerIn))
			
	messages.add_message(request, messages.SUCCESS, 'Success! <strong>%s</strong> was replaced by <strong>%s</strong>.  %s votes were affected.' % (playerOut, playerIn, votesAffected))
	return HttpResponseRedirect(game.get_absolute_url())

@login_required
def start_day(request, day, postid):
	post = get_object_or_404(Post, id=postid)
	if not post.game.is_user_mod(request.user):
		return HttpResponseNotFound

	gameday, created = GameDay.objects.get_or_create(game=post.game, dayNumber=day, defaults={'startPost': post})
	if not created:
		gameday.startPost = post
	gameday.save()
	
	post.game.deadline = None
	post.game.save()

	post.game.status_update("Day %s has begun!" % day)

	messages.add_message(request, messages.SUCCESS, 'Success! <strong>Day %s</strong> will now begin with post (%s) by %s.' % (gameday.dayNumber, post.postId, post.author))

	return HttpResponseRedirect(post.game.get_absolute_url())

@login_required
def templates(request):
	templates = VotecountTemplate.objects.filter(creator=request.user.get_profile().player)
	return render_to_response("templates.html", {'templates': templates }, context_instance=RequestContext(request))

@login_required
def create_template(request):
	if request.method == 'GET':
		try:
			system_default = VotecountTemplate.objects.get(system_default=True)
		except VotecountTemplate.DoesNotExist:
			system_default = VotecountTemplate()
			
		system_default.name = "My New Template"
		return render_to_response("template_edit.html", {'form': VotecountTemplateForm(instance=system_default) }, context_instance=RequestContext(request))

	c = {}
	c.update(csrf(request))
	form = VotecountTemplateForm(request.POST)
	if form.is_valid():
		new_temp = form.save(commit=False)
		new_temp.creator = request.user.get_profile().player
		new_temp.save()

		messages.add_message(request, messages.SUCCESS, 'Success! The template <strong>%s</strong> was saved.' % new_temp.name)
		return HttpResponseRedirect("/templates")
	else:
		return render_to_response("template_edit.html", {'form': form }, 
								context_instance=RequestContext(request))

@login_required
def edit_template(request, templateid):
	t = get_object_or_404(VotecountTemplate, id=templateid)
	if not request.user.is_superuser and t.creator != request.user.get_profile().player:
		return HttpResponseNotFound
	
	if request.method == 'GET':
		return render_to_response("template_edit.html", {'form': VotecountTemplateForm(instance=t), 'template': t, 'edit': True }, 
								context_instance=RequestContext(request))
	
	c = {}
	c.update(csrf(request))
	form = VotecountTemplateForm(request.POST)
	if form.is_valid():
		new_temp = form.save(commit=False)
		new_temp.id = t.id
		new_temp.creator = t.creator
		new_temp.system_default = t.system_default
		new_temp.save()

		if t.shared and not new_temp.shared:
			player = request.user.get_profile().player
			for g in Game.objects.filter(template=new_temp):
				if not g.is_player_mod(player):
					g.template = None
					g.save()
		
		messages.add_message(request, messages.SUCCESS, 'Success! The template <strong>%s</strong> was saved.' % new_temp.name)
		return HttpResponseRedirect("/templates")
	else:
		return render_to_response("template_edit.html", {'form': form, 'template': t, 'edit': True }, 
								context_instance=RequestContext(request))

@login_required
def delete_template(request, templateid):
	t = get_object_or_404(VotecountTemplate, id=templateid)
	if not request.user.is_superuser and t.creator != request.user.get_profile().player:
		return HttpResponseNotFound

	if t.system_default:
		messages.add_message(request, messages.ERROR, '<strong>Error!</strong> You cannot delete the system default template.')
		return HttpResponseRedirect('/templates')

	for g in Game.objects.filter(template=t):
		g.template = None
		g.save()
		
	t.delete()

	messages.add_message(request, messages.SUCCESS, 'Template was deleted!')
	return HttpResponseRedirect('/templates')
		
@login_required
def game_template(request, gameid, templateid):	
	game = get_object_or_404(Game, id=gameid)
	template = get_object_or_404(VotecountTemplate, id=templateid)
	
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound

	game.template = None if template.system_default else template
	game.save()
	
	messages.add_message(request, messages.SUCCESS, '<strong>Success!</strong> This game now uses the template <strong>%s</strong>.' % template.name)
	return HttpResponseRedirect(game.get_absolute_url())

def active_games(request):
	game_list = Game.objects.select_related(depth=1).filter(closed=False).order_by("name").extra(select={'size': "select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.spectator=0 and main_playerstate.moderator=0", 'day': 'select dayNumber from main_gameday where main_gameday.game_id=main_game.id order by dayNumber desc limit 1', 'alive': 'select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.alive=1'})

	big_games = filter(lambda g: g.size > 15, game_list)
	mini_games = filter(lambda g: g.size <= 15, game_list)
	
	return render_to_response("wiki_games.html", 
							{'big_games': big_games, 'mini_games': mini_games }, context_instance=RequestContext(request))

def active_games_style(request, style):
	if style == "default" or style == "verbose":
		game_list = Game.objects.select_related(depth=1).filter(closed=False).order_by("name").extra(select={'size': "select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.spectator=0 and main_playerstate.moderator=0", 'day': 'select dayNumber from main_gameday where main_gameday.game_id=main_game.id order by dayNumber desc limit 1', 'alive': 'select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.alive=1'})

		big_games = filter(lambda g: g.size > 15, game_list)
		mini_games = filter(lambda g: g.size <= 15, game_list)
	
		return render_to_response("wiki_games.html", 
								{'big_games': big_games, 'mini_games': mini_games, 'style': style }, 
								context_instance=RequestContext(request))
	elif style == "closedmonthly":
		game_list = Game.objects.select_related(depth=1).filter(closed=True).order_by("name").extra(select={'size': "select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.spectator=0 and main_playerstate.moderator=0", 'last_post': "select max(timestamp) from main_post where main_post.game_id=main_game.id"}).order_by("-last_post")
		game_list = filter(lambda g: datetime.now() - g.last_post < timedelta(days=31), game_list)

		return render_to_response("wiki_closed_games.html", 
								{'game_list': game_list }, 
								context_instance=RequestContext(request))
	else:
		return HttpResponse("Style not supported")

def active_games_json(request):
	gameList = sorted([{'name': g.name, 'mod': g.moderator.name, 'url': 'http://forums.somethingawful.com/showthread.php?threadid=%s' % g.threadId} for g in Game.objects.select_related(depth=1).filter(closed=False)], key = lambda g: g['name'])
	
	return HttpResponse(simplejson.dumps(gameList), mimetype='application/json')

def closed_games(request):
	game_list = Game.objects.select_related(depth=1).filter(closed=True).order_by("name").extra(select={'size': "select count(*) from main_playerstate where main_playerstate.game_id=main_game.id and main_playerstate.spectator=0 and main_playerstate.moderator=0", 'last_post': "select max(timestamp) from main_post where main_post.game_id=main_game.id", 'first_post': "select min(timestamp) from main_post where main_post.game_id=main_game.id"})

	return render_to_response("closed.html",
                                                        {'games': game_list,
                                                        'total': len(game_list) }, context_instance=RequestContext(request))

@login_required
def add_vote(request, gameid, player, votes, target):
	game = get_object_or_404(Game, id=gameid)
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound

	gameday = game.days.select_related(depth=1).all().order_by('-dayNumber')[:1][0]
	v = Vote(manual=True, post=gameday.startPost, game=game)
	if player == '-1':
		v.author = Player.objects.get(uid=0) #anonymous
	else:
		v.author = get_object_or_404(Player, id=player)

	if votes == 'unvotes':
		v.unvote = True
	else:
		v.target = get_object_or_404(Player, id=target)

	v.save()
	messages.add_message(request, messages.SUCCESS, 'Success! A new manual vote was saved.')
	return HttpResponseRedirect(game.get_absolute_url())

@login_required
def delete_vote(request, voteid):
	vote = get_object_or_404(Vote, id=voteid)
	game = vote.game
	if not game.is_user_mod(request.user):
		return HttpResponseNotFound

	vote.delete()
	messages.add_message(request, messages.SUCCESS, 'Success!  The vote was deleted.')
	return HttpResponseRedirect(game.get_absolute_url())

import Image, ImageFont
from ImageDraw import ImageDraw

def draw_wordwrap_text(draw, text, xpos, ypos, max_width, font):
	fill = (0, 0, 0, 255)
	used_width = 0
	max_width -= xpos
	space_width, space_height = draw.textsize(' ', font=font)

	text_size_x, text_size_y = draw.textsize(text, font=font)
	remaining = max_width
	output_text = []

	for word in text.split(None):
		word_width, word_height = draw.textsize(word, font=font)
		if word_width + space_width > remaining:
			output_text.append(word)
			remaining = max_width - word_width
		else:
			if not output_text:
				output_text.append(word)
			else:
				output = output_text.pop()
				output += ' %s' % word
				output_text.append(output)

			remaining = remaining - (word_width + space_width)

	for t in output_text:
		cur_width, cur_height = draw.textsize(t, font=font)
		if (cur_width > used_width):
			used_width = cur_width

		draw.text((xpos, ypos), t, font=font, fill=fill)
		ypos += text_size_y

	return used_width + xpos, ypos

def draw_votecount_text(draw, vc, xpos, ypos, max_width, font, bold_font):
	results = filter(lambda x: x['count'] > 0, vc.results)
	longest_name = 0
	divider_len_x, divider_len_y = draw.textsize(": ", font=font)
	max_x = 0
	for line in results:
		text = "%s (%s)" % (line['target'].name, line['count'])
		this_size_x, this_size_y = draw.textsize(text, font=bold_font)
		line['size'] = this_size_x
		if this_size_x > longest_name:
			longest_name = this_size_x

	for line in results:
		pct = 1.0 * line['count'] / vc.tolynch
		box_width  = min(pct * longest_name, longest_name)
		draw.rectangle([longest_name - box_width, ypos, longest_name, this_size_y + ypos], fill=(155 + (pct * 100), 100, 100, pct * 255))

		text = "%s (%s)" % (line['target'].name, line['count'])
		(x_size1, y_bottom1) = draw_wordwrap_text(draw, text, longest_name - line['size'], ypos, max_width, bold_font)

		(x_size2, y_bottom2) = draw_wordwrap_text(draw, ": ", x_size1, ypos, max_width, font)

		text = ", ".join([v['author'].name for v in filter(lambda v: v['unvote'] == False and v['enabled'] == True, line['votes'])])
		(x_size3, y_bottom3) = draw_wordwrap_text(draw, text, x_size2 + divider_len_x, ypos, max_width, font)
		
		max_x = max(max_x, x_size3)
		ypos = max(y_bottom1, y_bottom2, y_bottom3)

	return (max_x, ypos)

def votecount_to_image(img, game, xpos = 0, ypos = 0, max_width = 600):
	draw = ImageDraw(img)
	regular_font = ImageFont.truetype('/home/soru/public_html/votefinder.org/votefinder/static/MyriadPro-Regular.otf', 15)
	bold_font = ImageFont.truetype('/home/soru/public_html/votefinder.org/votefinder/static/MyriadPro-Bold.otf', 15)

	game.template = VotecountTemplate.objects.get(id=11)
	vc = VotecountFormatter(game)
	vc.go()

	(header_text, footer_text) = re.compile("\[.*?\]").sub('', vc.bbcode_votecount).split("\r\n")
	(header_x_size, header_y_size) = draw_wordwrap_text(draw, header_text, 0, 0, max_width, bold_font)
	draw.line([0, header_y_size - 2, header_x_size, header_y_size - 2], fill=(0,0,0,255), width=2)
	ypos = 2 * header_y_size

	(vc_x_size, ypos) = draw_votecount_text(draw, vc, 0, ypos, max_width, regular_font, bold_font)
	ypos += header_y_size

	(x_size, ypos) = draw_wordwrap_text(draw, footer_text, 0, ypos, max_width, regular_font)

	votes = Vote.objects.select_related(depth=2).filter(game=game, target=None, unvote=False, ignored=False, nolynch=False)
	if len(votes) > 0:
		ypos += header_y_size
		if len(votes) == 1:
			warning_text = "Warning: There is currently 1 unresolved vote.  The votecount may be inaccurate."
		else:
			warning_text = "Warning: There are currently %s unresolved votes.  The votecount may be inaccurate." % len(votes)

		(warning_x, ypos) = draw_wordwrap_text(draw, warning_text, 0, ypos, max_width, bold_font)
		x_size = max(x_size, warning_x)

	return (max(header_x_size, vc_x_size, x_size), ypos)

def check_update_game(game):
	if game.is_locked():
		return game
	else:
		game.lock()

	try:
		p = PageParser()
		newGame = p.Update(game)
		if newGame:
			return newGame
		else:
			game.save()
			return game
	except:
		return game

def votecount_image(request, slug):
	game = get_object_or_404(Game, slug=slug)

	key = "%s-vc-image" % slug
	img_dict = cache.get(key)

	if img_dict == None:
		game = check_update_game(game)
		img = Image.new("RGBA", (800, 1024), color=(255, 255, 255, 0))
		(w, h) = votecount_to_image(img, game, 0, 0, 800)
		img = img.crop((0, 0, w, h))
		cache.set(key, { "size": img.size, "data": img.tostring() }, 120)
	else:
		img = Image.fromstring("RGBA", img_dict['size'], img_dict['data'])

	response = HttpResponse(mimetype="image/png")
	img.save(response, "PNG")#, transparency=(255, 255, 255))
	return response

def autoupdate(request):
	games = Game.objects.filter(closed=False).order_by("lastUpdated")[:1]
	if len(games) == 1:
		game = check_update_game(games[0])
		post = game.posts.order_by('-timestamp')[:1][0]

		if datetime.now() - post.timestamp > timedelta(days=6):
			game.status_update("Closed automatically for inactivity.")
			game.closed = True
			game.save()

	return HttpResponse("Ok")

def players(request):
	return players_page(request, 1)

def players_page(request, page):
	items_per_page = 3000
	page = int(page)

	if page < 1:
		return HttpResponseRedirect('/players')

	first_record = (page - 1) * items_per_page

	total_players = Player.objects.all().count()
	total_pages = int(ceil(1.0 * total_players / items_per_page))

	players = Player.objects.select_related(depth=1).filter(uid__gt='0').order_by("name").extra(select={'alive':"select count(*) from main_playerstate join main_game on main_playerstate.game_id=main_game.id where main_playerstate.player_id=main_player.id and main_game.closed=false and main_playerstate.alive=true", 'last_post':"select max(timestamp) from main_post where author_id=main_player.id", 'total_posts':"select count(*) from main_post where main_post.author_id=main_player.id",'total_games_played':"select count(*) from main_playerstate where main_playerstate.player_id=main_player.id and main_playerstate.moderator=false and main_playerstate.spectator=false",'total_games_run':"select count(*) from main_game where main_game.moderator_id=main_player.id"})[first_record : first_record + items_per_page]

	if len(players) == 0:
		return HttpResponseRedirect('/players')

	return render_to_response("players.html", 
							{'players': players, 'page': page, 'total_pages': total_pages },
							context_instance=RequestContext(request))

@login_required
def delete_alias(request, id):
	alias = get_object_or_404(Alias, id=id)
	if not request.user.is_superuser and not request.user.get_profile().player == alias.player:
		return HttpResponseForbidden

	messages.add_message(request, messages.SUCCESS, 'The alias <strong>%s</strong> was deleted.' % alias.alias)
	player = alias.player
	alias.delete()

	return HttpResponseRedirect("/player/" + player.slug)

@login_required
def sendpms(request, slug):
	game = get_object_or_404(Game, slug=slug)
	if not game.is_user_mod(request.user):
		return HttpResponseForbidden

	return render_to_response("sendpms.html", { 'game': game },
							  context_instance=RequestContext(request))

def post_histories(request, gameid):
	game = get_object_or_404(Game, id=gameid)
	return render_to_response("post_histories.html", { 'game': game },  context_instance=RequestContext(request))

@login_required
def post_lynches(request, gameid, enabled):
	game = get_object_or_404(Game, id=gameid)
	if not game.is_user_mod(request.user):
		return HttpResponseForbidden

	if enabled == "on":
		game.post_lynches = True
		messages.add_message(request, messages.SUCCESS, 'Posting of lynches for this game is now enabled!')
	else:
		game.post_lynches = False
		messages.add_message(request, messages.SUCCESS, 'Posting of lynches for this game is now disabled!')

	game.save()
	return HttpResponseRedirect(game.get_absolute_url())
