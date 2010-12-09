from votefinder.main.models import *
import math
from ForumPageDownloader import ForumPageDownloader
import thread
import random

class VoteCounter:
    def __init__(self):
        self.results = {}
        self.currentVote = {}
        self.votesFound = False
        self.nolynch_player = None
        
    def run(self, game):
        gameday = game.days.select_related(depth=1).all().order_by('-dayNumber')[:1][0]

        try:
            votes = Vote.objects.select_related(depth=2).filter(game=game, ignored=False, manual=False, post__id__gte=gameday.startPost.id).order_by('id')
            manual_votes = Vote.objects.select_related(depth=2).filter(game=game, ignored=False, manual=True, post__id__gte=gameday.startPost.id).order_by('id')
            self.votesFound = True
        except Vote.DoesNotExist:
            return
        
        self.livingPlayers = Player.objects.select_related(depth=2).filter(games__in=game.living_players())
        self.game = game

        for p in self.livingPlayers:
            self.results[p] = { 'count': 0, 'votes': [] }
            self.currentVote[p] = None

        for v in votes:
            if v.author in self.livingPlayers and self.TargetIsValid(v):
                if v.unvote:
                    self.HandleUnvote(v)
                else:
                    self.HandleVote(v)

        # ensure manual votes are applied after all real votes
        for v in manual_votes:
            if self.TargetIsValid(v):
                if v.unvote:
                    self.HandleUnvote(v)
                else:
                    self.HandleVote(v)
        
        self.RunNotify(game, gameday)

        return self.BuildResultList()
    
    def RunNotify(self, game, gameday):
        gameday = GameDay.objects.get(id=gameday.id) #reload to prevent double posts from 2 threads updating at once
        if gameday.notified:
            return

        tolynch =  int(math.floor(len(game.living_players()) / 2.0) + 1)
        lynched = filter(lambda key: self.results[key]['count'] >= tolynch, self.results)

        if len(lynched) > 0:
            gameday.notified = True
            gameday.save()

            if len(lynched) == 1:
                game.status_update("%s was lynched on day %s!" % (lynched[0].name, gameday.dayNumber))
                self.PostLynchedMessage(game, lynched[0].name)

    def PostLynchedMessage(self, game, name):
        if not game.post_lynches:
            return

        message = random.choice(LynchMessage.objects.all()).text
        dl = ForumPageDownloader()
        dl.ReplyToThread(game.threadId, ":redhammer: " + (msg % name))

    def BuildResultList(self):
        list = []
        for key, val in self.results.items():
            list.append({'target': key, 'count': val['count'], 'votes': val['votes']})
    
        list.sort(key=lambda i: i['count'], reverse=True)

        return list
        
    def TargetIsValid(self, vote):
        if vote.nolynch and self.nolynch_player == None:
            self.nolynch_player = Player.objects.get(uid=-1)
            self.results[self.nolynch_player] = { 'count': 0, 'votes': [] }

        return vote.unvote or vote.nolynch or (vote.target in self.livingPlayers)
        
    def HandleVote(self, vote):
        if not vote.manual and self.PlayerIsVoting(vote.author):
            self.HandleUnvote(vote)

        if vote.nolynch:
            vote.target = self.nolynch_player

        self.AddVoteToPlayer(vote.target, vote.author, False, vote.post.pageNumber, vote.post.postId)    
        self.currentVote[vote.author] = vote.target

    def AddVoteToPlayer(self, target, author, unvote, page, postid):
        resultItem = self.results[target]
        if unvote:
            resultItem['count'] -= 1
        else:
            resultItem['count'] += 1
            
        resultItem['votes'].append({'unvote': unvote, 'enabled': True, 'author': author, 
                                    'url': 'http://forums.somethingawful.com/showthread.php?threadid=%s&pagenumber=%s#post%s' % (self.game.threadId, page, postid)})
    
    def HandleUnvote(self, vote):
        currentVote = self.PlayerIsVoting(vote.author)
        if currentVote:
            self.DisableCurrentVote(vote.author, currentVote)
            self.AddVoteToPlayer(currentVote, vote.author, True, vote.post.pageNumber, vote.post.postId)
        self.currentVote[vote.author] = None
        
    def DisableCurrentVote(self, player, target):
        for item in self.results[target]['votes']:
            if item['author'] == player and item['unvote'] == False and item['enabled'] == True:
                item['enabled'] = False
                return
        
    def PlayerIsVoting(self, player):
        if player in self.currentVote.keys():
            return self.currentVote[player]
        else:
            return None
