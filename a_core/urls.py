"""
URL configuration for a_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from a_users.views import profile_view
from a_home.views import home, learn_more_about_ai_models
from django.views.generic import TemplateView
from a_projects.views import github_webhook
from . import views


def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('', home, name='home'),
    path('', include('newsletter.urls')),
    path('sentry-debug/', trigger_error),
    path('learn-more-about-ai-models/', learn_more_about_ai_models, name='learn_more_about_ai_models'),
    path('admin/', admin.site.urls),
    path('git/', include('git_auth.urls')),

    path('profile/', include('a_users.urls')),
    path('projects/', include('a_projects.urls')),
    path('ai/', include('b_coding.urls')),
    path('ai/', include('b_planning.urls')),
    path('ai/', include('b_insights.urls')),
    path('@<username>/', profile_view, name="profile"),
    path('pricing/', include('management.urls')),
    path('accounts/', include('allauth.urls')),
    path('accounts/popup/close/', views.popup_close, name='popup-close'),
    #FOOTER PAGES
    path('privacy-policy/', TemplateView.as_view(template_name='footerpages/privacy_policy.html'), name='privacy_policy'),
    path('terms-of-service/', TemplateView.as_view(template_name='footerpages/terms_of_service.html'), name='terms_of_service'),
    path('legal-center/', TemplateView.as_view(template_name='footerpages/legal_center.html'), name='legal_center'),
]

# Only used when DEBUG=True, whitenoise can serve files when DEBUG=False
#if settings.DEBUG:
#    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
