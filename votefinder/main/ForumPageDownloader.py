import re

import requests

from bs4 import BeautifulSoup
from django.conf import settings
from votefinder.main.models import Game


class ForumPageDownloader():
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        # we must set this, SA blocks the default UA

    def download(self, page):
        data = self.perform_download(page)

        if data is None:
            return None
        elif not self.needs_to_login(data):
            return data
        elif self.login_to_forum():
            data = self.perform_download(page)

            if not self.needs_to_login(data):
                return data
            return None
        return None

    def log_login_attempt(self):
        g = Game.objects.get(id=228)
        g.status_update('Trying to re-login to forums.  PM Alli if this happens a lot.')

    def login_to_forum(self):
        data = ''

        self.log_login_attempt()

        page_request = self.session.post('https://forums.somethingawful.com/account.php',
                                         data={'action': 'login', 'username': settings.SA_LOGIN,
                                               'password': settings.SA_PASSWORD, 'secure_login': ''})
        data = page_request.text

        if self.is_logged_in_correctly(data):
            return True
        return False

    def needs_to_login(self, data):
        if re.search(re.compile(r'\*\*\* LOG IN \*\*\*'), data) is None:
            return False
        return True

    def is_logged_in_correctly(self, data):
        if not data:
            raise ValueError('Login failed, no data in response from login attempt')
        if re.search(re.compile(r'Login with username and password'), data) is None:
            return True
        return False

    def perform_download(self, page):
        try:
            page_request = self.session.get(page)
            data = page_request.text
            return data
        except BaseException:
            return None

    def reply_to_thread(self, thread, message):
        get_url = 'https://forums.somethingawful.com/newreply.php?action=newreply&threadid={}'.format(thread)
        post_url = 'https://forums.somethingawful.com/newreply.php?action=newreply'

        data = self.download(get_url)
        if data is None:
            return

        soup = BeautifulSoup(data, 'html.parser')

        inputs = {'message': message}
        for i in soup.find_all('input', {'value': True}):
            inputs[i['name']] = i['value']

        if not inputs['disablesmilies']:
            # Thread is locked!
            return False
        del inputs['disablesmilies']
        del inputs['preview']

        self.session.post(post_url, data=inputs)


if __name__ == '__main__':
    dl = ForumPageDownloader()
    result = dl.download('https://forums.somethingawful.com/showthread.php?threadid=3552086')
