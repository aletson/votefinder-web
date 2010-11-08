import urllib, urllib2, cookielib, re
import cPickle as pickle
from votefinder.main.models import CookieStore
from django.conf import settings

class ForumPageDownloader():
    def __init__(self):
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
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
            
    def LoginToForum(self):
        data = ""
        
        try:
            usock = self.opener.open("http://forums.somethingawful.com/account.php", 
                                     urllib.urlencode(dict(action='login', username=settings.SA_LOGIN, password=settings.SA_PASSWORD)))
            data = usock.read()
            usock.close()
        except URLError, e:
            return False
        
        if self.IsLoggedInCorrectlyPage(data):
            self.SaveCookies()
            return True
        else:
            return False
        
    def IsNeedToLogInPage(self, data):
        if re.search(re.compile(r"A BRIEF OVERVIEW \(WHY DO WE CHARGE TO REGISTER\?\)"), data) == None:
            return False
        else:
            return True
    
    def IsLoggedInCorrectlyPage(self, data):
        if re.search(re.compile(r"GLUE GLUEEEEE GLUUUUUUEEE,.*?GLUUUEEE GLUE GLLLUUUUUEEEEEE"), data) == None:
            return False
        else:
            return True
        
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
            
