import urllib

from votefinder.main.ForumPageDownloader import ForumPageDownloader
from votefinder.main.models import *


class CreateUserForm(forms.Form):
    login = forms.CharField(label="SA Username", min_length=3)
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, min_length=5,
                               label="New Password")
    confirm = forms.CharField(widget=forms.PasswordInput, min_length=5,
                              label="Confirm Password")

    def clean_confirm(self):
        password1 = self.cleaned_data["password"]
        password2 = self.cleaned_data["confirm"]
        if password1 != password2:
            raise forms.ValidationError("The two password fields don't match.")
        return password2

    def clean_login(self):
        login = self.cleaned_data['login']

        try:
            existingUser = User.objects.all().get(username=login)
            raise forms.ValidationError("A user by that name already exists.")
        except User.DoesNotExist:
            pass
        
        try:

        if self.required_key:
            downloader = ForumPageDownloader()
            data = downloader.download(
                'https://forums.somethingawful.com/member.php?action=getinfo&username=%s' % urllib.quote_plus(login))

            if data == None:
                raise forms.ValidationError("There was a problem downloading the profile for the SA user %s." % login)

            if data.find(str(self.required_key)) != -1:
                matcher = re.compile('userid=(?P<userid>\d+)').search(data)
                if matcher:
                    self.userid = matcher.group('userid')
                    try:
                        existingPlayer = Player.objects.all().get(uid=self.userid)
                        existingUserProfile = UserProfile.objects.all().get(player_id=existingPlayer.id)
                        existingUser = UserProfile.objects.all().get(id=existingUserProfile.user_id)
                        raise forms.ValidationError("%s is already registered with that user ID. Has your forum name changed?" % existingUser.username)
                    except UserProfile.DoesNotExist:
                        pass
                    except Player.DoesNotExist:
                        pass                        
                    matcher = re.compile(r'\<dt class="author"\>(?P<login>.+?)\</dt\>').search(data)
                    if matcher:
                        login = matcher.group('login')

                    return login
                else:
                    raise forms.ValidationError(
                        "Unable to find the userID of %s.  Please talk to the site admin." % login)
            else:
                raise forms.ValidationError(
                    "Unable to find the correct key (%s) in %s's SA profile" % (self.required_key, login))
        else:
            return login
