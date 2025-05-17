from django.contrib import admin
from .models import Profile, Country, CreditClaim, Policy
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


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'current_plan',)
    def current_plan(self, obj):
        plan = obj.current_plan
        return plan.name if plan else '-'
    current_plan.short_description = 'Plan actuel'
admin.site.register(Profile, ProfileAdmin)


admin.site.register(CreditClaim)

admin.site.register(Policy)