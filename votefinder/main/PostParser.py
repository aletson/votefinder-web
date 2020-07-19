import re
from datetime import timedelta

from votefinder.main.models import (Alias, Game, GameDay, Player, PlayerState,
                                    Vote)


class PostParser:
    def __init__(self):
        self.players = []
        self.gamePlayers = []

    def search_line_for_actions(self, post, line):
        # Votes
        pattern = re.compile(r'##\s*unvote|##\s*null|##\s*vote[:\s+]([^<\r\n]+)', re.I)
        pos = 0
        match = pattern.search(line, pos)

        while match:
            vote = Vote(post=post, game=post.game, author=post.author, unvote=True)
            (target_string,) = match.groups()
            if target_string:
                vote.target_string = target_string.strip()
                vote.target = self.autoresolve_vote(vote.target_string, post.game)
                vote.unvote = False

                if vote.target is None and vote.target_string.lower() in {'nolynch', 'no lynch', 'no execute', 'no hang', 'no cuddle', 'no lunch'}:
                    vote.no_execute = True
            try:
                game = Game.objects.get(id=post.game.id)  # Is this line necessary? Can't we just use post.game?
                player_last_vote = Vote.objects.filter(game=post.game, author=post.author).last()
                current_gameday = GameDay.objects.filter(game=post.game).last()
                if game.ecco_mode is False or player_last_vote is None or player_last_vote.post_id < current_gameday.start_post.id or player_last_vote.unvote or vote.unvote or PlayerState.get(game=game, player_id=player_last_vote.target).alive is False:
                    vote.save()
            except Game.DoesNotExist:
                vote.save()
            match = pattern.search(line, match.end())

        if post.game.is_player_mod(post.author):
            # pattern search for ##move and 3 wildcards pattern = re.compile("##\\s*move[:\\s+]([^<\\r\\n]+)", re.I
            # pattern search for ##deadline and # of hours
            pattern = re.compile(r'##\s*deadline[:\s+](\d+)', re.I)
            pos = 0
            match = pattern.search(line, pos)
            while match:
                (num_hrs,) = match.groups()
                if num_hrs and num_hrs > 0:  # Check if int - or modify regex
                    num_hrs = int(num_hrs)
                    new_deadline = post.timestamp + timedelta(hours=num_hrs)
                    post.game.deadline = new_deadline
                    post.game.save()

    def read_votes(self, post, game_players, players):
        self.gamePlayers = game_players
        self.players = players
        for quote in post.bodySoup.findAll('div', 'quote well'):
            quote.extract()
        for bold in post.bodySoup.findAll(['b', 'strong']):
            post_content = ''.join([str(bold_string) for bold_string in bold.contents])
            for line in post_content.splitlines():
                self.search_line_for_actions(post, line)

    def autoresolve_vote(self, text, game):
        try:
            if game.home_forum == 'bnr':
                player = Player.objects.get(bnr_uid__isnull=False, name__iexact=text)
            elif game.home_forum == 'sa':
                player = Player.objects.get(sa_uid__isnull=False, name__iexact=text)
            if player in self.players or player in self.gamePlayers:
                return player
        except Player.DoesNotExist:
            pass  # noqa: WPS420

        try:
            aliases = Alias.objects.filter(alias__iexact=text, player__in=self.players)
            if aliases:
                return aliases[0].player
        except Alias.DoesNotExist:
            pass  # noqa: WPS420

        try:
            aliases = Alias.objects.filter(alias__iexact=text, player__in=self.gamePlayers)
            if aliases:
                return aliases[0].player
        except Alias.DoesNotExist:
            pass  # noqa: WPS420

        try:
            if len(text) > 4:
                players = Player.objects.filter(name__icontains=text, name__in=[player.name for player in self.gamePlayers])
                if len(players) == 1:
                    return players[0]
        except Player.DoesNotExist:
            pass  # noqa: WPS420

        return None
