from django.views.generic.edit import FormView
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from .forms import DonateForm
from .models import PremiumDonationHistory, PremiumDonation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import KeyDonationSerializer
from social.apps.django_app.default.models import UserSocialAuth
from datetime import timedelta
import uuid


class DonateView(FormView):
    template_name = 'donations/donate.html'
    form_class = DonateForm
    success_url = '/thanks/'

    def get_context_data(self, **kwargs):
        context = super(DonateView, self).get_context_data(**kwargs)
        context['steam'] = self._get_steam()
        if self.request.user.is_authenticated():
            try:
                context['latestdonation'] = PremiumDonationHistory.objects.filter(user=self.request.user).latest()
                if context['latestdonation'].end_time > timezone.now():
                    context['donation_ended'] = False
                else:
                    context['donation_ended'] = True
            except PremiumDonationHistory.DoesNotExist:
                context['latestdonation'] = None
        else:
            context['latestdonation'] = None
        return context

    def _get_steam(self):
        if self.request.user.is_authenticated():
            try:
                u = self.request.user.social_auth.filter(provider="steam").get()
                return u.uid
            except ObjectDoesNotExist:
                pass

        return None

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """

        steam = self._get_steam()

        domain = get_current_site(self.request).domain

        initial = {
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "item_name": "Donation",
            "invoice": str(steam)+":"+uuid.uuid4().hex,
            "notify_url": "https://" + domain + reverse('paypal-ipn'),
            "return_url": settings.PAYPAL_REDIRECT_URL,
            "cancel_return": settings.PAYPAL_CANCEL_URL,
            "custom": steam,  # Custom command to correlate to some function later (optional)
        }

        return initial


class KeyDonation(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        serializer = KeyDonationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                social_user = UserSocialAuth.objects.get(uid=serializer.data["steamid64"])
            except ObjectDoesNotExist:
                # Todo: do something here as something has gone wrong
                return Response({"steamid64": "user does not exist"}, status=status.HTTP_404_NOT_FOUND)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        serializer = KeyDonationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                social_user = UserSocialAuth.objects.get(uid=serializer.data["steamid64"])
            except ObjectDoesNotExist:
                # Todo: do something here as something has gone wrong
                return Response({"steamid64": "user does not exist"}, status=status.HTTP_404_NOT_FOUND)

            days = 7 if serializer.data["amount"] == 1 else (20 * serializer.data["amount"] - 10)
            try:
                p = PremiumDonation.objects.get(user=social_user.user)
                p.end_time += timedelta(days=days)
            except PremiumDonation.DoesNotExist:
                end_time = timezone.now() + timedelta(days)
                p = PremiumDonation(
                    user=social_user.user,
                    end_time=end_time
                )
            p.keys = serializer.data["amount"]
            p.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
