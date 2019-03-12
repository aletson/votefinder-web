from django.conf.urls import *
from django.views.generic.base import TemplateView




from . import views
from . import feeds

urlpatterns = [
    url(r'^$', views.index),
    url(r'^add$', views.add),
    url(r'^add_game/(?P<threadid>\d+)/*$', views.add_game),
    url(r'^game_list/(?P<page>\d+)/*$', views.game_list),
    url(r'^game/(?P<slug>[\w-]+)$', views.game),
    url(r'^player/(?P<slug>[\w-]+)/*$', views.player),
    url(r'^p:(?P<playerid>\d+)/*$', views.player_id),
    url(r'^profile/*$', views.profile),
    url(r'^update/(?P<gameid>\d+)/*$', views.update),
    url(r'^player_state/(?P<gameid>\d+)/(?P<playerid>\d+)/(?P<state>\w+)/$', views.player_state),
    url(r'^player_list/', views.player_list),
    url(r'^add_player/(?P<gameid>\d+)/*$', views.add_player),
    url(r'^delete_spectators/(?P<gameid>\d+)/*$', views.delete_spectators),
    url(r'^votecount/(?P<gameid>\d+)/*$', views.votecount),
    url(r'^resolve/(?P<voteid>\d+)/(?P<resolution>-{0,1}\d+)/*$', views.resolve),
    url(r'^posts/(?P<gameid>\d+)/(?P<page>\d+)/*$', views.posts),
    url(r'^add_comment/(?P<gameid>\d+)/*$', views.add_comment),
    url(r'^delete_comment/(?P<commentid>\d+)/*$', views.delete_comment),
    url(r'^rss/*$', feeds.LatestRss()),
    url(r'^atom/*$', feeds.LatestAtom()),
    url(r'^game_status/(?P<slug>[\w-]+)/*', feeds.SpecificGameStatusAtom()),
    url(r'^game_status/*$', feeds.GameStatusAtom()),
    url(r'^faq/*$', TemplateView.as_view(template_name='faq.html')),
    url(
        r'^deadline/(?P<gameid>[\d]+)/(?P<month>[\d]+)/(?P<day>[\d]+)/(?P<year>[\d]+)/(?P<hour>[\d]+)/(?P<min>[\d]+)/(?P<ampm>[\w]+)/(?P<tzname>.+)$',
        views.deadline),
    url(r'^close_game/(?P<gameid>\d+)/*$', views.close_game),
    url(r'^reopen_game/(?P<gameid>\d+)/*$', views.reopen_game),
    url(r'^new_day/(?P<gameid>\d+)/(?P<day>\d+)/*$', views.new_day),
    url(r'^replace/(?P<gameid>\d+)/(?P<clear>\w+)/(?P<outgoing>\d+)/(?P<incoming>.+)*$', views.replace),
    url(r'^startday:(?P<day>\d+)/(?P<postid>\d+)*$', views.start_day),
    url(r'^templates$', views.templates),
    url(r'^create_template$', views.create_template),
    url(r'^template/(?P<templateid>\d+)$', views.edit_template),
    url(r'^delete_template/(?P<templateid>\d+)$', views.delete_template),
    url(r'^game_template/(?P<gameid>\d+)/(?P<templateid>\d+)', views.game_template),
    url(r'^active_games$', views.active_games),
    url(r'^active_games/json$', views.active_games_json),
    url(r'^active_games/(?P<style>.+)', views.active_games_style),
    url(r'^closed/*$', views.closed_games),
    url(r'^add_vote/(?P<gameid>\d+)/(?P<player>[\d-]+)/(?P<votes>\w+)/(?P<target>\d+)$',
        views.add_vote),
    url(r'^add_vote_global/(?P<gameid>\d+)$',views.add_vote_global),
    url(r'^delete_vote/(?P<voteid>\d+)$', views.delete_vote),
    url(r'^img/(?P<slug>[\w-]+)/*$', views.votecount_image),
    url(r'^autoupdate$', views.autoupdate),
    url(r'^players$', views.players),
    url(r'^players/(?P<page>\d+)$', views.players_page),
    url(r'^delete_alias/(?P<id>\d+)$', views.delete_alias),
    url(r'^sendpms/(?P<slug>[\w-]+)$', views.sendpms),
    url(r'^post_histories/(?P<gameid>\d+)$', views.post_histories),
    url(r'^post_lynches/(?P<gameid>\d+)/(?P<enabled>\w+)$', views.post_lynches),
    url(r'^ecco_mode/(?P<gameid>\d+)/(?P<enabled>\w+)$', views.ecco_mode),
    url(r'^post_vc/(?P<gameid>\d+)$', views.post_vc),
    url(r'^votechart/(?P<gameslug>[\w-]+)$', views.votechart_all),
    url(r'^votechart/(?P<gameslug>[\w-]+)/(?P<playerslug>[\w-]+)$', views.votechart_player),
    url(r'^gamechart$', views.gamechart),
    url(r'^update_user_theme$', views.update_user_theme)
]
