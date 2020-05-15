import re
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup, Comment
from votefinder.main.models import (Alias, Game, GameDay, Player, PlayerState,
                                    Post, Vote)

from . import ForumPageDownloader


class PageParser:
    def __init__(self):
        self.pageNumber = 0
        self.maxPages = 0
        self.gameName = ''
        self.posts = []
        self.players = []
        self.gamePlayers = []
        self.votes = []
        self.user = None
        self.downloader = ForumPageDownloader.ForumPageDownloader()

    def add_game(self, threadid, state):
        self.new_game = True
        self.state = state
        return self.download_and_update('http://forums.somethingawful.com/showthread.php?threadid={}'.format(threadid),
                                        threadid)

    def download_and_update(self, url, threadid):
        data = self.download_forum_page(url)
        if not data:
            return None

        game = self.parse_page(data, threadid)
        if not game:
            return None

        return game

    def Update(self, game):
        self.new_game = False
        page = game.currentPage
        if game.currentPage < game.maxPages:
            page = game.currentPage + 1

        return self.download_and_update(
            'http://forums.somethingawful.com/showthread.php?threadid={}&pagenumber={}'.format(game.threadId, page),
            game.threadId)

    def download_forum_page(self, url):
        return self.downloader.download(url)

    def autoresolve_vote(self, text):
        try:
            player = Player.objects.get(name__iexact=text)
            if player in self.players or player in self.gamePlayers:
                return player
        except Player.DoesNotExist:
            pass

        try:
            aliases = Alias.objects.filter(alias__iexact=text, player__in=self.players)
            if aliases:
                return aliases[0].player
        except Alias.DoesNotExist:
            pass

        try:
            aliases = Alias.objects.filter(alias__iexact=text, player__in=self.gamePlayers)
            if aliases:
                return aliases[0].player
        except Alias.DoesNotExist:
            pass

        try:
            if len(text) > 4:
                players = Player.objects.filter(name__icontains=text, name__in=[p.name for p in self.gamePlayers])
                if len(players) == 1:
                    return players[0]
        except Player.DoesNotExist:
            pass

        return None

    def search_line_for_actions(self, post, line):
        # Votes
        pattern = re.compile('##\\s*unvote|##\\s*vote[:\\s+]([^<\\r\\n]+)', re.I)
        pos = 0
        match = pattern.search(line, pos)

        while match:
            v = Vote(post=post, game=post.game, author=post.author, unvote=True)
            (targetStr,) = match.groups()
            if targetStr:
                v.targetString = targetStr.strip()
                v.target = self.autoresolve_vote(v.targetString)
                v.unvote = False

                if v.target is None and v.targetString.lower() in {'nolynch', 'no lynch', 'no execute', 'no hang', 'no cuddle', 'no lunch'}:
                    v.nolynch = True
            try:
                game = Game.objects.get(id=post.game.id)
                player_last_vote = Vote.objects.filter(game=post.game, author=post.author).last()
                current_gameday = GameDay.objects.filter(game=post.game).last()
                if game.ecco_mode is False or player_last_vote is None or player_last_vote.post_id < current_gameday.startPost_id or player_last_vote.unvote or v.unvote or PlayerState.get(game=game, player_id=player_last_vote.target).alive is False:
                    v.save()
            except Game.DoesNotExist:
                v.save()
                pass
            match = pattern.search(line, match.end())

        if post.game.is_player_mod(post.author):
            # pattern search for ##move and 3 wildcards pattern = re.compile("##\\s*move[:\\s+]([^<\\r\\n]+)", re.I
            # pattern search for ##deadline and # of hours
            pattern = re.compile(r'##\\s*deadline[:\\s+](\\d+)', re.I)
            pos = 0
            match = pattern.search(line, pos)
            while match:
                (num_hrs,) = match.groups()
                if num_hrs and num_hrs > 0:  # Check if int - or modify regex
                    num_hrs = int(num_hrs)
                    new_deadline = post.timestamp + timedelta(hours=num_hrs)
                    post.game.deadline = new_deadline
                    post.game.save()

    def read_votes(self, post):
        for quote in post.bodySoup.findAll('div', 'quote well'):
            quote.extract()
        for bold in post.bodySoup.findAll('b'):
            post_content = ''.join([str(x) for x in bold.contents])
            for line in post_content.splitlines():
                self.search_line_for_actions(post, line)

    def parse_page(self, data, threadid):
        soup = BeautifulSoup(data, 'html5lib')
        self.pageNumber = self.find_page_number(soup)
        self.maxPages = self.find_max_pages(soup)
        self.gameName = re.compile(r'\[.*?\]').sub('', self.read_thread_title(soup)).strip()

        posts = soup.find_all('table', 'post')
        if not posts:
            return None

        mod = None
        for post_node in posts:
            new_post = self.read_post_values(post_node)
            if new_post:
                if not mod:
                    mod = new_post.author

                new_post.pageNumber = self.pageNumber
                self.posts.append(new_post)
        if self.new_game and self.state == 'pregame':
            day_number = 0
        else:
            day_number = 1
            self.state = 'started'

        game, game_created = Game.objects.get_or_create(threadId=threadid,
                                                       defaults={'moderator': mod, 'name': self.gameName,
                                                                 'currentPage': 1, 'maxPages': 1, 'state': self.state,
                                                                 'added_by': self.user, 'current_day': day_number})

        if game_created:
            playerState, created = PlayerState.objects.get_or_create(game=game, player=mod,
                                                                     defaults={'moderator': True})
        else:
            self.gamePlayers = [p.player for p in game.all_players()]

        game.maxPages = self.maxPages
        game.currentPage = self.pageNumber
        game.gameName = self.gameName

        for post in self.posts:
            post.game = game
            post.save()
            self.read_votes(post)
            if post.author not in self.players:
                self.players.append(post.author)
            cur_player = post.author
            cur_player.last_post = datetime.now()
            cur_player.total_posts += 1
            cur_player.save()

        if self.new_game or game.state == 'pregame':
            defaultState = 'alive'
        else:
            defaultState = 'spectator'

        for player in self.players:
            playerState, created = PlayerState.objects.get_or_create(game=game, player=player,
                                                                     defaults={defaultState: True})

        if game_created:
            gameday = GameDay(game=game, dayNumber=day_number, startPost=self.posts[0])
            gameday.save()

        game.save()
        return game

    def find_page_number(self, soup):
        pages = soup.find('div', 'pages')
        if pages:
            curPage = pages.find(attrs={'selected': 'selected'})
            if curPage:
                return curPage['value']
            return '1'
        return '1'

    def find_max_pages(self, soup):
        pages = soup.find('div', 'pages')
        if pages:
            option_tags = pages.find_all('option')
            total_pages = len(option_tags)
            if total_pages == 0:
                return 1
            return total_pages
        return 1

    def read_thread_title(self, soup):
        title = soup.find('title')
        if title:
            return title.text[:len(title.text) - 29]
        return None

    def find_or_create_player(self, playername, playeruid):
        player, created = Player.objects.get_or_create(uid=playeruid,
                                                       defaults={'name': playername})

        if player.name != playername:
            player.name = playername
            player.save()

        return player

    def read_post_values(self, node):
        post_id = node['id'][4:]
        if post_id == '':
            return None

        try:
            post = Post.objects.get(postId=post_id)
            return None
        except Post.DoesNotExist:
            post = Post()

        post.postId = post_id
        title_node = node.find('dd', 'title')
        if title_node:
            post.avatar = str(title_node.find('img'))

        post.bodySoup = node.find('td', 'postbody')
        for quote in post.bodySoup.findAll('div', 'bbc-block'):
            quote['class'] = 'quote well'
        [img.replaceWith('<div class="embedded-image not-loaded" data-image="'+img['src']+'">Click to load image...</div>') for img in post.bodySoup.find_all('img')]  # noqa: WPS428 false positive
        comments = post.bodySoup.find_all(text=lambda text: isinstance(text, Comment))
        for match in comments:
            match.decompose()
        post.body = post.bodySoup.prettify(formatter=None)
        post.body = re.sub(r'google_ad_section_(start|end)', '', post.body)
        post_date_node = node.find('td', 'postdate')

        if post_date_node:
            date_text = post_date_node.text.replace('#', '').replace('?', '').strip()
            post.timestamp = datetime(*time.strptime(date_text, '%b %d, %Y %H:%M')[:6])
        else:
            return None

        anchor_list = post_date_node.findAll('a')
        if anchor_list:
            post.authorSearch = anchor_list[-1]['href']

        author_string = node.find('dt', 'author').text
        author_string = re.sub('<.*?>', '', author_string)
        author_string = re.sub('&\\w+?;', '', author_string).strip()

        matcher = re.compile(r'userid=(?P<uid>\d+)').search(post.authorSearch)
        if matcher:
            author_uid = matcher.group('uid')
        else:
            return None

        if author_string == 'Adbot':
            return None
        else:
            post.author = self.find_or_create_player(author_string, author_uid)

        return post
