from django.urls import path
from social.views import (
    FollowToggleView, 
    FollowStatusView, 
    FollowersListView, 
    FollowingListView,
    MyMoodView, 
    UserMoodView, 
    FeedView, 
    MyActivitiesView,
)


urlpatterns = [
    path('users/<uuid:user_id>/follow/', FollowToggleView.as_view(), name='social-follow-toggle'),
    path('users/<uuid:user_id>/follow-status/', FollowStatusView.as_view(), name='social-follow-status'),
    path('users/<uuid:user_id>/followers/', FollowersListView.as_view(), name='social-followers'),
    path('users/<uuid:user_id>/following/', FollowingListView.as_view(), name='social-following'),

    path('me/mood/', MyMoodView.as_view(), name='social-my-mood'),
    path('users/<uuid:user_id>/mood/', UserMoodView.as_view(), name='social-user-mood'),

    path('feed/', FeedView.as_view(), name='social-feel'),
    path('me/activities/', MyActivitiesView.as_view(), name='social-my-activities'),
]
