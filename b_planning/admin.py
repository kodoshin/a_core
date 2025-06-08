from django.contrib import admin
from .models import *


admin.site.register(PlanningTokenUsage)
admin.site.register(PlanningProcessingStep)
admin.site.register(PlanningChatCategory)
admin.site.register(PlanningProcessingError)

@admin.register(PlanningChat)
class PlanningChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project')
@admin.register(PlanningChatMessage)
class PlanningChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'order', 'type')
