import re
import urllib

from django import forms
from django.contrib.auth.models import User
from votefinder.main.BNRApi import BNRApi
from votefinder.main.SAForumPageDownloader import SAForumPageDownloader
from votefinder.main.models import Player, UserProfile


class CreateUserForm(forms.Form):
    login = forms.CharField(label='Username', min_length=3)
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, min_length=5,
                               label='New Password')
    confirm = forms.CharField(widget=forms.PasswordInput, min_length=5,
                              label='Confirm Password')

    def clean_login(self):
        login = self.cleaned_data['login']
        try:
            existing_user = User.objects.all().get(username=login)
            raise forms.ValidationError('A user by the name {} already exists.'.format(existing_user.username))
        except User.DoesNotExist:
            pass  # noqa: WPS420
        return login

    def clean_confirm(self):
        password1 = self.cleaned_data['password']
        password2 = self.cleaned_data['confirm']
        if password1 != password2:
            raise forms.ValidationError("The two password fields don't match.")
        return password2


class LinkProfileForm(forms.Form):
    login = forms.CharField(label='Username', min_length=3)
    home_forum = forms.ChoiceField(choices=[('sa', 'Something Awful'), ('bnr', 'Bread & Roses')])

    def clean_login(self):
        login = self.cleaned_data['login']
        home_forum = self.data['home_forum']

        if self.required_key:
            if home_forum == 'sa':
                downloader = SAForumPageDownloader()
                page_data = downloader.download(
                    'https://forums.somethingawful.com/member.php?action=getinfo&username={}'.format(urllib.parse.quote_plus(login)))

                if page_data is None:
                    raise forms.ValidationError('There was a problem downloading the profile for the SA user {}.'.format(login))

                if page_data.find(str(self.required_key)) == -1:
                    raise forms.ValidationError("Unable to find the correct key ({}) in {}'s SA profile".format(self.required_key, login))
                else:
                    matcher = re.compile(r'userid=(?P<userid>\d+)').search(page_data)
                    if matcher:
                        self.userid = matcher.group('userid')
                        try:
                            existing_player = Player.objects.all().get(sa_uid=self.userid)
                            existing_userprofile = UserProfile.objects.all().get(player=existing_player)  # noqa: F841
                            raise forms.ValidationError('{} is already registered to a user profile. Do you have another Votefinder account?'.format(existing_player.name))
                        except Player.DoesNotExist:
                            pass  # noqa: WPS420
                        except UserProfile.DoesNotExist:
                            raise forms.ValidationError('Votefinder is already aware of {} as an unclaimed player profile. Claim it from their <a href="/player/{}">profile page</a>.'.format(existing_player.name, existing_player.slug))
                        matcher = re.compile(r'\<dt class="author"\>(?P<login>.+?)\</dt\>').search(page_data)
                        if matcher:
                            login = matcher.group('login')
                    else:
                        raise forms.ValidationError(
                            'Unable to find the userID of {}.  Please talk to the site admin.'.format(login))
            elif home_forum == 'bnr':
                api = BNRApi()
                user_profile = api.get_user_by_name(urllib.parse.quote_plus(login))
                if user_profile is None:
                    raise forms.ValidationError('There was a problem downloading the profile for the BNR user {}.'.format(login))
                if user_profile['location'] == str(self.required_key):
                    if user_profile['user_id']:
                        self.userid = user_profile['user_id']
                        try:
                            existing_player = Player.objects.all().get(bnr_uid=self.userid)
                            raise forms.ValidationError('{} is already registered with that user ID. Has your forum name changed?'.format(existing_player.name))
                        except Player.DoesNotExist:
                            pass  # noqa: WPS420
                        login = user_profile['username']
                    else:
                        raise forms.ValidationError(
                            'Unable to find the userID of {}.  Please talk to the site admin.'.format(login))
                else:
                    raise forms.ValidationError("Unable to find the correct key ({}) in {}'s BNR profile".format(self.required_key, login))

        return login
