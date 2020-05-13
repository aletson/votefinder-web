import math
import re
from datetime import datetime

from django.conf import settings
from django.utils.dateformat import format
from django.utils.timesince import timeuntil
from pytz import timezone

from . import VoteCounter
from votefinder.main.models import *


class VotecountFormatter:
    def __init__(self, game):
        self.empty_tick = ''
        self.tick = ''

        self.vc = VoteCounter.VoteCounter()
        self.game = game

    def go(self, show_comment=True):
        self.results = self.vc.run(self.game)

        game_template = self.game.template
        if game_template is None:
            game_template = VotecountTemplate.objects.get(system_default=True)

        gameday = self.game.days.select_related().last()
        living_players = [ps.player for ps in self.game.living_players()]
        alive = len(living_players)
        if self.game.deadline:
            tz = timezone(self.game.timezone)
            dl = timezone(settings.TIME_ZONE).localize(self.game.deadline).astimezone(tz)
            deadline = format(dl, r'F d[\s\u\p\e\r]S[/\s\u\p\e\r], Y \a\t P ') + dl.tzname()
            until_deadline = timeuntil(self.game.deadline, datetime.now())
            until_deadline = until_deadline.replace(u'\u00A0', ' ')
        else:
            deadline = ''
            until_deadline = ''

        self.tolynch = self.to_lynch(alive)
        detail_level = game_template.detail_level
        self.tick = game_template.full_tick
        self.empty_tick = game_template.empty_tick
        comments = Comment.objects.filter(game=self.game).order_by('-timestamp') if show_comment else ''

        votecount_lines = []
        for item in self.results:
            if item['count'] == 0 and game_template.hide_zero_votes:
                continue

            if item['votes']:
                votelist = []
                for v in item['votes']:
                    thisvote = None
                    if v['unvote']:
                        if detail_level == 3:
                            thisvote = ''.join(
                                [game_template.before_unvote, str(v['author'].name), game_template.after_unvote])
                    elif v['enabled']:
                        thisvote = ''.join([game_template.before_vote, str(v['author'].name), game_template.after_vote])
                    else:
                        if detail_level >= 2:
                            thisvote = ''.join(
                                [game_template.before_unvoted_vote, str(v['author'].name), game_template.after_unvoted_vote])

                    if thisvote:
                        votelist.append(thisvote.replace('{{url}}', v['url']))

                if votelist:
                    this_line = game_template.single_line.replace('{{target}}', str(item['target'].name)).replace(
                        '{{count}}', str(item['count'])).replace('{{votelist}}', ', '.join(votelist))
                    votecount_lines.append(
                        this_line.replace('{{ticks}}', self.build_ticks(item['count'], self.tolynch)))

        self.not_voting_list = sorted(
            filter(lambda x: self.vc.currentVote[x] is None and x in living_players, self.vc.currentVote),
            key=lambda x: x.name.lower())
        temp_not_voting = game_template.single_line.replace('{{target}}', 'Not Voting').replace('{{count}}', str(
            len(self.not_voting_list))).replace('{{ticks}}', self.build_ticks(0, self.tolynch))

        temp_overall = game_template.overall.replace('{{votecount}}', '\n'.join(votecount_lines))
        temp_overall = temp_overall.replace('{{deadline}}',
            game_template.deadline_exists if self.game.deadline else game_template.deadline_not_set)
        temp_overall = temp_overall.replace('{{notvoting}}', temp_not_voting.replace('{{votelist}}', ', '.join(
            map(lambda x: x.name, self.not_voting_list))))

        if comments:
            temp_overall += '\n \n' + '\n \n'.join([c.comment for c in comments])

        self.bbcode_votecount = temp_overall.replace('{{deadline}}', str(deadline)).replace('{{timeuntildeadline}}',
            until_deadline).replace('{{day}}', str(gameday.dayNumber)).replace('{{tolynch}}', str(self.tolynch)).replace('{{alive}}', str(alive))

        self.html_votecount = self.ConvertBBCodeToHTML(self.bbcode_votecount)

    def f(self, x):
        test = x

    def to_lynch(self, count):
        return int(math.floor(count / 2.0) + 1)

    def build_ticks(self, ticked, total):
        return ''.join(
            ['[img]%s[/img]' % (self.empty_tick if i < (total - ticked) else self.tick) for i in range(0, total)])

    def ConvertBBCodeToHTML(self, bbcode):
        results = bbcode

        results = results.replace('\n', '<br />\n').replace('[b]', '<b>').replace('[/b]', '</b>').replace('[i]', '<i>')
        results = results.replace('[/i]', '</i>').replace('[u]', '<u>').replace('[/u]', '</u>').replace('[super]', '<sup>')
        results = results.replace('[/super]', '</sup>').replace('[sub]', '<sub>').replace('[/sub]', '</sub>').replace('[s]', '<del>')
        results = results.replace('[/s]', '</del>').replace('[list]', '<list>').replace('[/list]', '</list><br/>').replace('[*]', '<li>')

        results = re.compile(r'\[img\](.*?)\[/img\]', re.I | re.S).sub(r'<img src="\1">', results)
        results = re.compile(r'\[url=(.*?)\](.*?)\[/url\]', re.I | re.S).sub(r'<u><a href="\1">\2</a></u>', results)

        return results
