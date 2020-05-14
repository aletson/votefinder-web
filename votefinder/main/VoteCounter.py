import math
import random

from votefinder.main.models import GameDay, LynchMessage, Player, Vote

from . import ForumPageDownloader, VotecountFormatter


class VoteCounter:
    def __init__(self):
        self.results = {}
        self.currentVote = {}
        self.votesFound = False
        self.nolynch_player = None
        self.voteLog = []
        self.show_only_active_votes = False

    def run(self, game):
        gameday = game.days.select_related().last()

        try:
            votes = Vote.objects.select_related().filter(game=game, ignored=False, manual=False,
                                                         post__id__gte=gameday.startPost.id).order_by('id')
            manual_votes = Vote.objects.select_related().filter(game=game, ignored=False, manual=True,
                                                                post__id__gte=gameday.startPost.id).order_by('id')
            self.votesFound = True
        except Vote.DoesNotExist:
            return

        self.livingPlayers = Player.objects.select_related().filter(games__in=game.living_players())
        self.game = game
        self.voteLog = []

        for single_player in self.livingPlayers:
            self.results[single_player] = {'count': 0, 'votes': []}
            self.currentVote[single_player] = None

        for single_vote in votes:
            if single_vote.author in self.livingPlayers and self.TargetIsValid(single_vote):
                if single_vote.unvote:
                    self.HandleUnvote(single_vote)
                else:
                    self.HandleVote(single_vote)

        # ensure manual votes are applied after all real votes
        for single_manual_vote in manual_votes:
            if self.TargetIsValid(single_manual_vote):
                if single_manual_vote.unvote:
                    self.HandleUnvote(single_manual_vote)
                else:
                    self.HandleVote(single_manual_vote)

        self.RunNotify(game, gameday)

        return self.BuildResultList()

    def GetVoteLog(self):
        return self.voteLog

    def RunNotify(self, game, gameday):
        gameday = GameDay.objects.get(id=gameday.id)  # reload to prevent double posts from 2 threads updating at once
        if gameday.notified:
            return

        tolynch = int(math.floor(len(game.living_players()) / 2.0) + 1)
        lynched = filter(lambda key: self.results[key]['count'] >= tolynch, self.results)

        if list(lynched):
            gameday.notified = True
            gameday.save()

            if len(list(lynched)) == 1:
                game.status_update('{} was executed on day {}!'.format(lynched[0].name, gameday.dayNumber))
                self.PostLynchedMessage(game, lynched[0].name)

    def PostLynchedMessage(self, game, name):
        if not game.post_lynches:
            return

        message = random.choice(LynchMessage.objects.all()).text  # noqa: S311
        v = VotecountFormatter.VotecountFormatter(game)
        v.go()
        message = '{}\n\n'.format(message)
        message += v.bbcode_votecount
        dl = ForumPageDownloader()
        dl.ReplyToThread(game.threadId, ':redhammer: ' + (message % name))

    def BuildResultList(self):
        resultlist = []
        for key, val in self.results.items():
            resultlist.append({'target': key, 'count': val['count'], 'votes': val['votes']})

        resultlist.sort(key=lambda i: i['count'], reverse=True)

        return resultlist

    def TargetIsValid(self, vote):
        if vote.nolynch and self.nolynch_player is None:
            self.nolynch_player = Player.objects.get(uid=-1)
            self.results[self.nolynch_player] = {'count': 0, 'votes': []}

        return vote.unvote or vote.nolynch or (vote.target in self.livingPlayers)

    def HandleVote(self, vote):
        if not vote.manual and self.PlayerIsVoting(vote.author):
            self.HandleUnvote(vote)

        if vote.nolynch:
            vote.target = self.nolynch_player

        self.AddVoteToPlayer(vote.target, vote.author, False, vote.post.pageNumber, vote.post.postId,
                             vote.post.timestamp)
        self.currentVote[vote.author] = vote.target

    def AddVoteToPlayer(self, target, author, unvote, page, postid, timestamp):
        resultItem = self.results[target]
        if unvote:
            resultItem['count'] -= 1
            text = '{} unvotes'.format(author)
        else:
            resultItem['count'] += 1
            text = '{} votes {}'.format(author, target)

        self.voteLog.append({'timestamp': timestamp, 'player': target.name, 'count': resultItem['count'], 'text': text})

        resultItem['votes'].append({'unvote': unvote, 'enabled': True, 'author': author,
                                    'url': 'http://forums.somethingawful.com/showthread.php?threadid={}&pagenumber={}#post{}'.format(
                                        self.game.threadId, page, postid)})

    def HandleUnvote(self, vote):
        currentVote = self.PlayerIsVoting(vote.author)
        if currentVote:
            self.DisableCurrentVote(vote.author, currentVote)
            self.AddVoteToPlayer(currentVote, vote.author, True, vote.post.pageNumber, vote.post.postId,
                                 vote.post.timestamp)
        self.currentVote[vote.author] = None

    def DisableCurrentVote(self, player, target):
        for item in self.results[target]['votes']:
            if item['author'] == player and item['unvote'] is False and item['enabled']:
                item['enabled'] = False
                return

    def PlayerIsVoting(self, player):
        if player in self.currentVote.keys():
            return self.currentVote[player]
        return None
