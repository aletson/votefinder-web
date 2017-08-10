from django.contrib import admin

from votefinder.main.models import *

admin.site.register(Game)
admin.site.register(Player)
admin.site.register(Post)
admin.site.register(Alias)
admin.site.register(Vote)
admin.site.register(BlogPost)
admin.site.register(UserProfile)
admin.site.register(PlayerState)
admin.site.register(Comment)
admin.site.register(GameDay)
admin.site.register(CookieStore)
admin.site.register(VotecountTemplate)
admin.site.register(LynchMessage)


class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'timestamp', 'game', 'pagenumber')
    list_filter = ('game', 'pagenumber')
    list_select_related = True
