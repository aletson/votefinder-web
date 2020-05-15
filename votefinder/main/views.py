import json as simplejson
import math
import re
import urllib
from datetime import datetime, timedelta
from math import ceil

import boto3
from pytz import common_timezones, timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import connections
from django.db.models import Max, Min, Q
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseNotFound, HttpResponseRedirect)
from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.template.context_processors import csrf
from PIL import Image, ImageDraw, ImageFont
from votefinder.main.models import (AddCommentForm, AddPlayerForm, Alias,
                                    BlogPost, Comment, Game, GameDay,
                                    GameStatusUpdate, Player, PlayerState,
                                    Post, Theme, UserProfile, Vote,
                                    VotecountTemplate, VotecountTemplateForm)

from . import (ForumPageDownloader, GameListDownloader, PageParser,
               VoteCounter, VotecountFormatter)


def check_mod(request, game):
    try:
        moderator = game.is_user_mod(request.user) or request.user.is_superuser
    except AttributeError:
        moderator = False
    return moderator


def index(request):
    active_game_list = Game.objects.select_related().filter(state='started').order_by('name')
    pregame_list = Game.objects.select_related().filter(state='pregame').order_by('name')

    big_games = [this_game for this_game in active_game_list if this_game.is_big]
    mini_games = [this_game for this_game in active_game_list if not this_game.is_big]
    posts = BlogPost.objects.all().order_by('-timestamp')[:5]

    game_count = Game.objects.count()
    post_count = Post.objects.count()
    vote_count = Vote.objects.count()
    player_count = Player.objects.count()
    context = {'pregame_games': pregame_list, 'big_games': big_games, 'mini_games': mini_games,
               'total': len(big_games) + len(mini_games), 'posts': posts,
               'game_count': game_count, 'post_count': post_count, 'vote_count': vote_count,
               'player_count': player_count}
    return render(request, 'index.html', context)


@login_required
def add(request):
    default_url = 'http://forums.somethingawful.com/showthread.php?threadid=3069667'
    return render(request, 'add.html', {'defaultUrl': default_url})


@login_required
def add_game(request):
    data = {'success': True, 'message': 'Success!', 'url': ''}
    if request.method == 'POST':
        threadid = request.POST.get('threadid')
        state = request.POST.get('addState')
        if state in {'started', 'pregame'}:
            try:
                game = Game.objects.get(thread_id=threadid)
                data['url'] = game.get_absolute_url()
            except Game.DoesNotExist:
                p = PageParser.PageParser()
                p.user = request.user
                game = p.add_game(threadid, state)
                if game:
                    data['url'] = game.get_absolute_url()
                    game.status_update('A new game was created by {}!'.format(game.moderator.name))

                    sqs = boto3.client('sqs')
                    queue_url = settings.SQS_QUEUE_URL
                    sqs.send_message(
                        QueueUrl=queue_url,
                        DelaySeconds=10,
                        MessageAttributes={
                            'GameTitle': {
                                'DataType': 'String',
                                'StringValue': game.name,
                            },
                            'Moderator': {
                                'DataType': 'String',
                                'StringValue': game.moderator.name,
                            },
                            'threadId': {
                                'DataType': 'Number',
                                'StringValue': game.thread_id,
                            },
                        },
                        MessageBody=(
                            'New game announcement'
                        ),
                    )
                else:
                    data['success'] = False
                    data['message'] = "Couldn't download or parse the forum thread.  Sorry!"
        else:
            data['success'] = False
            data['message'] = "Couldn\'t validate the starting game state. Please contact support."
    else:
        data['success'] = False
        data['message'] = 'Form was submitted incorrectly. Please use the add game page.'
    return HttpResponse(simplejson.dumps(data), content_type='application/json')


@login_required
def game_list(request, page):
    downloader = GameListDownloader.GameListDownloader()
    downloader.get_game_list('http://forums.somethingawful.com/forumdisplay.php?forumid=103&pagenumber={}'.format(page))
    return HttpResponse(simplejson.dumps(downloader.GameList), content_type='application/json')


def game(request, slug):
    game = get_object_or_404(Game, slug=slug)
    players = game.players.select_related().all()
    form = AddPlayerForm()
    try:
        comment = Comment.objects.get(game=game)
        comment_form = AddCommentForm(initial={'comment': comment.comment})
    except Comment.DoesNotExist:
        comment_form = AddCommentForm()

    moderators = [ps.player for ps in game.moderators()]
    templates = VotecountTemplate.objects.select_related().filter(Q(creator__in=moderators) | Q(shared=True))
    updates = GameStatusUpdate.objects.filter(game=game).order_by('-timestamp')

    gameday = game.days.select_related().last()
    manual_votes = Vote.objects.filter(game=game, manual=True, post__id__gte=gameday.start_post.id).order_by('id')

    if game.deadline:
        tz = timezone(game.timezone)
        tzone = tz.zone
        deadline = timezone(settings.TIME_ZONE).localize(game.deadline).astimezone(tz)
    else:
        deadline = timezone(game.timezone).localize(datetime.now() + timedelta(days=3))
        tzone = game.timezone

    post_vc_button = bool(check_mod(request, game) and (game.last_vc_post is None or datetime.now() - game.last_vc_post >= timedelta(minutes=60) or (game.deadline and game.deadline - datetime.now() <= timedelta(minutes=60))))
    context = {'game': game, 'players': players, 'moderator': check_mod(request, game), 'form': form,
               'comment_form': comment_form, 'gameday': gameday, 'post_vc_button': post_vc_button,
               'nextDay': gameday.day_number + 1, 'deadline': deadline, 'templates': templates,
               'manual_votes': manual_votes, 'timezone': tzone, 'common_timezones': common_timezones,
               'updates': updates}
    return render(request, 'game.html', context)


def update(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if game.is_locked():
        return HttpResponse(simplejson.dumps(
            {'success': False, 'message': 'Someone else is updating that game right now.  Please wait.'}),
            content_type='application/json')
    else:
        game.lock()
    try:
        p = PageParser.PageParser()
        new_game = p.Update(game)
        if new_game:
            return HttpResponse(
                simplejson.dumps({'success': True, 'curPage': new_game.current_page, 'maxPages': new_game.max_pages}),
                content_type='application/json')
        game.save()
        return HttpResponse(simplejson.dumps({'success': False, 'message': 'There was a problem either downloading or parsing the forum page.  Please try again later.'}),
                            content_type='application/json')
    except BaseException:
        game.save()
        raise


@login_required
def profile(request):
    player = request.user.profile.player
    games = player.games.select_related().all()
    themes = Theme.objects.all()
    context = {'player': player, 'games': games, 'profile': request.user.profile, 'themes': themes,
               'show_delete': True}
    return render(request, 'profile.html', context)


@login_required
def update_user_theme(request):
    if request.method == 'POST':
        profile = request.user.profile
        theme_id = request.POST.get('t')
        theme = Theme.objects.get(id=theme_id)
        profile.theme = theme  # This might not work check it afterwards.
        profile.save()
        return HttpResponse(simplejson.dumps({'success': True}))


def update_user_pronouns(request):
    if request.method == 'POST':
        profile = request.user.profile
        pronouns = request.POST.get('p')
        profile.pronouns = pronouns
        profile.save()
        return HttpResponse(simplejson.dumps({'success': True}))


def player(request, slug):
    try:
        player = Player.objects.get(slug=slug)
        games = player.games.select_related().all()
    except Player.DoesNotExist:
        return HttpResponseNotFound

    try:
        aliases = Alias.objects.filter(player=player)
        profile = UserProfile.objects.get(player=player)
        pronouns = profile.pronouns
    except Alias.DoesNotExist:
        pass
    except UserProfile.DoesNotExist:
        pronouns = None

    show_delete = False
    if request.user.is_superuser or (request.user.is_authenticated and request.user.profile.player == player):
        show_delete = True

    return render(request, 'player.html',
                  {'player': player, 'games': games, 'aliases': aliases, 'show_delete': show_delete, 'pronouns': pronouns})


def player_id(request, playerid):
    player = get_object_or_404(Player, id=playerid)
    return HttpResponseRedirect(player.get_absolute_url())


@login_required
def player_state(request, gameid, playerid, state):
    game = get_object_or_404(Game, id=gameid)
    player = get_object_or_404(Player, id=playerid)
    current_state = get_object_or_404(PlayerState, game=game, player=player)

    if not check_mod(request, game) or game.moderator == player:
        return HttpResponseNotFound

    if state == 'dead':
        current_state.set_dead()
        game.status_update('{} died.'.format(player.name))
    elif state == 'alive':
        current_state.set_alive()
    elif state == 'spectator':
        current_state.set_spectator()
    elif state == 'mod':
        current_state.set_moderator()
    else:
        return HttpResponseNotFound

    current_state.save()
    current_state.game.save()  # updated cached values

    return HttpResponse(simplejson.dumps({'success': True}))


def player_list(request):
    results = []
    try:
        for player in Player.objects.filter(name__icontains=request.GET['term']):
            results.append(player.name)
    except Player.DoesNotExist:
        pass

    return HttpResponse(simplejson.dumps(results), content_type='application/json')


@login_required
def add_player(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if request.method != 'POST' or not check_mod(request, game):
        return HttpResponseNotFound

    c = {}
    c.update(csrf(request))
    form = AddPlayerForm(request.POST)
    if form.is_valid():
        current_state, created = PlayerState.objects.get_or_create(player=form.player, game=game)
        if not current_state.moderator:
            current_state.set_alive()
            current_state.save()
            game.save()  # updated cached totals
        if created:
            messages.add_message(request, messages.SUCCESS, '<strong>{}</strong> was added to the game.'.format(form.player))
        else:
            messages.add_message(request, messages.SUCCESS,
                                 '<strong>{}</strong> was already in the game, but they have been set to alive.'.format(form.player))
    else:
        messages.add_message(request, messages.ERROR,
                             'Unable to find a player named <strong>{}</strong>.'.format(form.data['name']))

    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def delete_spectators(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if not check_mod(request, game):
        return HttpResponseNotFound

    for p in game.spectators():
        PlayerState.delete(p)

    messages.add_message(request, messages.SUCCESS, 'All spectators were deleted from the game.')
    return HttpResponseRedirect(game.get_absolute_url())


def votecount(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    try:
        votes = Vote.objects.select_related().filter(game=game, target=None, unvote=False, ignored=False, nolynch=False)
        if votes:
            players = sorted(game.all_players(), key=lambda p: p.player.name.lower())
            return render(request, 'unresolved.html',
                          {'game': game, 'votes': votes, 'players': players})
    except Vote.DoesNotExist:
        pass

    vc_formatter = VotecountFormatter.VotecountFormatter(game)
    vc_formatter.go()

    post_vc_button = bool(check_mod(request, game) and (game.last_vc_post is None or datetime.now() - game.last_vc_post >= timedelta(
        minutes=60) or (game.deadline and game.deadline - datetime.now() <= timedelta(minutes=60))))
    context = {'post_vc_button': post_vc_button,
               'html_votecount': vc_formatter.html_votecount,
               'bbcode_votecount': vc_formatter.bbcode_votecount}
    return render(request, 'votecount.html', context)


def resolve(request, voteid, resolution):
    vote = get_object_or_404(Vote, id=voteid)
    votes = Vote.objects.filter(game=vote.game, target_string__iexact=vote.target_string, target=None, unvote=False,
                                ignored=False)

    if resolution == '-1':
        vote.ignored = True
        vote.save()
    elif resolution == '-2':
        vote.nolynch = True
        vote.save()
    else:
        player = get_object_or_404(Player, id=int(resolution))
        for this_vote in votes:
            this_vote.target = player
            this_vote.save()

        alias, created = Alias.objects.get_or_create(player=player, alias=vote.target_string)
        if created:
            alias.save()

    key = '{}-vc-image'.format(vote.game.slug)
    cache.delete(key)

    new_votes = Vote.objects.filter(game=vote.game, target_string__iexact=vote.target_string, target=None, unvote=False,
                                    ignored=False, nolynch=False)

    refresh = bool(len(votes) != 1 or not new_votes)
    return HttpResponse(simplejson.dumps({'success': True, 'refresh': refresh}))


def posts(request, gameid, page):
    game = get_object_or_404(Game, id=gameid)
    posts = game.posts.select_related().filter(page_number=page).order_by('id')
    page = int(page)
    gameday = game.days.select_related().last()
    context = {'game': game, 'posts': posts,
               'prevPage': page - 1, 'nextPage': page + 1, 'page': page,
               'pageNumbers': range(1, game.current_page + 1),
               'currentDay': gameday.day_number, 'nextDay': gameday.day_number + 1, 'moderator': check_mod(request, game)}
    return render(request, 'posts.html', context)


@login_required
def start_game(request, gameid, day):
    game = get_object_or_404(Game, id=gameid)
    if game.state != 'pregame' or not check_mod(request, game):
        return HttpResponseNotFound
    game.state = 'started'
    game.save()
    game.status_update('The game has started!')
    if day == '1':
        return new_day(request, gameid, day)
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def add_comment(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if request.method != 'POST' or not check_mod(request, game):
        return HttpResponseNotFound

    c = {}
    c.update(csrf(request))
    form = AddCommentForm(request.POST)
    if form.is_valid():
        comments = Comment.objects.filter(game=game)
        if comments:
            comments.delete()

        if len(form.cleaned_data['comment']) > 1:
            comment = Comment(comment=form.cleaned_data['comment'], player=request.user.profile.player, game=game)
            comment.save()
            game.status_update_noncritical(
                '{} added a comment: {}'.format(request.user.profile.player, form.cleaned_data['comment']))

        messages.add_message(request, messages.SUCCESS, 'Your comment was added successfully.')
    else:
        messages.add_message(request, messages.ERROR, 'Unable to add your comment.  Was it empty?')
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def delete_comment(request, commentid):
    comment = get_object_or_404(Comment, id=commentid)
    if not check_mod(comment.game):
        return HttpResponseNotFound

    url = comment.game.get_absolute_url()
    Comment.delete(comment)
    messages.add_message(request, messages.SUCCESS, 'The comment was deleted successfully.')
    return HttpResponseRedirect(url)


@login_required
def deadline(request, gameid, month, day, year, hour, minute, ampm, tzname):
    game = get_object_or_404(Game, id=gameid)
    if game.state != 'started' or not check_mod(request, game):
        return HttpResponseNotFound

    hour = int(hour)
    if ampm == 'AM' and hour == 12:
        hour = hour - 12
    if ampm == 'PM' and hour != 12:
        hour = hour + 12

    prev_deadline = game.deadline
    dl = timezone(tzname).localize(datetime(int(year), int(month), int(day), int(hour), int(minute)))
    game.timezone = tzname
    game.deadline = dl.astimezone(timezone(settings.TIME_ZONE)).replace(tzinfo=None)
    game.save()

    if not prev_deadline:
        game.status_update_noncritical(
            'A deadline has been set for {}.'.format(dl.strftime('%A, %B %d at %I:%M %p ') + dl.tzname()))

    messages.add_message(request, messages.SUCCESS, 'The deadline was set successfully.')
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def close_game(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if not check_mod(request, game):
        return HttpResponseNotFound

    game.state = 'closed'
    game.save()

    game.status_update('The game is over.')

    messages.add_message(request, messages.SUCCESS,
                         'The game was <strong>closed</strong>!  Make sure to add it to the wiki!')

    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def reopen_game(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if game.state != 'closed' or not check_mod(request, game):
        return HttpResponseNotFound

    game.state = 'started'
    game.save()

    game.status_update('The game is re-opened!')

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
    if game.state != 'started' or not check_mod(request, game):
        return HttpResponseNotFound

    player_out = get_object_or_404(Player, id=outgoing)
    try:
        player_in = Player.objects.get(name__iexact=urllib.unquote(incoming))
    except Player.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'No player by the name <strong>{}</strong> was found!'.format(incoming))
        return HttpResponseRedirect(game.get_absolute_url())

    clear_votes = bool(clear == 'true')

    try:
        player_state = PlayerState.objects.get(game=game, player=player_out)
    except PlayerState.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'The player <strong>{}</strong> is not in that game!'.format(player_out))

    try:
        new_player_state = PlayerState.objects.get(game=game, player=player_in)
        if new_player_state.spectator:
            new_player_state.delete()
        else:
            messages.add_message(request, messages.ERROR,
                                 'The player <strong>{}</strong> is already in that game!'.format(player_in))
            return HttpResponseRedirect(game.get_absolute_url())
    except PlayerState.DoesNotExist:
        pass

    player_state.player = player_in
    player_state.save()
    votes_affected = 0

    vote_list = game.votes.filter(Q(author=player_out) | Q(target=player_out))
    votes_affected = len(vote_list)

    if clear_votes:
        vote_list.delete()
    else:
        for vote in vote_list:
            if vote.author == player_out:
                vote.author = player_in
            else:
                vote.target = player_in
            vote.save()

    game.status_update_noncritical('{} is replaced by {}.'.format(player_out, player_in))

    messages.add_message(request, messages.SUCCESS,
                         'Success! <strong>{}</strong> was replaced by <strong>{}</strong>.  {} votes were affected.'
                         .format(player_out, player_in, votes_affected))
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def start_day(request, day, postid):
    post = get_object_or_404(Post, id=postid)
    if post.game.state != 'started' or not check_mod(request, post.game):
        return HttpResponseNotFound

    gameday, created = GameDay.objects.get_or_create(game=post.game, day_number=day, defaults={'start_post': post})
    if not created:
        gameday.start_post = post
    gameday.save()

    post.game.deadline = None
    post.game.save()

    post.game.status_update('Day {} has begun!'.format(day))

    messages.add_message(request, messages.SUCCESS,
                         'Success! <strong>Day {}</strong> will now begin with post ({}) by {}.'
                         .format(gameday.day_number, post.post_id, post.author))

    return HttpResponseRedirect(post.game.get_absolute_url())


@login_required
def templates(request):
    templates = VotecountTemplate.objects.filter(creator=request.user.profile.player)
    return render(request, 'templates.html', {'templates': templates})


@login_required
def create_template(request):
    if request.method == 'GET':
        try:
            system_default = VotecountTemplate.objects.get(system_default=True)
        except VotecountTemplate.DoesNotExist:
            system_default = VotecountTemplate()

        system_default.name = 'My New Template'
        return render(request, 'template_edit.html', {'form': VotecountTemplateForm(instance=system_default)})

    c = {}
    c.update(csrf(request))
    form = VotecountTemplateForm(request.POST)
    if form.is_valid():
        new_temp = form.save(commit=False)
        new_temp.creator = request.user.profile.player
        new_temp.save()

        messages.add_message(request, messages.SUCCESS,
                             'Success! The template <strong>{}</strong> was saved.'.format(new_temp.name))
        return HttpResponseRedirect('/templates')
    return render(request, 'template_edit.html', {'form': form})


@login_required
def edit_template(request, templateid):
    old_temp = get_object_or_404(VotecountTemplate, id=templateid)
    if not request.user.is_superuser and old_temp.creator != request.user.profile.player:
        return HttpResponseNotFound

    if request.method == 'GET':
        return render(request, 'template_edit.html',
                      {'form': VotecountTemplateForm(instance=old_temp), 'template': old_temp, 'edit': True})

    c = {}
    c.update(csrf(request))
    form = VotecountTemplateForm(request.POST)
    if form.is_valid():
        new_temp = form.save(commit=False)
        new_temp.id = old_temp.id
        new_temp.creator = old_temp.creator
        new_temp.system_default = old_temp.system_default
        new_temp.save()

        if old_temp.shared and not new_temp.shared:
            player = request.user.profile.player
            for game in Game.objects.filter(template=new_temp):
                if not game.is_player_mod(player):
                    game.template = None
                    game.save()

        messages.add_message(request, messages.SUCCESS,
                             'Success! The template <strong>{}</strong> was saved.'.format(new_temp.name))
        return HttpResponseRedirect('/templates')
    return render(request, 'template_edit.html', {'form': form, 'template': old_temp, 'edit': True})


@login_required
def delete_template(request, templateid):
    template = get_object_or_404(VotecountTemplate, id=templateid)
    if not request.user.is_superuser and template.creator != request.user.profile.player:
        return HttpResponseNotFound

    if template.system_default:
        messages.add_message(request, messages.ERROR,
                             '<strong>Error!</strong> You cannot delete the system default template.')
        return HttpResponseRedirect('/templates')

    for this_game in Game.objects.filter(template=template):
        this_game.template = None
        this_game.save()

    template.delete()

    messages.add_message(request, messages.SUCCESS, 'Template was deleted!')
    return HttpResponseRedirect('/templates')


@login_required
def game_template(request, gameid, templateid):
    game = get_object_or_404(Game, id=gameid)
    template = get_object_or_404(VotecountTemplate, id=templateid)
    if not check_mod(request, game):
        return HttpResponseNotFound

    game.template = None if template.system_default else template
    game.save()

    messages.add_message(request, messages.SUCCESS,
                         '<strong>Success!</strong> This game now uses the template <strong>{}</strong>.'
                         .format(template.name))
    return HttpResponseRedirect(game.get_absolute_url())


def active_games(request):
    game_list = Game.objects.select_related().filter(state='started').order_by('name')

    big_games = [this_game for this_game in game_list if this_game.is_big]
    mini_games = [this_game for this_game in game_list if this_game.is_big is False]

    return render(request, 'wiki_games.html',
                  {'big_games': big_games, 'mini_games': mini_games})


def active_games_style(request, style):
    if style in {'default', 'verbose'}:
        game_list = Game.objects.select_related().filter(state='started').order_by('name')
        big_games = [this_game for this_game in game_list if this_game.is_big]
        mini_games = [this_game for this_game in game_list if not this_game.is_big]

        return render(request, 'wiki_games.html', {'big_games': big_games, 'mini_games': mini_games, 'style': style})
    elif style == 'closedmonthly':
        game_list = Game.objects.select_related().filter(state='closed').order_by('name').annotate(last_post=Max('posts__timestamp')).order_by(
            '-last_post')
        game_list = [this_game for this_game in game_list if datetime.now() - this_game.last_post < timedelta(days=31)]

        return render(request, 'wiki_closed_games.html', {'game_list': game_list})
    return HttpResponse('Style not supported')


def active_games_json(request):
    game_list = sorted(({'name': game.name, 'mod': game.moderator.name,
                        'url': 'http://forums.somethingawful.com/showthread.php?threadid={}'.format(game.thread_id)} for game in
                       Game.objects.select_related().filter(state='started')), key=lambda g: game['name'])

    return HttpResponse(simplejson.dumps(game_list), content_type='application/json')


def closed_games(request):
    game_list = Game.objects.select_related().filter(state='closed').order_by('name').annotate(last_post=Max('posts__timestamp'), first_post=Min('posts__timestamp'))
    return render(request, 'closed.html', {'games': game_list, 'total': len(game_list)})


@login_required
def add_vote(request, gameid, player, votes, target):
    game = get_object_or_404(Game, id=gameid)
    if game.state != 'started' or not check_mod(request, game):
        return HttpResponseNotFound

    gameday = game.days.select_related().last()
    vote = Vote(manual=True, post=gameday.start_post, game=game)
    if player == '-1':
        vote.author = Player.objects.get(uid=0)  # anonymous
    else:
        vote.author = get_object_or_404(Player, id=player)

    if votes == 'unvotes':
        vote.unvote = True
    else:
        vote.target = get_object_or_404(Player, id=target)

    vote.save()
    messages.add_message(request, messages.SUCCESS, 'Success! A new manual vote was saved.')
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def add_vote_global(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if game.state != 'started' or not check_mod(request, game):
        return HttpResponseNotFound

    gameday = game.days.select_related().last()
    playerlist = get_list_or_404(PlayerState, game=game)
    for indiv_player in playerlist:
        target = get_object_or_404(Player, id=indiv_player.player_id)
        vote = Vote(manual=True, post=gameday.start_post, game=game, author=Player.objects.get(uid=0), target=target)
        vote.save()
    messages.add_message(request, messages.SUCCESS, 'Success! A global hated vote has been added.')
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def delete_vote(request, voteid):
    vote = get_object_or_404(Vote, id=voteid)
    game = vote.game
    if game.state != 'started' or not check_mod(request, game):
        return HttpResponseNotFound

    vote.delete()
    messages.add_message(request, messages.SUCCESS, 'Success!  The vote was deleted.')
    return HttpResponseRedirect(game.get_absolute_url())


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
        elif output_text:
            output = output_text.pop()
            output = '{} {}'.format(output, word)
            output_text.append(output)
            remaining = remaining - (word_width + space_width)
        else:
            output_text.append(word)
            remaining = remaining - (word_width + space_width)

    for t in output_text:
        cur_width, cur_height = draw.textsize(t, font=font)
        if (cur_width > used_width):
            used_width = cur_width

        draw.text((xpos, ypos), t, font=font, fill=fill)
        ypos += text_size_y

    return used_width + xpos, ypos


def draw_votecount_text(draw, vc, xpos, ypos, max_width, font, bold_font):
    results = [x for x in vc.results if x['count'] > 0]
    longest_name = 0
    divider_len_x, divider_len_y = draw.textsize(': ', font=font)
    max_x = 0
    if results is None:  # No votes found
        text = 'No votes found in vc.results~'
        this_size_x, this_size_y = draw.textsize(text, font=bold_font)
        line = []
        line['size'] = this_size_x
        (x_size1, y_bottom1) = draw_wordwrap_text(draw, text, 0, ypos, max_width, bold_font)
        return (x_size1, y_bottom1)
    for line in results:
        text = '{} ({})'.format(line['target'].name, line['count'])
        this_size_x, this_size_y = draw.textsize(text, font=bold_font)
        line['size'] = this_size_x
        if this_size_x > longest_name:
            longest_name = this_size_x

    for line in results:
        pct = 1.0 * line['count'] / vc.tolynch
        box_width = min(pct * longest_name, longest_name)
        draw.rectangle([longest_name - box_width, ypos, longest_name, this_size_y + ypos],
                       fill=(int(155 + (pct * 100)), 100, 100, int(pct * 255)))

        text = '{} ({})'.format(line['target'].name, line['count'])
        (x_size1, y_bottom1) = draw_wordwrap_text(draw, text, longest_name - line['size'], ypos, max_width, bold_font)

        (x_size2, y_bottom2) = draw_wordwrap_text(draw, ': ', x_size1, ypos, max_width, font)

        text = ', '.join(
            [v['author'].name for v in filter(lambda v: v['unvote'] is False and v['enabled'], line['votes'])])
        (x_size3, y_bottom3) = draw_wordwrap_text(draw, text, x_size2 + divider_len_x, ypos, max_width, font)

        max_x = max(max_x, x_size3)
        ypos = max(y_bottom1, y_bottom2, y_bottom3)

    return (max_x, ypos)


def votecount_to_image(img, game, xpos=0, ypos=0, max_width=600):
    draw = ImageDraw.Draw(img)
    regular_font = ImageFont.truetype(settings.REGULAR_FONT_PATH, 15)
    bold_font = ImageFont.truetype(settings.BOLD_FONT_PATH, 15)
    tid = 11  # default template, no custom image template support yet
    game.template = VotecountTemplate.objects.get(id=tid)
    vc = VotecountFormatter.VotecountFormatter(game)
    vc.go(show_comment=False)
    split_vc = re.compile(r'\[.*?\]').sub('', vc.bbcode_votecount).split('\r\n')
    header_text = split_vc[0]  # Explicitly take the first and last elements in case of multiline templates
    footer_text = split_vc[-1]
    (header_x_size, header_y_size) = draw_wordwrap_text(draw, header_text, 0, 0, max_width, bold_font)
    draw.line([0, header_y_size - 2, header_x_size, header_y_size - 2], fill=(0, 0, 0, 255), width=2)
    ypos = 2 * header_y_size

    (vc_x_size, ypos) = draw_votecount_text(draw, vc, 0, ypos, max_width, regular_font, bold_font)
    ypos += header_y_size

    (x_size, ypos) = draw_wordwrap_text(draw, footer_text, 0, ypos, max_width, regular_font)

    votes = Vote.objects.select_related().filter(game=game, target=None, unvote=False, ignored=False, nolynch=False)
    if votes:
        ypos += header_y_size
        if len(votes) == 1:
            warning_text = 'Warning: There is currently 1 unresolved vote.  The votecount may be inaccurate.'
        else:
            warning_text = 'Warning: There are currently {} unresolved votes.  The votecount may be inaccurate.'.format(len(
                votes))

        (warning_x, ypos) = draw_wordwrap_text(draw, warning_text, 0, ypos, max_width, bold_font)
        x_size = max(x_size, warning_x)

    return (max(header_x_size, vc_x_size, x_size), ypos)


def check_update_game(game):
    if game.is_locked():
        return game
    else:
        game.lock()

    try:
        page_parser = PageParser.PageParser()
        new_game = page_parser.update(game)
        if new_game:
            return new_game
        game.save()
        return game
    except BaseException:
        return game


def votecount_image(request, slug):
    game = get_object_or_404(Game, slug=slug)

    key = '{}-vc-image'.format(slug)
    img_dict = cache.get(key)

    if img_dict is None:
        game = check_update_game(game)
        img = Image.new('RGBA', (800, 1024), (255, 255, 255, 0))
        (width, height) = votecount_to_image(img, game, 0, 0, 800)
        img = img.crop((0, 0, width, height))
        cache.set(key, {'size': img.size, 'data': img.tobytes()}, 120)
    else:
        img = Image.frombytes('RGBA', img_dict['size'], img_dict['data'])

    response = HttpResponse(content_type='image/png')
    img.save(response, 'PNG')  # transparency=(255, 255, 255))
    return response


def autoupdate(request):
    games = Game.objects.exclude(state='closed').order_by('-last_updated')
    for game in games:
        key = '{}-vc-image'.format(game.slug)
        cache.delete(key)  # image will regenerate on next GET
        game = check_update_game(game)
        post = game.posts.order_by('-timestamp')[:1][0]

        if datetime.now() - post.timestamp > timedelta(days=6) and game.state == 'started':
            game.status_update('Closed automatically for inactivity.')
            game.state = 'closed'
            game.save()
    return HttpResponse('Ok')


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
    players = Player.objects.select_related().filter(uid__gt='0').order_by('name').extra(select={
        'alive': 'select count(*) from main_playerstate join main_game on main_playerstate.game_id=main_game.id where main_playerstate.player_id=main_player.id and main_game.state = "started" and main_playerstate.alive=true',
        'total_games_played': 'select count(*) from main_playerstate where main_playerstate.player_id=main_player.id and main_playerstate.moderator=false and main_playerstate.spectator=false',
        'total_games_run': 'select count(*) from main_game where main_game.moderator_id=main_player.id'})[
        first_record: first_record + items_per_page]

    if not players:
        return HttpResponseRedirect('/players')

    for player in players:
        if player.total_games_played > 0:
            player.posts_per_game = player.total_posts / (1.0 * player.total_games_played)
        else:
            player.posts_per_game = 0

    return render(request, 'players.html',
                  {'players': players, 'page': page, 'total_pages': total_pages})


@login_required
def delete_alias(request, aliasid):
    alias = get_object_or_404(Alias, id=aliasid)
    if not request.user.is_superuser and request.user.profile.player != alias.player:
        return HttpResponseForbidden

    messages.add_message(request, messages.SUCCESS, 'The alias <strong>{}</strong> was deleted.'.format(alias.alias))
    player = alias.player
    alias.delete()

    return HttpResponseRedirect('/player/{}'.format(player.slug))


@login_required
def sendpms(request, slug):
    game = get_object_or_404(Game, slug=slug)
    if game.state != 'started' or not check_mod(request, game):
        return HttpResponseForbidden

    return render(request, 'sendpms.html', {'game': game})


def post_histories(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    return render(request, 'post_histories.html', {'game': game})


@login_required
def post_lynches(request, gameid, enabled):
    game = get_object_or_404(Game, id=gameid)
    if not check_mod(request, game):
        return HttpResponseForbidden

    if enabled == 'on':
        game.post_lynches = True
        messages.add_message(request, messages.SUCCESS, 'Posting of voted executes for this game is now enabled!')
    else:
        game.post_lynches = False
        messages.add_message(request, messages.SUCCESS, 'Posting of voted executes for this game is now disabled!')

    game.save()
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def ecco_mode(request, gameid, enabled):
    game = get_object_or_404(Game, id=gameid)
    if not check_mod(request, game):
        return HttpResponseForbidden

    if enabled == 'on':
        game.ecco_mode = True
        messages.add_message(request, messages.SUCCESS, 'Ecco Mode has been enabled for this game!')
    else:
        game.ecco_mode = False
        messages.add_message(request, messages.SUCCESS, 'Ecco Mode has been disabled for this game!')

    game.save()
    return HttpResponseRedirect(game.get_absolute_url())


@login_required
def post_vc(request, gameid):
    game = get_object_or_404(Game, id=gameid)
    if game.state != 'started' or not check_mod(request, game):
        return HttpResponseForbidden

    if game.last_vc_post is not None and datetime.now() - game.last_vc_post < timedelta(minutes=60) and (game.deadline and game.deadline - datetime.now() > timedelta(minutes=60)):
        messages.add_message(request, messages.ERROR, 'Votefinder has posted too recently in that game.')
    else:
        game.last_vc_post = datetime.now()
        game.save()

        game = check_update_game(game)

        vc_formatter = VotecountFormatter.VotecountFormatter(game)
        vc_formatter.go()

        dl = ForumPageDownloader.ForumPageDownloader()
        dl.reply_to_thread(game.thread_id, vc_formatter.bbcode_votecount)
        messages.add_message(request, messages.SUCCESS, 'Votecount posted.')

    return HttpResponseRedirect(game.get_absolute_url())


def votechart_all(request, gameslug):
    game = get_object_or_404(Game, slug=gameslug)
    day = GameDay.objects.get(game=game, day_number=game.current_day)
    required_votes_to_execute = int(math.floor(len(game.living_players()) / 2.0) + 1)

    vc = VoteCounter.VoteCounter()
    vc.run(game)
    vote_log = vc.get_votelog()

    return render(request, 'votechart.html',
                  {'game': game, 'showAllPlayers': True, 'startDate': day.start_post.timestamp,
                   'now': datetime.now(), 'toLynch': required_votes_to_execute,
                   'votes': vote_log, 'numVotes': len(vote_log),
                   'players': [p.player.name for p in game.living_players()],
                   'allPlayers': [p.player for p in game.living_players()]},
                  )


def votechart_player(request, gameslug, playerslug):
    game = get_object_or_404(Game, slug=gameslug)
    player = get_object_or_404(Player, slug=playerslug)
    day = GameDay.objects.get(game=game, day_number=game.current_day)
    required_votes_to_execute = int(math.floor(len(game.living_players()) / 2.0) + 1)

    vc = VoteCounter.VoteCounter()
    vc.run(game)
    vote_log = [vote for vote in vc.get_votelog() if vote['player'] == player.name]

    return render(request, 'votechart.html',
                  {'game': game, 'showAllPlayers': False, 'startDate': day.start_post.timestamp,
                   'now': datetime.now(), 'toLynch': required_votes_to_execute,
                   'votes': vote_log, 'numVotes': len(vote_log),
                   'allPlayers': [p.player for p in game.living_players()],
                   'selectedPlayer': player.name,
                   'players': [player.name]},
                  )


def dictfetchall(cursor):
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def gamechart(request):
    cursor = connections['default'].cursor()
    cursor.execute(
        'select cast(timestamp as date) as date, count(1)/count(distinct(game_id)) as activity, count(distinct(author_Id)) as posters, count(distinct(game_id)) as games, count(1) as posts from main_post group by date order by date')
    gamedata_by_date = dictfetchall(cursor)

    return render(request, 'gamechart.html',
                  {'data': gamedata_by_date, 'dataLen': len(gamedata_by_date)},
                  )


def common_games(request, slug_a, slug_b):
    player_a = get_object_or_404(Player, slug=slug_a)
    player_b = get_object_or_404(Player, slug=slug_b)
    games_a = [state.game for state in PlayerState.objects.filter(player=player_a) if not (state.moderator or state.spectator)]
    games_b = [state.game for state in PlayerState.objects.filter(player=player_b) if not (state.moderator or state.spectator)]
    common_games = [game for game in games_a if game in games_b]

    context = {
        'player_a': player_a,
        'player_b': player_b,
        'games': common_games,
    }

    return render(request, 'common_games.html', context)
