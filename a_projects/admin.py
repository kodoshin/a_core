from django.contrib import admin
from .models import *


#admin.site.register(Project)
admin.site.register(Technology)
admin.site.register(Status)
#admin.site.register(File)
admin.site.register(ComponentType)
#admin.site.register(Component)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'technology', 'user')
@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'project', 'type')

@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'file', 'component_type', 'get_project_name')

    def get_project_name(self, obj):
        return obj.file.project.name if obj.file and obj.file.project else None

    get_project_name.admin_order_field = 'file__project__name'  # permet le tri sur ce champ
    get_project_name.short_description = 'Project Name'