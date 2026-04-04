from django.contrib import admin
from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "inn", "owner", "created_at"]
    list_filter = ["type"]
    search_fields = ["name", "inn"]
    raw_id_fields = ["owner"]
