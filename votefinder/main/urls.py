from django.conf.urls import *
from votefinder.main.feeds import *
from django.views.generic.base import TemplateView
import votefinder.main.views

urlpatterns = [
    url(r'^$',                                     votefinder.main.views.index),
    url(r'^add$',                                  votefinder.main.views.add),
    url(r'^add_game/(?P<threadid>\d+)/*$',      	votefinder.main.views.add_game),
    url(r'^game_list/(?P<page>\d+)/*$',            votefinder.main.views.game_list),
    url(r'^game/(?P<slug>[\w-]+)$',               	votefinder.main.views.game),
    url(r'^player/(?P<slug>[\w-]+)/*$',            votefinder.main.views.player),
    url(r'^p:(?P<playerid>\d+)/*$',                votefinder.main.views.player_id),
    url(r'^profile/*$',                            votefinder.main.views.profile),
    url(r'^update/(?P<gameid>\d+)/*$',             votefinder.main.views.update),
    url(r'^player_state/(?P<gameid>\d+)/(?P<playerid>\d+)/(?P<state>\w+)/$', votefinder.main.views.player_state),
    url(r'^player_list/',                          votefinder.main.views.player_list),
    url(r'^add_player/(?P<gameid>\d+)/*$',         votefinder.main.views.add_player),
    url(r'^delete_spectators/(?P<gameid>\d+)/*$',  votefinder.main.views.delete_spectators),
    url(r'^votecount/(?P<gameid>\d+)/*$',          votefinder.main.views.votecount),
    url(r'^resolve/(?P<voteid>\d+)/(?P<resolution>-{0,1}\d+)/*$', votefinder.main.views.resolve),
    url(r'^posts/(?P<gameid>\d+)/(?P<page>\d+)/*$', votefinder.main.views.posts),
    url(r'^add_comment/(?P<gameid>\d+)/*$',        votefinder.main.views.add_comment),
    url(r'^delete_comment/(?P<commentid>\d+)/*$', 	votefinder.main.views.delete_comment),
    url(r'^rss/*$',                                LatestRss()),
    url(r'^atom/*$',                               LatestAtom()),
    url(r'^game_status/(?P<slug>[\w-]+)/*',        SpecificGameStatusAtom()),
    url(r'^game_status/*$',                        GameStatusAtom()),
    url(r'^faq/*$',                                TemplateView.as_view(template_name='faq.html')),
    url(r'^deadline/(?P<gameid>[\d]+)/(?P<month>[\d]+)/(?P<day>[\d]+)/(?P<year>[\d]+)/(?P<hour>[\d]+)/(?P<min>[\d]+)/(?P<ampm>[\w]+)/(?P<tzname>.+)$', votefinder.main.views.deadline),
    url(r'^close_game/(?P<gameid>\d+)/*$',         votefinder.main.views.close_game),
    url(r'^reopen_game/(?P<gameid>\d+)/*$',        votefinder.main.views.reopen_game),
    url(r'^new_day/(?P<gameid>\d+)/(?P<day>\d+)/*$', votefinder.main.views.new_day),
    url(r'^replace/(?P<gameid>\d+)/(?P<clear>\w+)/(?P<outgoing>\d+)/(?P<incoming>.+)*$', votefinder.main.views.replace),
    url(r'^startday:(?P<day>\d+)/(?P<postid>\d+)*$',votefinder.main.views.start_day),   
    url(r'^templates$',                            votefinder.main.views.templates),
    url(r'^create_template$',                      votefinder.main.views.create_template),
    url(r'^template/(?P<templateid>\d+)$',         votefinder.main.views.edit_template),
    url(r'^delete_template/(?P<templateid>\d+)$',  votefinder.main.views.delete_template),
    url(r'^game_template/(?P<gameid>\d+)/(?P<templateid>\d+)', votefinder.main.views.game_template),
    url(r'^active_games$',                         votefinder.main.views.active_games),
    url(r'^active_games/json$',                    votefinder.main.views.active_games_json),
    url(r'^active_games/(?P<style>.+)',            votefinder.main.views.active_games_style),
    url(r'^closed/*$',                             votefinder.main.views.closed_games),
    url(r'^add_vote/(?P<gameid>\d+)/(?P<player>[\d-]+)/(?P<votes>\w+)/(?P<target>\d+)$', votefinder.main.views.add_vote),
    url(r'^delete_vote/(?P<voteid>\d+)$',          votefinder.main.views.delete_vote),
    url(r'^img/(?P<slug>[\w-]+)/*$',               votefinder.main.views.votecount_image),
    url(r'^autoupdate$',                           votefinder.main.views.autoupdate),
    url(r'^players$',                              votefinder.main.views.players),
    url(r'^players/(?P<page>\d+)$',                votefinder.main.views.players_page),
    url(r'^delete_alias/(?P<id>\d+)$',             votefinder.main.views.delete_alias),
    url(r'^sendpms/(?P<slug>[\w-]+)$',             votefinder.main.views.sendpms),
    url(r'^post_histories/(?P<gameid>\d+)$',       votefinder.main.views.post_histories),
    url(r'^post_lynches/(?P<gameid>\d+)/(?P<enabled>\w+)$', votefinder.main.views.post_lynches),
    url(r'^ecco_mode/(?P<gameid>\d+)/(?P<enabled>\w+)$', votefinder.main.views.ecco_mode),
    url(r'^post_vc/(?P<gameid>\d+)$',              votefinder.main.views.post_vc),
    url(r'^votechart/(?P<gameslug>[\w-]+)$',       votefinder.main.views.votechart_all),
    url(r'^votechart/(?P<gameslug>[\w-]+)/(?P<playerslug>[\w-]+)$', votefinder.main.views.votechart_player),
    url(r'^gamechart$',                            votefinder.main.views.gamechart)
]