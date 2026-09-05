from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Subscription, SubscriptionHistory, PinnedPost

@receiver(post_save, sender=Subscription)
def subscription_post_save(sender, instance, created, **kwargs):
    if created:
        # Create a new SubscriptionHistory entry when a Subscription is created
        SubscriptionHistory.objects.create(
            subscription=instance,
            action='created',
            description=f'Subscription created for plan {instance.plan.name}.'
        )
    else:
        # Create a new SubscriptionHistory entry when a Subscription is updated
        if hasattr(instance, '_previous_state'):
            if instance.previous_status != instance.status:
                SubscriptionHistory.objects.create(
                    subscription=instance,
                    action=instance.status,
                    description=f'Subscription status changed from {instance.previous_status} to {instance.status}.'
                )

@receiver(pre_delete, sender=Subscription)
def subscription_pre_delete(sender, instance, **kwargs):
    '''obrabotchik udaleniya podpiski, sozdayushchiy zapis v istorii'''
    try:
        instance.user.pinned_post.delete()
    except PinnedPost.DoesNotExist:
        pass

@receiver(post_save, sender=PinnedPost)
def pinned_post_save(sender, instance, created, **kwargs):
    '''sohraneniye zakrep posta'''
    if created:
        '''proverka na podpisku active'''
        if not hasattr(instance.user, 'subscription') or not instance.user.subscription.is_active:
            instance.delete()
            return
        '''zapis v istoriyu'''
        SubscriptionHistory.objects.create(
            subscription=instance.user.subscription,
            action='post_pinned',
            description=f'Post "{instance.post.title}" pinned',
            metadata={
                'post_id': instance.post.id,
                'post_title': instance.post.title
            }
        )

@receiver(pre_delete, sender=PinnedPost)
def pinned_post_pre_delete(sender, instance, **kwargs):
    '''udaleniye zakrep posta'''
    if hasattr(instance.user, 'subscription'):
        SubscriptionHistory.objects.create(
            subscription=instance.user.subscription,
            action='post_unpinned',
            description=f'Post "{instance.post.title}" unpinned',
            metadata={
                'post_id': instance.post.id,
                'post_title': instance.post.title
            }
        )

