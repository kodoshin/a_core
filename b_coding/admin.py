from django.contrib import admin
from .models import *


#admin.site.register(CodingChat)
admin.site.register(TokenUsage)
admin.site.register(ProcessingStep)
#admin.site.register(CodingChatMessage)
admin.site.register(ChatCategory)
admin.site.register(ProcessingError)

@admin.register(CodingChat)
class CodingChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project')
@admin.register(CodingChatMessage)
class CodingChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'order', 'type')
