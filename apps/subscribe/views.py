from django.core import checks
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import SubscriptionPlan, Subscription, PinnedPost, SubscriptionHistory
from .serializers import SubscriptionSerializer, SubscriptionPlanSerializer, SubscriptionCreateSerializer, PinnedPostSerializer, SubscriptionHistorySerializer, UserSubscriptionStatusSerializer, PinPostSerializer, UnpinPostSerializer
from apps.main.models import Post

class SubscriptionPlanListView(generics.ListAPIView):
    '''spisok tarifnyh planow'''
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]
    
class SubscriptionPlanDetailView(generics.RetrieveAPIView):
    '''detalnaya informasiya'''
    queryset = SubscriptionPlan.objects.filter(is_active = True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]
    
class UserSubscriptionView(generics.RetrieveAPIView):
    '''info o podpiske usera'''
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        '''vozvrzat podpiski useru'''
        try:
            return self.request.user.subscription
        except Subscription.DoesNotExist:
            return None
        
    def retrieve(self, request, *args, **kwargs):
        '''info o podpiske usera'''
        subscription = self.get_object()
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        else:
            return Response({
                'detail': 'No subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
    
class SubscriptionHistoryView(generics.ListAPIView):
    '''istoriya izmeneniy podpiski'''
    serializer_class = SubscriptionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        '''istoriya podpiski usera'''
        try:
            subscription = self.request.user.subscription
            return subscription.history.all()
        except Subscription.DoesNotExist:
            return SubscriptionHistory.objects.none()
        
class PinnedPostView(generics.RetrieveUpdateDestroyAPIView):
    '''upravleniye zakrep postom'''
    serializer_class = PinnedPostSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        '''zakrep post usera'''
        try:
            return self.request.user.pinned_post
        except PinnedPost.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        '''vozvrat info o zakrep post'''
        pinned_post = self.get_object()
        if pinned_post:
            serializer = self.get_serializer(pinned_post)
            return Response(serializer_data)
        else:
            return Response({
                'detail': 'No pinned posts found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    def update(self, request, *args, **kwargs):
        '''obnovleniye zakrep posta'''
        if not hasattr(request.user, 'subscription') or not request.user.subscription.is_active:
            return Response({
                'error': 'Active subscription required to pin posts'
            }, status=status.HTTP_404_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        '''udaleniye zakrep posta'''
        pinned_post = self.get_object()
        if pinned_post:
            pinned_post.delete()
            return Response(status=status.HTTP_404_NO_CONTENT)
        else:
            return Response({
                'detail': 'No pinned posts'
            }, status=status.HTTP_404_NOT_FOUND)
            
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def subscription_status(request):
    '''vozvrat ststus podpiski usera'''
    serializer = UserSubscriptionStatusSerializer(request.user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pin_post(request):
    '''zakrepleniye posta usera'''
    serializer = PinnedPostSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        post_id = serializer.validated_data['post_id']
        
        try:
            with transaction.atomic():
                post = get_object_or_404(Post, id=post_id, status='published')
                
                if post.author != request.user:
                    return Response({
                        'error': 'You can only pin your own posts'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                if not hasattr(request.user, 'subscription') or not request.user.subscription.is_active:
                    return Response({
                        'error': 'Active subscription required to pin posts'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                if hasattr(request.user, 'pinned_post'):
                    request.user.pinned_post.delete()
                
                pinned_post = PinnedPost.objects.create(
                    user = request.user,
                    post = post
                )
                
                response_serializer = PinnedPostSerializer(pinned_post)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unpin_post(request):
    '''otkrepleniye posta'''
    serializer = UnpinPostSerializer(data = request.data, context={'request': request})
    
    if serializer.is_valid():
        try:
            pinned_post = request.user.pinned_post
            pinned_post.delete()
            
            return Response({
                'message': 'Post unpinned succesfully'
            }, status=status.HTTP_200_OK)
            
        except PinnedPost.DoesNotExist:
            return Response({
                'error': 'Pinned post not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request):
    '''otmena podpiski'''
    try:
        subscription = request.user.subscription
        
        if not subscription.is_active:
            return Response({
                'error': 'No active subscription found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            subscription.cancel()
            
            if hasattr(request.user, 'pinned_post'):
                request.user.pinned_post.delete()
            
            SubscriptionHistory.objects.create(
                subscription=subscription,
                action = 'cancelled',
                description = 'Subscription cancelled by user'
            )
            
        return Response({
            'message': 'Subscription cancelled succesfully'
        }, status=status.HTTP_200_OK)
    
    except Subscription.DoesNotExist:
        return Response({
            'error': 'No subscription found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def pinned_posts_list(request):
    '''spisok zakrep postov'''
    pinned_posts = PinnedPost.objects.select_related('post', 'post__author', 'post__category', 'user__subscription'
    ).filter(
        user__subscription__status='active',
        user__subscription__end_date__gt=timezone.now(),
        post__status='published'
    ).order_by('pinned_at')
    serializer = PinnedPostSerializer(pinned_posts, many=True)
    return Response(serializer.data)

    '''formiruem otvet s info o poste'''
    posts_data = []
    for pinned_post in pinned_posts:
        post = pinned_post.post
        post_data = ({
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'image': post.image.url if post.image else None,
            'category': post.category.name if post.category else None,
            'author': {
                'id': post.author.id,
                'username': post.author.username,
                'full_name': post.author.get_full_name(),
            },
            'views_count': post.views_count,
            'comments_count': post.comments_count,
            'created_at': post.created_at,
            'pinned_at': pinned_post.pinned_at,
            'is_pinned': True,
        })
        

    return Response({
        'count': int(posts_data),
        'results': posts_data,
    }) 

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def can_pin_post(request, post_id):
    '''proverka vozmozhnosti zakrepleniya posta'''
    try:
        post = get_object_or_404(Post, id=post_id, status='published')
        
        cheks = {
            'posts_exists': True,
            'is_own_post': post.author == request.user,
            'has_subscription': hasattr(request.user, 'subscription'),
            'subscription_active': False,
            'can_pin': False
        }        
        
        if checks['has_subscription']:
            checks['subscription_active'] = request.user.subscription.is_active
            
        checks['can_pin'] ={
            checks['is_own_post'] and 
            checks['has_subscription'] and
            checks['subscription_active']
        }
        
        return Response({
            'post_id': post.id,
            'can_pin': checks['can_pin'],
            'checks': checks,
            'message': 'You can pin this post' if checks['can_pin'] else 'You cannot pin this post'
        })
        
    except Post.DoesNotExist:
        return Response({
            'post_id': post_id,
            'can_pin': False,
            'checks': {
                'posts_exists': False,
            },
            'message': 'Post does not exist'
        }, status=status.HTTP_404_NOT_FOUND)