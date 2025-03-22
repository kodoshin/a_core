from django.contrib import admin
from .models import AllowedFile
from import_export.admin import ImportExportModelAdmin
from import_export import resources



class AllowedFileResource(resources.ModelResource):
    class Meta:
        model = AllowedFile
        import_id_fields = ('extension',)  # Spécifier la clé unique

# Ajout de l'import/export dans l'admin
@admin.register(AllowedFile)
class CountryAdmin(ImportExportModelAdmin):
    resource_class = AllowedFileResource
    list_display = ('name', 'extension', 'description')  # Affichage des colonnes
    search_fields = ('name',)


