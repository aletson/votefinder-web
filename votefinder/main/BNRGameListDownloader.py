import re

from bs4 import BeautifulSoup
from votefinder.main.models import Game

from votefinder.main import BNRForumPageDownloader


class BNRGameListDownloader():
    def __init__(self):
        self.GameList = []
        self.downloader = BNRForumPageDownloader.BNRForumPageDownloader()

    def get_game_list(self, page):
        game_raw_html = self.download_list(page)
        if not game_raw_html:
            return False

        if not self.parse_game_list(game_raw_html):
            return False

        return True

    def download_list(self, page):
        return self.downloader.download(
            'https://breadnroses.net/forums/35/page-{}'.format(page))

    def parse_game_list(self, game_raw_html):
        soup = BeautifulSoup(game_raw_html, 'html.parser')
        thread_titles = soup.find_all('div', 'structItem-title')
        for thread_title in thread_titles:
            thread = thread_title.find('a')
            if thread.text.lower().find('mafia') != -1 or thread.text.lower().find('werewolf') != 1:
                game = {'name': thread.text, 'url': thread['href'], 'tracked': self.is_game_tracked(thread['href'])}
                self.GameList.append(game)

        return True

    def is_game_tracked(self, url):
        matcher = re.compile(r'threads/.*\.(?P<threadid>\d+)').search(url)
        if matcher:
            try:
                Game.objects.all().get(thread_id=matcher.group('threadid'))
                return True
            except Game.DoesNotExist:
                pass  # noqa: WPS420

        return False
