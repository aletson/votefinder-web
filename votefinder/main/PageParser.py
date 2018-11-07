import time
from datetime import datetime, timedelta
from BeautifulSoup import BeautifulSoup
from BeautifulSoup import Comment
from ForumPageDownloader import ForumPageDownloader
from votefinder.main.models import *


class PageParser:
    def __init__(self):
        self.pageNumber = 0
        self.maxPages = 0
        self.gameName = ""
        self.posts = []
        self.players = []
        self.gamePlayers = []
        self.votes = []
        self.user = None
        self.downloader = ForumPageDownloader()

    def Add(self, threadid):
        self.new_game = True
        return self.DownloadAndUpdate("http://forums.somethingawful.com/showthread.php?threadid=%s" % threadid,
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
            "http://forums.somethingawful.com/showthread.php?threadid=%s&pagenumber=%s" % (game.threadId, page),
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
            if len(aliases) > 0:
                return aliases[0].player
        except Alias.DoesNotExist:
            pass

        try:
            aliases = Alias.objects.filter(alias__iexact=text, player__in=self.gamePlayers)
            if len(aliases) > 0:
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
        pattern = re.compile("##\\s*unvote|##\\s*vote[:\\s+]([^<\\r\\n]+)", re.I)
        pos = 0
        match = pattern.search(line, pos)

        while match:
            v = Vote(post=post, game=post.game, author=post.author, unvote=True)
            (targetStr,) = match.groups()
            if targetStr:
                v.targetString = targetStr.strip()
                v.target = self.AutoResolveVote(v.targetString)
                v.unvote = False

                if v.target == None and (v.targetString.lower() == "nolynch" or v.targetString.lower() == "no lynch" or v.targetString.lower() == "no execute" or v.targetString.lower() == "no cuddle"):
                    v.nolynch = True
            try:
                game = Game.objects.get(id=post.game.id)
                playersLastVote = Vote.objects.filter(game=post.game, author=post.author).last()
                currentGameDay = GameDay.objects.filter(game=post.game).last()
                if game.ecco_mode == False or playersLastVote == None or playersLastVote.post_id < currentGameDay.startPost_id or playersLastVote.unvote == True or v.unvote == True or PlayerState.get(
                        game=game, player_id=playersLastVote.target).alive == False:
                    v.save()
            except Game.DoesNotExist:
                v.save()
                pass
            match = pattern.search(line, match.end())

        if post.game.is_user_mod(post.author):
            # pattern search for ##move and 3 wildcards pattern = re.compile("##\\s*move[:\\s+]([^<\\r\\n]+)", re.I
            # pattern search for ##deadline and # of hours
            pattern = re.compile("##\\s*deadline[:\\s+](\\d+)", re.I)
            pos = 0
            match = pattern.search(line,pos)
            while match:
                (numHrs,) = match.groups()
                if numHrs and numHrs > 0: # Check if int - or modify regex
                    numHrs = int(numHrs)
                    newDeadline = post.timestamp + timedelta(hours=numHrs)
                    post.game.deadline = newDeadline
                    post.game.save()
                                

    def ReadVotes(self, post):
        for quote in post.bodySoup.findAll("div", "quote well"):
            quote.extract()
        for bold in post.bodySoup.findAll("b"):
            content = "".join([str(x) for x in bold.contents])
            for line in content.splitlines():
                self.SearchLineForActions(post, line)

    def ParsePage(self, data, threadid):
        soup = BeautifulSoup(data)

        self.pageNumber = self.FindPageNumber(soup)
        self.maxPages = self.FindMaxPages(soup)
        self.gameName = re.compile(r"\[.*?\]").sub("", self.ReadThreadTitle(soup)).strip()

        posts = soup.findAll("table", "post")
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

        game, gameCreated = Game.objects.get_or_create(threadId=threadid,
                                                       defaults={'moderator': mod, 'name': self.gameName,
                                                                 'currentPage': 1, 'maxPages': 1,
                                                                 'added_by': self.user})

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

            if not post.author in self.players:
                self.players.append(post.author)
            cur_player = post.author
            cur_player.last_post = datetime.now()
            cur_player.total_posts += 1
            cur_player.save()

        if self.new_game or self.pageNumber == 1:
            defaultState = 'alive'
        else:
            defaultState = 'spectator'

        for player in self.players:
            playerState, created = PlayerState.objects.get_or_create(game=game, player=player,
                                                                     defaults={defaultState: True})

        if gameCreated:
            gameday = GameDay(game=game, dayNumber=1, startPost=self.posts[0])
            gameday.save()

        game.save()
        return game

    def FindPageNumber(self, soup):
        pages = soup.find("div", "pages")
        if pages:
            curPage = pages.find(attrs={"selected": "selected"})
            if curPage:
                return curPage['value']
            else:
                return "1"

        return "1"

    def FindMaxPages(self, soup):
        pages = soup.find("div", "pages")
        if pages:
            option_tags = pages.findAll("option")
            total_pages = len(option_tags)
            if total_pages == 0:
                return 1
            else:
                return total_pages
        else:
            return 1

    def ReadThreadTitle(self, soup):
        title = soup.find("title")
        if title:
            return title.text[:len(title.text) - 29]
        else:
            return None

    def FindOrCreatePlayer(self, playerName, playerUid):
        player, created = Player.objects.get_or_create(uid=playerUid,
                                                       defaults={'name': playerName})

        if player.name != playerName:
            player.name = playerName
            player.save()

        return player

    def ReadPostValues(self, node):
        postId = node["id"][4:]
        if postId == '':
            return None

        try:
            post = Post.objects.get(postId=postId)
            return None
        except Post.DoesNotExist:
            post = Post()

        post.postId = postId
        titleNode = node.find("dd", "title")
        if titleNode:
            post.avatar = unicode(titleNode.find("img"))

        post.bodySoup = node.find("td", "postbody")
        for quote in post.bodySoup.findAll("div", "bbc-block"):
		    quote['class'] = "quote well"
        [img.extract() for img in post.bodySoup.findAll("img")]
        [comment.extract() for comment in post.bodySoup.findAll(text=lambda text: isinstance(text, Comment))]
        post.body = "".join([str(x) for x in post.bodySoup.contents]).strip()

        postDateNode = node.find("td", "postdate")
        if postDateNode:
            dateText = postDateNode.text.replace("#", "").replace("?", "").strip()
            post.timestamp = datetime(*time.strptime(dateText, "%b %d, %Y %H:%M")[:6])
        else:
            return None

        anchorList = postDateNode.findAll("a")
        if len(anchorList) > 0:
            post.authorSearch = anchorList[-1]["href"]

        authorString = node.find("dt", "author").text
        authorString = re.sub("<.*?>", "", authorString)
        authorString = re.sub("&\\w+?;", "", authorString).strip()

        matcher = re.compile("userid=(?P<uid>\d+)").search(post.authorSearch)
        if matcher:
            authorUid = matcher.group('uid')
        else:
            return None

        if authorString == "Adbot":
            return None
        else:
            post.author = self.FindOrCreatePlayer(authorString, authorUid)

        return post
