import _pickle as pickle
import http.cookiejar as cookielib
from urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen
from datetime import datetime

from django.conf import settings
from pytz import timezone

from bs4 import BeautifulSoup
from votefinder.main.models import *


class ForumPageDownloader():
    def __init__(self):
        self.cj = cookielib.CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cj))
        self.LoadCookies()

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
        with open("/tmp/logins.txt", "a") as f:
            f.write("%s\n" % timezone(settings.TIME_ZONE).localize(datetime.now()).astimezone(
                timezone('US/Pacific')).ctime())

        g = Game.objects.get(id=228)
        g.status_update("Trying to re-login to forums.  PM soru if this happens a lot.")

    def LoginToForum(self):
        data = ""

        self.LogLoginAttempt()

        try:
            usock = self.opener.open("https://forums.somethingawful.com/account.php",
                                     urllib.urlencode(
                                         dict(action='login', username=settings.SA_LOGIN, password=settings.SA_PASSWORD,
                                              secure_login="")))
            data = usock.read()
            usock.close()
        except URLError:
            return False

        if self.IsLoggedInCorrectlyPage(data):
            self.SaveCookies()
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
            usock = self.opener.open(page)
            data = usock.read()
            usock.close()
            return data
        except:
            return None

    def LoadCookies(self):
        for c in CookieStore.objects.all():
            self.cj.set_cookie(pickle.loads(c.cookie.encode('utf8')))

    def SaveCookies(self):
        all_cookies = CookieStore.objects.all()
        all_cookies.delete()

        for cookie in self.cj:
            new_cookie = CookieStore(cookie=pickle.dumps(cookie))
            new_cookie.save()

    def ReplyToThread(self, thread, message):
        getUrl = "https://forums.somethingawful.com/newreply.php?action=newreply&threadid=%s" % thread
        postUrl = "https://forums.somethingawful.com/newreply.php?action=newreply"

        data = self.download(getUrl)
        if data is None:
            return

        soup = BeautifulSoup(data)

        inputs = {'message': message}
        for i in soup.findAll('input', {'value': True}):
            inputs[i['name']] = i['value']

        del inputs['disablesmilies']
        del inputs['preview']

        r = requests.post(postUrl, data = inputs)

        request = Request(postUrl, datagen, headers)
        result = request.content


if __name__ == "__main__":
    dl = ForumPageDownloader()
    result = dl.download("https://forums.somethingawful.com/showthread.php?threadid=3552086")
