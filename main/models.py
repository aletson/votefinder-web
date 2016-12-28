from django.db import models
from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
import re
from datetime import datetime, timedelta
import thread
from oauth import oauth
from oauthtwitter import OAuthApi
import random
from urllib2 import urlopen, Request, HTTPError
from urllib import quote
from simplejson import loads
import bitly
from django.db.models import signals

DETAIL_LEVEL_CHOICES = (
    ( 1, 'Brief' ),
    ( 2, 'Medium' ),
    ( 3, 'Detailed' ),
)

def SlugifyUniquely(value, model, slugfield="slug"):
	suffix = 1
	potential = base = slugify(value)[:45]
	while True:
		if suffix > 1:
			potential = "-".join([base, str(suffix)])
		if not model.objects.filter(**{slugfield: potential}).count():
			return potential
		suffix += 1

class Player(models.Model):
	name	= models.CharField(max_length=255, unique=True, db_index=True)
	uid 	= models.IntegerField(unique=True, db_index=True)
	slug	= models.SlugField()

	def __unicode__(self):
		return self.name

	def get_absolute_url(self):
		return '/player/%s' % self.slug

	def save(self, *args, **kwargs):
		if not self.id:
			self.slug = SlugifyUniquely(self.name, self.__class__)
		super(Player, self).save(*args, **kwargs) 

	def current_games(self):
		return PlayerState.objects.filter(player=self, game__closed=False, spectator=False)

	def closed_games(self):
		return PlayerState.objects.filter(player=self, game__closed=True)

class VotecountTemplate(models.Model):
	creator				= models.ForeignKey(Player, editable=False)
	name				= models.CharField(max_length=256)
	shared				= models.BooleanField(default=False)
	system_default		= models.BooleanField(editable=False)

	overall				= models.TextField()
	single_line			= models.CharField(max_length=256)
	deadline_exists		= models.CharField(max_length=256)
	deadline_not_set	= models.CharField(max_length=256)
	before_vote			= models.CharField(max_length=256, blank=True)
	after_vote			= models.CharField(max_length=256, blank=True)
	before_unvote 		= models.CharField(max_length=256, blank=True)
	after_unvote		= models.CharField(max_length=256, blank=True)
	before_unvoted_vote = models.CharField(max_length=256, blank=True)
	after_unvoted_vote	= models.CharField(max_length=256, blank=True)
	detail_level		= models.IntegerField(choices=DETAIL_LEVEL_CHOICES, default=3)
	hide_zero_votes		= models.BooleanField(default=False)
	full_tick			= models.CharField(max_length=256, default="https://votefinder.org/t.png")
	empty_tick			= models.CharField(max_length=256, default="https://votefinder.org/te.png")

	def __unicode__(self):
		if self.system_default:
			return 'DEFAULT: %s [by %s]' % (self.name, self.creator)
		elif self.shared:
			return 'SHARED: %s [by %s]' % (self.name, self.creator)
		else:
			return '%s [by %s]' % (self.name, self.creator)

def twitter_in_bg(msg):
	consumer_key = "r11W5M2m2tdNtcknWSjNKw"
	consumer_secret = "zSd0vCV2mTcWVyKfAKiIcm6gdzozLEVMjXXpT51XV3c"
	oauth_token = "166303978-z0Dp7pAoKrgs2ZjN7rCmwVmd9zum4LaUNjH5fzhJ"
	oauth_token_secret = "YK7cOAF7HcSbvn43EPGBgSXyQ5RWIaruYAfTz3lNpwE"

	twitter = OAuthApi(consumer_key, consumer_secret, oauth_token, oauth_token_secret)
	twitter.UpdateStatus(msg)

class Game(models.Model):
	name 		= models.CharField(max_length=255) 
	threadId 	= models.IntegerField(unique=True, db_index=True)
	moderator 	= models.ForeignKey(Player, related_name='moderatingGames')
	lastUpdated 	= models.DateTimeField(auto_now=True, auto_now_add=True)
	maxPages 	= models.IntegerField()
	currentPage 	= models.IntegerField()
	slug		= models.SlugField()
	locked_at	= models.DateTimeField(null=True, blank=True)
	closed		= models.BooleanField(default=False)
	deadline	= models.DateTimeField(null=True, blank=True)
	template	= models.ForeignKey(VotecountTemplate, null=True, blank=True)
	added_by	= models.ForeignKey(User)
	timezone	= models.CharField(max_length=128, default='US/Eastern')
	post_lynches 	= models.BooleanField(default=False)
	ecco_mode	= models.BooleanField(default=False)
	last_vc_post 	= models.DateTimeField(null=True, blank=True)
	is_big		= models.BooleanField(default=False)
	current_day	= models.IntegerField(default=1)
	living_count	= models.IntegerField(default=0)
	players_count	= models.IntegerField(default=0)

	def update_counts(self):
		self.players_count = self.count_players()
		self.living_count = len(self.living_players())
		self.is_big = True if self.players_count > 16 else False

		days = self.days.order_by("-id")
		if len(days) > 0:
			self.current_day = days[0].dayNumber

	def status_update(self, message):
		self.status_update_noncritical(message)
		tag =  "".join([w.capitalize() for w in re.split(re.compile("[\W_-]*"), self.slug)])
		thread.start_new_thread(twitter_in_bg, ('#%s %s' % (tag, message),))

	def status_update_noncritical(self, message):
		u = GameStatusUpdate(game=self, message=message)
		u.save()

	def is_locked(self):
		if self.locked_at is None or datetime.now() - self.locked_at > timedelta(minutes=1):
			return False
		else:
			return True
		
	def lock(self, *args, **kwargs):
		self.locked_at = datetime.now()
		super(Game, self).save(*args, **kwargs) 

	def __unicode__(self): 
		return self.name
	
	def save(self, *args, **kwargs):
		if not self.id:
			filtered_name = re.compile(r"[:\.-].+").sub("", self.name.lower())
			filtered_name = filtered_name.replace("mini-mafia", "")
			filtered_name = filtered_name.replace("mafia", "")
			filtered_name = filtered_name.replace("mini", "")
			if filtered_name.strip() == "":
				self.slug = SlugifyUniquely(self.name.strip(), self.__class__)
			else:
				self.slug = SlugifyUniquely(filtered_name.strip(), self.__class__)
		self.locked_at = None
		self.update_counts()
		super(Game, self).save(*args, **kwargs) 
		
	def get_absolute_url(self):
		return '/game/%s' % self.slug
   
	def count_players(self):
		return self.players.filter(spectator=False, moderator=False).count()
		
	def all_players(self):
		return sorted(self.players.select_related(depth=1).filter(spectator=False, moderator=False), key=lambda p: p.player.name.lower())
	
	def living_players(self):
		return sorted(self.players.select_related(depth=1).filter(alive=True), key=lambda p: p.player.name.lower())

	def dead_players(self):
		return sorted(self.players.select_related(depth=1).filter(alive=False, moderator=False, spectator=False), key=lambda p: p.player.name.lower())

	def spectators(self):
		return sorted(self.players.select_related(depth=1).filter(spectator=True), key=lambda p: p.player.name.lower())

	def moderators(self):
		return sorted(self.players.select_related(depth=1).filter(moderator=True), key=lambda p: p.player.name.lower())

	def is_player_mod(self, player):
		try:
			user_state = PlayerState.objects.get(game=self, player=player)
			if user_state.moderator:
				return True
		except PlayerState.DoesNotExist:
			pass
		return False

	def is_user_mod(self, user):
		if user.is_superuser:
			return True
		elif user.is_authenticated():
			return self.is_player_mod(user.profile.player)
		else:
			return False

class Comment(models.Model):
	player		= models.ForeignKey(Player)
	game		= models.ForeignKey(Game)
	timestamp	= models.DateTimeField(auto_now_add=True)
	comment		= models.CharField(max_length=4096, blank=True, null=True)
	
	def __unicode__(self):
		return "%s: %s" % (self.player, self.comment[:100])

class PlayerState(models.Model):
	game		= models.ForeignKey(Game, related_name='players')
	player		= models.ForeignKey(Player, related_name='games')
	spectator	= models.BooleanField(default=False)
	alive		= models.BooleanField(default=False)
	moderator	= models.BooleanField(default=False)

	def set_moderator(self):
		(self.spectator, self.moderator, self.alive) = (False, True, False)

	def set_alive(self):
		(self.spectator, self.moderator, self.alive) = (False, False, True)
	
	def set_dead(self):
		(self.spectator, self.moderator, self.alive) = (False, False, False)
	
	def set_spectator(self):
		(self.spectator, self.moderator, self.alive) = (True, False, False)

	def state(self):
		if self.moderator:
			return "Moderator"
		elif self.spectator: 
			return "Spectator"
		elif self.alive:
			return "Alive"
		else:
			return "Dead"

	def __unicode__(self):
		return "%s [%s]" % (self.player, self.state())

class Alias(models.Model):
	player 		= models.ForeignKey(Player)
	alias 		= models.CharField(max_length=255)

	def __unicode__(self):
		return self.alias

	class Meta:
		verbose_name_plural = "Aliases"

class Post(models.Model):
	postId 		= models.IntegerField(unique=True, db_index=True)
	timestamp 	= models.DateTimeField()
	author 		= models.ForeignKey(Player, related_name="posts")
	authorSearch = models.CharField(max_length=256)
	body 		= models.TextField()
	avatar 		= models.CharField(max_length=256)
	pageNumber 	= models.IntegerField()
	game 		= models.ForeignKey(Game, related_name="posts")

	def __unicode__(self):
		return "%s at %s" % ( self.author.name, self.timestamp )

class PrivMsg(models.Model):
	game		= models.ForeignKey(Game, related_name="pms")
	target		= models.ForeignKey(Player, related_name="pms_received")
	author		= models.ForeignKey(Player, related_name="pms_sent")
	subject		= models.CharField(max_length=85)
	icon		= models.CharField(max_length=10)
	sent		= models.BooleanField(default=False)

class Vote(models.Model):
	post 		= models.ForeignKey(Post, related_name='votes', db_index=True)
	game		= models.ForeignKey(Game, related_name='votes', db_index=True)
	author		= models.ForeignKey(Player, related_name='votes')
	target 		= models.ForeignKey(Player, related_name='target_of_votes', null=True)
	targetString = models.CharField(max_length=256)
	unvote 		= models.BooleanField(default=False)
	ignored		= models.BooleanField(default=False)
	manual		= models.BooleanField(default=False)
	nolynch		= models.BooleanField(default=False)

	def __unicode__(self):
		if self.unvote:
			return "%s unvotes" % self.author
		else:
			return "%s votes %s" % (self.author, self.targetString)

def shorten(url):
	try:
		api = bitly.Api(login='soru', apikey='R_7d78eb0cfe6994ee6084b35eba2f20c4')
		return api.shorten(url)
	except:
		pass

	try:
		data = urlopen(Request('http://goo.gl/api/url', 'url=%s' % quote(url), {'User-Agent':'toolbar'}))
		json = loads(data.read())
		return json['short_url']
	except:
		pass

	return None

class GameStatusUpdate(models.Model):
	timestamp	= models.DateTimeField(auto_now=True)
	game		= models.ForeignKey(Game)
	message		= models.CharField(max_length=1024)
	url		= models.CharField(max_length=255)

	def save(self, *args, **kwargs):
		if not self.id:
			postUrl = "http://forums.somethingawful.com/showthread.php?goto=post&postid=%s" % self.game.posts.all().order_by("-id")[0].postId
			url = shorten(postUrl)
			if url == None:
				self.url = postUrl
			else:
				self.url = url

		super(GameStatusUpdate, self).save(*args, **kwargs) 


class BlogPost(models.Model):
	author 		= models.ForeignKey(User)
	title		= models.CharField(max_length=255)
	text		= models.TextField()
	timestamp	= models.DateTimeField(auto_now=True)

	def __unicode__(self):
		return self.title

	def get_absolute_url(self):
		return '/'
	
class UserProfile(models.Model):
	player		= models.ForeignKey(Player, unique=True)
	user		= models.OneToOneField(User, related_name="profile")
	registered	= models.DateTimeField(auto_now=True)

	def __unicode__(self):
		return self.player.name

class GameDay(models.Model):
	game		= models.ForeignKey(Game, related_name='days', db_index=True)
	dayNumber	= models.IntegerField(default=1)
	startPost	= models.ForeignKey(Post)
	notified	= models.BooleanField(default=False)
	
	def __unicode__(self):
		return "Day %s of %s" % (self.dayNumber, self.game)

class CookieStore(models.Model):
	cookie 		= models.TextField()

class AddPlayerForm(forms.Form):
	name		= forms.CharField()
	
	def clean_name(self):
		name = self.cleaned_data['name']
		try:
			self.player = Player.objects.get(name=name)
		except Player.DoesNotExist:
			raise forms.ValidationError("No player by that name.")

		return self.player.name

class AddCommentForm(forms.Form):
	comment		= forms.CharField(widget=forms.widgets.Textarea(), required=False) 

class VotecountTemplateForm(ModelForm):
	class Meta:
		model = VotecountTemplate
		fields = '__all__'

class LynchMessage(models.Model):
	text = models.CharField(max_length=512)

	def __unicode__(self):
		return self.text
