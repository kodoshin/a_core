from django.contrib import admin
from .models import *


admin.site.register(CodingChat)
admin.site.register(TokenUsage)
admin.site.register(ProcessingStep)
admin.site.register(CodingChatMessage)
admin.site.register(ChatCategory)

