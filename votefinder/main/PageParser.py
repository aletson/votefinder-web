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

    def Add(self, threadid, state):
        self.new_game = True
        self.state = state
        return self.DownloadAndUpdate('http://forums.somethingawful.com/showthread.php?threadid={}'.format(threadid),
                                      threadid)

    def DownloadAndUpdate(self, url, threadid):
        data = self.DownloadForumPage(url)
        if not data:
            return None

        game = self.ParsePage(data, threadid)
        if not game:
            return None

        return game

    def Update(self, game):
        self.new_game = False
        page = game.currentPage
        if game.currentPage < game.maxPages:
            page = game.currentPage + 1

        return self.DownloadAndUpdate(
            'http://forums.somethingawful.com/showthread.php?threadid={}&pagenumber={}'.format(game.threadId, page),
            game.threadId)

    def DownloadForumPage(self, url):
        return self.downloader.download(url)

    def AutoResolveVote(self, text):
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

    def SearchLineForActions(self, post, line):
        # Votes
        pattern = re.compile('##\\s*unvote|##\\s*vote[:\\s+]([^<\\r\\n]+)', re.I)
        pos = 0
        match = pattern.search(line, pos)

        while match:
            v = Vote(post=post, game=post.game, author=post.author, unvote=True)
            (targetStr,) = match.groups()
            if targetStr:
                v.targetString = targetStr.strip()
                v.target = self.AutoResolveVote(v.targetString)
                v.unvote = False

                if v.target is None and v.targetString.lower() in {'nolynch', 'no lynch', 'no execute', 'no hang', 'no cuddle', 'no lunch'}:
                    v.nolynch = True
            try:
                game = Game.objects.get(id=post.game.id)
                playersLastVote = Vote.objects.filter(game=post.game, author=post.author).last()
                currentGameDay = GameDay.objects.filter(game=post.game).last()
                if game.ecco_mode is False or playersLastVote is None or playersLastVote.post_id < currentGameDay.startPost_id or playersLastVote.unvote or v.unvote or PlayerState.get(game=game, player_id=playersLastVote.target).alive is False:
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
                (numHrs,) = match.groups()
                if numHrs and numHrs > 0:  # Check if int - or modify regex
                    numHrs = int(numHrs)
                    newDeadline = post.timestamp + timedelta(hours=numHrs)
                    post.game.deadline = newDeadline
                    post.game.save()

    def ReadVotes(self, post):
        for quote in post.bodySoup.findAll('div', 'quote well'):
            quote.extract()
        for bold in post.bodySoup.findAll('b'):
            postContent = ''.join([str(x) for x in bold.contents])
            for line in postContent.splitlines():
                self.SearchLineForActions(post, line)

    def ParsePage(self, data, threadid):
        soup = BeautifulSoup(data, 'html5lib')
        self.pageNumber = self.FindPageNumber(soup)
        self.maxPages = self.FindMaxPages(soup)
        self.gameName = re.compile(r'\[.*?\]').sub('', self.ReadThreadTitle(soup)).strip()

        posts = soup.find_all('table', 'post')
        if not posts:
            return None

        mod = None
        for postNode in posts:
            newPost = self.ReadPostValues(postNode)
            if newPost:
                if not mod:
                    mod = newPost.author

                newPost.pageNumber = self.pageNumber
                self.posts.append(newPost)
        if self.new_game and self.state == 'pregame':
            dayNumber = 0
        else:
            dayNumber = 1
            self.state = 'started'

        game, gameCreated = Game.objects.get_or_create(threadId=threadid,
                                                       defaults={'moderator': mod, 'name': self.gameName,
                                                                 'currentPage': 1, 'maxPages': 1, 'state': self.state,
                                                                 'added_by': self.user, 'current_day': dayNumber})

        if gameCreated:
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
            self.ReadVotes(post)
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

        if gameCreated:
            gameday = GameDay(game=game, dayNumber=dayNumber, startPost=self.posts[0])
            gameday.save()

        game.save()
        return game

    def FindPageNumber(self, soup):
        pages = soup.find('div', 'pages')
        if pages:
            curPage = pages.find(attrs={'selected': 'selected'})
            if curPage:
                return curPage['value']
            return '1'
        return '1'

    def FindMaxPages(self, soup):
        pages = soup.find('div', 'pages')
        if pages:
            option_tags = pages.find_all('option')
            total_pages = len(option_tags)
            if total_pages == 0:
                return 1
            return total_pages
        return 1

    def ReadThreadTitle(self, soup):
        title = soup.find('title')
        if title:
            return title.text[:len(title.text) - 29]
        return None

    def FindOrCreatePlayer(self, playername, playeruid):
        player, created = Player.objects.get_or_create(uid=playeruid,
                                                       defaults={'name': playername})

        if player.name != playername:
            player.name = playername
            player.save()

        return player

    def ReadPostValues(self, node):
        postId = node['id'][4:]
        if postId == '':
            return None

        try:
            post = Post.objects.get(postId=postId)
            return None
        except Post.DoesNotExist:
            post = Post()

        post.postId = postId
        titleNode = node.find('dd', 'title')
        if titleNode:
            post.avatar = str(titleNode.find('img'))

        post.bodySoup = node.find('td', 'postbody')
        for quote in post.bodySoup.findAll('div', 'bbc-block'):
            quote['class'] = 'quote well'
        [img.replaceWith('<div class="embedded-image not-loaded" data-image="'+img['src']+'">Click to load image...</div>') for img in post.bodySoup.find_all('img')]  # noqa: WPS428 false positive
        comments = post.bodySoup.find_all(text=lambda text: isinstance(text, Comment))
        for match in comments:
            match.decompose()
        post.body = post.bodySoup.prettify(formatter=None)
        post.body = re.sub(r'google_ad_section_(start|end)', '', post.body)
        postDateNode = node.find('td', 'postdate')

        if postDateNode:
            dateText = postDateNode.text.replace('#', '').replace('?', '').strip()
            post.timestamp = datetime(*time.strptime(dateText, '%b %d, %Y %H:%M')[:6])
        else:
            return None

        anchorList = postDateNode.findAll('a')
        if anchorList:
            post.authorSearch = anchorList[-1]['href']

        authorString = node.find('dt', 'author').text
        authorString = re.sub('<.*?>', '', authorString)
        authorString = re.sub('&\\w+?;', '', authorString).strip()

        matcher = re.compile(r'userid=(?P<uid>\d+)').search(post.authorSearch)
        if matcher:
            authorUid = matcher.group('uid')
        else:
            return None

        if authorString == 'Adbot':
            return None
        else:
            post.author = self.FindOrCreatePlayer(authorString, authorUid)

        return post
