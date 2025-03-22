from django.contrib import admin
from .models import *


admin.site.register(Project)
admin.site.register(Technology)
admin.site.register(Status)
admin.site.register(File)
admin.site.register(ComponentType)
admin.site.register(Component)