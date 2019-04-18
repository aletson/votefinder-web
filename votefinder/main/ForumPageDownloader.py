import requests
from datetime import datetime

from django.conf import settings

from bs4 import BeautifulSoup
from votefinder.main.models import *


class ForumPageDownloader():
    def __init__(self):
        self.session = requests.Session()

    def download(self, page):
        data = self.PerformDownload(page)

        if data is None:
            return None
        elif not self.IsNeedToLogInPage(data):
            return data
        elif self.LoginToForum():
            data = self.PerformDownload(page)

            if not self.IsNeedToLogInPage(data):
                return data
            else:
                return None
        else:
            return None

    def LogLoginAttempt(self):
        g = Game.objects.get(id=228)
        g.status_update("Trying to re-login to forums.  PM soru if this happens a lot.")

    def LoginToForum(self):
        data = ""

        self.LogLoginAttempt()

        try:
            page_request = self.session.get("https://forums.somethingawful.com/account.php",
                                     params={action: 'login', username: settings.SA_LOGIN, password: settings.SA_PASSWORD,
                                              secure_login: ''})
            data = page_request.text()
        except URLError:
            return False

        if self.IsLoggedInCorrectlyPage(data):
            return True
        else:
            return False

    def IsNeedToLogInPage(self, data):
        if re.search(re.compile(r"Sorry, you must be a registered forums member to view this page"), data) == None:
            return False
        else:
            return True

    def IsLoggedInCorrectlyPage(self, data):
        if re.search(re.compile(r"Login with username and password"), data) == None:
            return True
        else:
            return False

    def PerformDownload(self, page):
        try:
            page_request = self.session.get(page)
            data = page_request.text()
            raise AppError(data)
            return data
        except:
            raise
            return None

    def ReplyToThread(self, thread, message):
        getUrl = "https://forums.somethingawful.com/newreply.php?action=newreply&threadid=%s" % thread
        postUrl = "https://forums.somethingawful.com/newreply.php?action=newreply"

        data = self.download(getUrl)
        if data is None:
            return

        soup = BeautifulSoup(data, 'html.parser')

        inputs = {'message': message}
        for i in soup.find_all('input', {'value': True}):
            inputs[i['name']] = i['value']

        del inputs['disablesmilies']
        del inputs['preview']

        r = self.session.post(postUrl, data=inputs)
        result = r.text()


if __name__ == "__main__":
    dl = ForumPageDownloader()
    result = dl.download("https://forums.somethingawful.com/showthread.php?threadid=3552086")
