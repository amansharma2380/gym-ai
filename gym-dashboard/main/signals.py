from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import MemberProfile

@receiver(post_save, sender=User)
def create_member_profile(sender, instance, created, **kwargs):
    if created:
        MemberProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_member_profile(sender, instance, **kwargs):
    # When user saved, ensure profile saved too (if exists)
    try:
        instance.memberprofile.save()
    except MemberProfile.DoesNotExist:
        MemberProfile.objects.create(user=instance)
