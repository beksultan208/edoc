from django.contrib import admin
from .models import Signature


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ["document", "user", "signed_at", "ip_address", "is_valid"]
    list_filter = ["is_valid"]
    raw_id_fields = ["document", "user"]
    readonly_fields = ["signed_at"]
