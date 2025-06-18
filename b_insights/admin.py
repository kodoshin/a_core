from django.contrib import admin
from .models import *


#admin.site.register(CodingChat)
admin.site.register(InsightTokenUsage)
admin.site.register(InsightProcessingStep)
#admin.site.register(CodingChatMessage)
admin.site.register(InsightChatCategory)
admin.site.register(InsightProcessingError)

@admin.register(InsightChat)
class CodingChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project')
@admin.register(InsightChatMessage)
class CodingChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'order', 'type')
