import re

from bs4 import BeautifulSoup
from votefinder.main.models import Game

from . import ForumPageDownloader


class GameListDownloader():
    def __init__(self):
        self.GameList = []
        self.downloader = ForumPageDownloader.ForumPageDownloader()

    def get_game_list(self, page):
        game_raw_html = self.download_list(page)
        if not game_raw_html:
            return False

        if not self.parse_game_list(game_raw_html):
            return False

        return True

    def download_list(self, page):
        return self.downloader.download(
            'http://forums.somethingawful.com/forumdisplay.php?forumid=103&pagenumber={}'.format(page))

    def parse_game_list(self, game_raw_html):
        soup = BeautifulSoup(game_raw_html, 'html.parser')

        for thread in soup.find_all('a', 'thread_title'):
            if thread.text.lower().find('mafia') != -1:
                game = {'name': thread.text, 'url': thread['href'], 'tracked': self.is_game_tracked(thread['href'])}
                self.GameList.append(game)

        return True

    def is_game_tracked(self, url):
        matcher = re.compile(r'threadid=(?P<threadid>\d+)').search(url)
        if matcher:
            try:
                Game.objects.all().get(thread_id=matcher.group('threadid'))
                return True
            except Game.DoesNotExist:
                pass  # noqa: WPS420

        return False
