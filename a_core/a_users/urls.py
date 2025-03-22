from django.urls import path
from a_users.views import *


urlpatterns = [
    path('', profile_view, name="profile"),
    path('onboarding/', profile_view, name='profile-onboarding'),
    path('settings/', profile_settings_view, name="profile-settings"),
    path('emailchange/', profile_emailchange, name="profile-emailchange"),
    path('githubkeychange/', profile_githubkeychange, name="profile-githubkeychange"),
    path('emailverify/', profile_emailverify, name="profile-emailverify"),
    path('delete/', profile_delete_view, name="profile-delete"),
    path('user/projects/', user_projects_view, name='user-projects'),
    path('claim-credits/', claim_credits_view, name="claim-credits"),
]