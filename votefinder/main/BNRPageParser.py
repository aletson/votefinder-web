import re
from datetime import datetime

from bs4 import BeautifulSoup
from votefinder.main.models import (Game, GameDay, Player, PlayerState,
                                    Post)

from votefinder.main import BNRForumPageDownloader, PostParser


class BNRPageParser:
    def __init__(self):
        self.pageNumber = 0
        self.maxPages = 0
        self.gameName = ''
        self.posts = []
        self.players = []
        self.gamePlayers = []
        self.votes = []
        self.user = None
        self.downloader = BNRForumPageDownloader.BNRForumPageDownloader()

    def add_game(self, threadid, state):
        self.new_game = True
        self.state = state
        return self.download_and_update('https://breadnroses.net/threads/{}'.format(threadid),
                                        threadid)

    def download_and_update(self, url, threadid):
        page_html = self.download_forum_page(url)
        if not page_html:
            return None

        game = self.parse_page(page_html, threadid)
        if not game:
            return None

        return game

    def update(self, game):
        self.new_game = False
        page = game.current_page
        if game.current_page < game.max_pages:
            page = game.current_page + 1

        return self.download_and_update(
            'https://breadnroses.net/threads/{}/page-{}'.format(game.thread_id, page),
            game.thread_id)

    def download_forum_page(self, url):
        return self.downloader.download(url)

    def parse_page(self, page_html, threadid):
        soup = BeautifulSoup(page_html, 'html5lib')
        self.pageNumber = self.find_page_number(soup)
        self.maxPages = self.find_max_pages(soup)
        self.gameName = re.compile(r'\[.*?\]').sub('', self.read_thread_title(soup)).strip()

        posts = soup.find_all('article', 'message--post')
        if not posts:
            return None

        mod = None
        for post_node in posts:
            new_post = self.read_post_values(post_node)
            if new_post:
                if not mod:
                    mod = new_post.author

                new_post.page_number = self.pageNumber
                self.posts.append(new_post)
        if self.new_game and self.state == 'pregame':
            day_number = 0
        else:
            day_number = 1
            self.state = 'started'

        game, game_created = Game.objects.get_or_create(thread_id=threadid,
                                                        defaults={'moderator': mod, 'name': self.gameName,
                                                                  'current_page': 1, 'max_pages': 1, 'state': self.state,
                                                                  'added_by': self.user, 'current_day': day_number})

        if game_created:
            player_state, created = PlayerState.objects.get_or_create(game=game, player=mod,
                                                                      defaults={'moderator': True})
        else:
            self.gamePlayers = [player.player for player in game.all_players()]

        game.max_pages = self.maxPages
        game.current_page = self.pageNumber
        game.gameName = self.gameName

        for post in self.posts:
            post.game = game
            post.save()
            PostParser.read_votes(post, self.gamePlayers, self.players)
            if post.author not in self.players:
                self.players.append(post.author)
            cur_player = post.author
            cur_player.last_post = datetime.now()
            cur_player.total_posts += 1
            cur_player.save()

        if self.new_game or game.state == 'pregame':
            default_state = 'alive'
        else:
            default_state = 'spectator'

        for player in self.players:
            player_state, created = PlayerState.objects.get_or_create(game=game, player=player,
                                                                      defaults={default_state: True})

        if game_created:
            gameday = GameDay(game=game, day_number=day_number, start_post=self.posts[0])
            gameday.save()

        game.save()
        return game

    def find_page_number(self, soup):
        pages = soup.find('div', 'pageNav-page--current')
        if pages:
            current_page = int(pages.find('a').get_text())
            if current_page:
                return current_page['value']
            return '1'
        return '1'

    def find_max_pages(self, soup):
        pages = soup.find('div', 'pageNav-page')
        if pages:
            total_pages = int(pages[-1].find('a').getText())
            if total_pages == 0:
                return 1
            return total_pages
        return 1

    def read_thread_title(self, soup):
        title = soup.find('title')
        if title:
            return title.text[:len(title.text) - 18]  # " | Bread and Roses"
        return None

    def find_or_create_player(self, playername, playeruid):
        player, created = Player.objects.get_or_create(bnr_uid=playeruid,
                                                       defaults={'name': playername})

        if player.name != playername:
            player.name = playername
            player.save()

        return player

    def read_post_values(self, node):
        post_id = node['id'][8:]
        if post_id == '':
            return None

        try:
            post = Post.objects.get(post_id=post_id)
            return None
        except Post.DoesNotExist:
            post = Post()

        post.post_id = post_id
        title_node = node.find('div', 'message-avatar')
        if title_node:
            post.avatar = str(title_node.find('img'))

        post.bodySoup = node.find('div', 'bbWrapper')
        for quote in post.bodySoup.findAll('div', 'bbCodeBlock--quote'):
            quote['class'] = 'quote well'
        [img.replaceWith('<div class="embedded-image not-loaded" data-image="{}">Click to load image...</div>'.format(img['src'])) for img in post.bodySoup.find_all('img')]  # noqa: WPS428 false positive
        post.body = post.bodySoup.prettify(formatter=None)
        post_date_node = node.find('time', 'u-dt').get('datetime')

        if post_date_node:
            post.timestamp = post_date_node
        else:
            return None

        author_string = node.get('data-author')
        author_string = re.sub(r'<.*?>', '', author_string)
        author_string = re.sub(r'&\w+?;', '', author_string).strip()
        author_uid = node.find('a', 'avatar').get('data-user-id')

        post.author = self.find_or_create_player(author_string, author_uid)

        return post
