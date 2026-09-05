from celery import shared_task
from django.utils import timezone
from .models import Subscription, PinnedPost, SubscriptionHistory

@shared_task
def check_expired_subscriptions():
    '''proverka istekshih podpisok'''
    now = timezone.now()
    
    expired_subscriptions = Subscription.objects.filter(status='active', end_date__lt=now)
    expire_count = 0
    pinned_post_removed = 0
    
    for subscription in expired_subscriptions:
        subscription.delete()
        expired_count += 1
        
        try:
            pinned_post = subscription.user.pinned_post
            pinned_post.delete()
            pinned_post_removed += 1
        except PinnedPost.DoesNotExist:
            pass
    
        SubscriptionHistory.objects.create(
            subscription=subscription,
            action = 'expired',
            description = f'Subscription expired automatically',
        )
          
    return {
        'expired_subscriptions': expire_count,
        'pinned_posts_removed': pinned_post_removed
    }
    
@shared_task
def send_subscription_expiry_reminder():
    '''otpravka napominaniya ob istecheniii podiski'''
    
    from datetime import timedelta
    from django.core.mail import send_mail
    from django.conf import settings
    
    '''nahodim podpiski s 3 dnyami''' 
    reminder_date = timezone.now() + timedelta(days=3)
    
    expiring_subscriptions = Subscription.objects.filter(status='active', end_date__date=reminder_date.date(), auto_renew=False)
    
    sent_count = 0
    
    for subscription in expiring_subscriptions:
        try:
            send_mail(
                subject='Subscription Expiry Reminder',
                message=f'Dear {subscription.user.full_name} or {subscription.user.username}, your subscription for plan {subscription.plan.name} will expire on {subscription.end_date}. Please renew your subscription to continue enjoying our services.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[subscription.user.email],
                fail_silently=True,
            )
            
            sent_count += 1
        except Exception as e:
            print(f"Failed to send reminder email to {subscription.user.email}: {e}")
    
    return {'reminder_emails_sent': sent_count}