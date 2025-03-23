from django.contrib import admin
from .models import Profile, Country, CreditClaim
from import_export.admin import ImportExportModelAdmin
from import_export import resources



class CountryResource(resources.ModelResource):
    class Meta:
        model = Country
        import_id_fields = ('name',)  # Spécifier la clé unique

# Ajout de l'import/export dans l'admin
@admin.register(Country)
class CountryAdmin(ImportExportModelAdmin):
    resource_class = CountryResource
    list_display = ('name', 'phone_code')  # Affichage des colonnes
    search_fields = ('name',)


admin.site.register(Profile)

admin.site.register(CreditClaim)