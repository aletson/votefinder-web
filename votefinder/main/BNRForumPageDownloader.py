import re

import requests

from bs4 import BeautifulSoup
from django.conf import settings
from votefinder.main.models import Game


class BNRForumPageDownloader():
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        # review if necessary

    def download(self, page):
        page_data = self.perform_download(page)

        if page_data is None:
            return None
        elif not self.needs_to_login(page_data):
            return page_data
        elif self.login_to_forum():
            page_data = self.perform_download(page)

            if not self.needs_to_login(page_data):
                return page_data
            return None
        return None

    def log_login_attempt(self):
        game = Game.objects.get(id=228)
        game.status_update('Trying to re-login to forums.  PM Alli if this happens a lot.')

    def login_to_forum(self):
        page_text = ''

        self.log_login_attempt()

        page_request = self.session.post('https://breadnroses.net/login/login',
                                         data={'login': settings.BNR_LOGIN,
                                               'password': settings.BNR_PASSWORD, '_xfRedirect': 'https://breadnroses.net'})
        page_text = page_request.text

        if self.is_logged_in_correctly(page_text):
            return True
        return False

    def needs_to_login(self, page_data):
        if re.search(re.compile(r'linkText\"\>Log in'), page_data) is None:
            return False
        return True

    def is_logged_in_correctly(self, page_data):
        if not page_data:
            raise ValueError('Login failed, no data in response from login attempt')
        if re.search(re.compile(r'linkText\"\>Log in'), page_data) is None:
            return True
        return False

    def perform_download(self, page):
        try:
            page_request = self.session.get(page)
            return page_request.text
        except BaseException:
            return None

    def reply_to_thread(self, thread, message):  # TODO
        get_url = 'https://breadnroses.net/threads/{}'.format(thread)
        post_url = 'https://breadnroses.net/threads/{}/add-reply'.format(thread)

        page_data = self.download(get_url)
        if page_data is None:
            return False  # Could not retrieve anything from the page.

        soup = BeautifulSoup(page_data, 'html.parser')

        inputs = {'message_html': message}
        for input_element in soup.find_all('input', {'value': True}):
            inputs[input_element['name']] = input_element['value']

        if not inputs['disablesmilies']:
            return False  # Thread is locked.
        inputs.pop('disablesmilies')
        inputs.pop('preview')

        self.session.post(post_url, data=inputs)


if __name__ == '__main__':
    dl = BNRForumPageDownloader()
    result = dl.download('https://breadnroses.net/threads/1012')  # noqa: WPS110
