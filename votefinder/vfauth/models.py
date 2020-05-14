import re
import urllib

from django import forms
from django.contrib.auth.models import User
from votefinder.main.ForumPageDownloader import ForumPageDownloader
from votefinder.main.models import Player, UserProfile


class CreateUserForm(forms.Form):
    login = forms.CharField(label='SA Username', min_length=3)
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, min_length=5,
                               label='New Password')
    confirm = forms.CharField(widget=forms.PasswordInput, min_length=5,
                              label='Confirm Password')

    def clean_confirm(self):
        password1 = self.cleaned_data['password']
        password2 = self.cleaned_data['confirm']
        if password1 != password2:
            raise forms.ValidationError("The two password fields don't match.")
        return password2

    def clean_login(self):
        login = self.cleaned_data['login']

        try:
            existingUser = User.objects.all().get(username=login)
            raise forms.ValidationError('A user by that name already exists.')
        except User.DoesNotExist:
            pass

        if self.required_key:
            downloader = ForumPageDownloader()
            data = downloader.download(
                'https://forums.somethingawful.com/member.php?action=getinfo&username={}'.format(urllib.parse.quote_plus(login)))

            if data is None:
                raise forms.ValidationError('There was a problem downloading the profile for the SA user {}.'.format(login))

            if data.find(str(self.required_key)) == -1:
                raise forms.ValidationError("Unable to find the correct key ({}) in {}'s SA profile".format(self.required_key, login))
            else:
                matcher = re.compile(r'userid=(?P<userid>\d+)').search(data)
                if matcher:
                    self.userid = matcher.group('userid')
                    try:
                        existingPlayer = Player.objects.all().get(uid=self.userid)
                        existingUserProfile = UserProfile.objects.all().get(player_id=existingPlayer.id)
                        existingUser = UserProfile.objects.all().get(id=existingUserProfile.user_id)
                        raise forms.ValidationError('{} is already registered with that user ID. Has your forum name changed?'.format(existingUser.username))
                    except UserProfile.DoesNotExist:
                        pass
                    except Player.DoesNotExist:
                        pass
                    except User.DoesNotExist:
                        pass
                    matcher = re.compile(r'\<dt class="author"\>(?P<login>.+?)\</dt\>').search(data)
                    if matcher:
                        login = matcher.group('login')
                else:
                    raise forms.ValidationError(
                        'Unable to find the userID of {}.  Please talk to the site admin.'.format(login))

        return login
