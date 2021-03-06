from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import Group
from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from social.apps.django_app.default.models import UserSocialAuth
from djangobb_forum.models import Profile
from game_info.models import Server
from valve.rcon import RCON
from datetime import timedelta


class PremiumDonation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    keys = models.IntegerField(default = 0)
    dollars = models.FloatField(default = 0.0)
    end_time = models.DateTimeField()

    def __unicode__(self):
        return "%s expires at %s" % (self.user, self.end_time)

    class Meta:
        get_latest_by = "end_time"

class PremiumDonationHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    keys = models.IntegerField(default = 0)
    dollars = models.FloatField(default = 0.0)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()

    def __unicode__(self):
        return "%s donated %s keys and %s dollars" % (self.user, self.keys, self.dollars)

    class Meta:
        verbose_name_plural = "Premium donation history"
        get_latest_by = "end_time"


@receiver(post_delete, sender=PremiumDonation)
def premium_post_delete(sender, instance, **kwargs):
    group = Group.objects.get(name=settings.PREMIUM_GROUP_NAME)
    instance.user.groups.remove(group)
    profile = Profile.objects.get(user=instance.user)
    profile.status = ""
    profile.save()

@receiver(post_save, sender=PremiumDonation)
def premium_post_save(sender, instance, created, **kwargs):
    if created:
        group = Group.objects.get(name=settings.PREMIUM_GROUP_NAME)
        instance.user.groups.add(group)
        profile = Profile.objects.get(user=instance.user)
        profile.status = "Premium"
        profile.save()
    PremiumDonationHistory(
        user = instance.user,
        keys = instance.keys,
        dollars = instance.dollars,
        end_time = instance.end_time
    ).save()

@receiver(valid_ipn_received)
def add_premium(sender, **kwargs):
    """
        When PayPal IPN completes, add the users premium
        set an expiry time
    """
    ipn_obj = sender
    if ipn_obj.payment_status == ST_PP_COMPLETED:
        try:
            social_user = UserSocialAuth.objects.get(uid=ipn_obj.custom)
        except ObjectDoesNotExist:
            # Todo: do something here as something has gone wrong
            return
        for x in settings.DONATION_AMOUNTS:
            if x[0] == ipn_obj.mc_gross:
                try:
                    p = PremiumDonation.objects.get(user=social_user.user)
                    p.end_time += timedelta(days=x[1])
                except PremiumDonation.DoesNotExist:
                    end_time = timezone.now() + timedelta(days=x[1])
                    p = PremiumDonation(
                        user=social_user.user,
                        end_time=end_time
                    )
            p.dollars = ipn.obj.mc_gross
            p.save()

def reload_admins():
    servers = Server.objects.all()
    for server in servers:
        with RCON((server.host, server.port), settings.RCON_PASSWORD) as rcon:
            print(rcon("sm_reloadadmins"))
