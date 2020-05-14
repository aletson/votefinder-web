from django.conf import settings
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from votefinder.main.models import BlogPost, GameStatusUpdate, Game


class LatestRss(Feed):
    title = 'VoteFinder Updates'
    link = 'https://'+ settings.PRIMARY_DOMAIN + '/'
    author_name = 'Alli'
    feed_url = 'https://' + settings.PRIMARY_DOMAIN + '/rss'
    description = 'Changes and updates to the VoteFinder site.'
    guid = '/'

    def items(self):
        return BlogPost.objects.all().order_by('-timestamp')[:5]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.text

    def item_link(self, item):
        return 'https://' + settings.PRIMARY_DOMAIN + '/'

    def item_pubdate(self, item):
        return item.timestamp


class LatestAtom(LatestRss):
    feed_type = Atom1Feed
    subtitle = LatestRss.description


class GameStatusRss(Feed):
    title = 'VoteFinder Game Status Updates'
    link = 'https://' + settings.PRIMARY_DOMAIN + '/'
    author_name = 'Alli'
    feed_url = 'https://' + settings.PRIMARY_DOMAIN + '/game_status'
    description = 'Game status updates for games tracked by VoteFinder.'
    guid = '/'

    def items(self):
        return GameStatusUpdate.objects.all().order_by('-id')[:5]

    def item_title(self, item):
        if item.game:
            return '[%s] %s' % (item.game.name, item.message)
        return item.message

    def item_description(self, item):
        return item.message

    def item_link(self, item):
        return item.url

    def item_pubdate(self, item):
        return item.timestamp


class GameStatusAtom(GameStatusRss):
    feed_type = Atom1Feed
    subtitle = GameStatusRss.description


class SpecificGameStatusRss(Feed):
    title = 'VoteFinder Game Status Updates'
    link = 'https://' + settings.PRIMARY_DOMAIN + '/'
    author_name = 'Alli'
    feed_url = 'https://' + settings.PRIMARY_DOMAIN + '/game_status'
    description = 'Game status updates for games tracked by VoteFinder.'
    guid = '/'
    game = None

    def get_object(self, request, slug):
        self.game = get_object_or_404(Game, slug=slug)
        return self.game

    def items(self):
        return GameStatusUpdate.objects.filter(game=self.game).order_by('-id')[:5]

    def item_title(self, item):
        if item.game:
            return '[%s] %s' % (item.game.name, item.message)
        return item.message

    def item_description(self, item):
        return item.message

    def item_link(self, item):
        return item.url

    def item_pubdate(self, item):
        return item.timestamp


class SpecificGameStatusAtom(SpecificGameStatusRss):
    feed_type = Atom1Feed
    subtitle = GameStatusRss.description
