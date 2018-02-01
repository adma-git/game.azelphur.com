from paypal.standard.ipn.models import PayPalIPN
from django.conf import settings
from django.db.models import Sum, F, IntegerField
from decimal import Decimal
import datetime
from django.utils import timezone
from donations.models import PremiumDonationHistory

def donations(request):
    now = timezone.now()
    amount = PremiumDonationHistory.objects.filter(
        start_time__gt = datetime.date(now.year, now.month, 1)
    ).aggregate(amount = Sum((F('keys') * 2) + F('dollars'), output_field=IntegerField()))['amount']
    if amount == None:
        amount = Decimal("0.0")
    amount_max = Decimal(settings.MONTHLY_DONATION_AMOUNT)
    amount_needed = amount_max-amount if amount_max-amount > 0 else 0
    context = {'donation_amount' : "%g" % (amount),
               'donation_max' : "%g" % (amount_max),
               'donation_needed' : "%g" % (amount_needed),
               'donation_percent' : "%g" % ((amount/amount_max)*100)}
    return context
