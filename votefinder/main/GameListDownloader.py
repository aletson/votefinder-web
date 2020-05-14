import re

from bs4 import BeautifulSoup
from votefinder.main.models import Game

from . import ForumPageDownloader


class GameListDownloader():
    def __init__(self):
        self.GameList = []
        self.downloader = ForumPageDownloader.ForumPageDownloader()

    def GetGameList(self, page):
        data = self.DownloadList(page)
        if not data:
            return False

        if not self.ParseGameList(data):
            return False

        return True

    def DownloadList(self, page):
        return self.downloader.download(
            'http://forums.somethingawful.com/forumdisplay.php?forumid=103&pagenumber={}'.format(page))

    def ParseGameList(self, data):
        soup = BeautifulSoup(data, 'html.parser')

        for thread in soup.find_all('a', 'thread_title'):
            if thread.text.lower().find('mafia') != -1:
                game = {'name': thread.text, 'url': thread['href'], 'tracked': self.IsGameTracked(thread['href'])}
                self.GameList.append(game)

        return True

    def IsGameTracked(self, url):
        matcher = re.compile(r'threadid=(?P<threadid>\d+)').search(url)
        if matcher:
            try:
                Game.objects.all().get(threadId=matcher.group('threadid'))
                return True
            except Game.DoesNotExist:
                pass

        return False
