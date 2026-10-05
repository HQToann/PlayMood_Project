from django.urls import path
from social.views import (
    FollowToggleView,
    FollowStatusView,
    FollowersListView,
    FollowingListView,
    MoodTypeListView,
    MoodThemeListView,
    MyMoodView,
    UserMoodView,
    FeedView,
    MyActivitiesView,
    # Follow Request views
    FollowRequestReceivedView,
    FollowRequestSentView,
    FollowRequestAcceptView,
    FollowRequestRejectView,
    FollowRequestCancelView,
    FriendsListView,
)

urlpatterns = [
    # Follow
    path('users/<uuid:user_id>/follow/', FollowToggleView.as_view(), name='social-follow-toggle'),
    path('users/<uuid:user_id>/follow-status/', FollowStatusView.as_view(), name='social-follow-status'),
    path('users/<uuid:user_id>/followers/', FollowersListView.as_view(), name='social-followers'),
    path('users/<uuid:user_id>/following/', FollowingListView.as_view(), name='social-following'),

    # Mood Types & Themes (public, no auth required)
    path('mood-themes/', MoodThemeListView.as_view(), name='social-mood-themes'),
    path('mood-types/', MoodTypeListView.as_view(), name='social-mood-types'),

    # Mood
    path('me/mood/', MyMoodView.as_view(), name='social-my-mood'),
    path('users/<uuid:user_id>/mood/', UserMoodView.as_view(), name='social-user-mood'),

    # Feed & Activity
    path('feed/', FeedView.as_view(), name='social-feed'),
    path('me/activities/', MyActivitiesView.as_view(), name='social-my-activities'),

    # Follow Requests
    path('follow-requests/received/', FollowRequestReceivedView.as_view(), name='social-follow-requests-received'),
    path('follow-requests/sent/', FollowRequestSentView.as_view(), name='social-follow-requests-sent'),
    path('follow-requests/<uuid:request_id>/accept/', FollowRequestAcceptView.as_view(), name='social-follow-request-accept'),
    path('follow-requests/<uuid:request_id>/reject/', FollowRequestRejectView.as_view(), name='social-follow-request-reject'),
    path('follow-requests/<uuid:request_id>/cancel/', FollowRequestCancelView.as_view(), name='social-follow-request-cancel'),

    # Friends
    path('friends/', FriendsListView.as_view(), name='social-friends'),
]
