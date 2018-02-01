from django.contrib import admin
from .models import PremiumDonation, PremiumDonationHistory
from rest_framework.authtoken.admin import TokenAdmin

TokenAdmin.raw_id_fields = ('user',)

class PremiumDonationAdmin(admin.ModelAdmin):
    list_display = ('user', 'end_time')

class PremiumDonationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'keys', 'dollars', 'start_time', 'end_time')

admin.site.register(PremiumDonation, PremiumDonationAdmin)
admin.site.register(PremiumDonationHistory, PremiumDonationHistoryAdmin)
