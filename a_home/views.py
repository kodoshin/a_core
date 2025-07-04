from django.shortcuts import render
from .models import Persona
from a_projects.models import Project, Status, Technology
from .ai_tools_radar_chart import create_ai_tools_radar_chart
from b_coding.models import CodingChat
from b_insights.models import InsightChat
from git_auth.views import get_github_token
from newsletter.forms import NewsletterSubscriptionForm

def home(request):
    personas = Persona.objects.all()
    radar_chart = create_ai_tools_radar_chart()
    technologies = Technology.objects.exclude(name='Other').exclude(status__name='inactive')
    try:
        status = Status.objects.get(code=1)
    except :
        status = None

    if request.user.is_authenticated:
        profile = request.user.profile
        onboarding = {
            "token": bool(get_github_token(request.user)),
            "project": Project.objects.filter(user=request.user).exists(),
            "coding": CodingChat.objects.filter(user=request.user).exists(),
            "insight": InsightChat.objects.filter(user=request.user).exists(),
        }

        onboarding_track = onboarding["true_count"] = sum(onboarding.values())


        user_projects = Project.objects.filter(user=request.user, status=status).order_by('-id')
        plan_limit = request.user.profile.current_plan.project_limits
        can_create = user_projects.count() < plan_limit
        context = {
            'personas': personas,
            'projects': user_projects,
            'technologies': technologies,
            'can_create': can_create,
            'plan_limit': plan_limit,
            'onboarding': onboarding,
            'onboarding_track': onboarding_track,
            'onboarding_done': profile.onboarding_is_done,
        }
    else:
        form = NewsletterSubscriptionForm()
        context = {
            'personas': personas,
            'radar_chart': radar_chart,
            'technologies': technologies,
            'newsletter_form': form,
        }


    return render(request, 'home.html', context)


def learn_more_about_ai_models(request):
    personas = Persona.objects.all()
    radar_chart = create_ai_tools_radar_chart()
    technologies = Technology.objects.exclude(name='Other').exclude(status__name='inactive')
    try:
        status = Status.objects.get(code=1)
    except:
        status = None

    if request.user.is_authenticated:
        user_projects = Project.objects.filter(user=request.user, status=status).order_by('-id')
        plan_limit = request.user.profile.current_plan.project_limits
        can_create = user_projects.count() < plan_limit
        context = {
            'personas': personas,
            'projects': user_projects,
            'technologies': technologies,
            'can_create': can_create,
            'plan_limit': plan_limit,
        }
    else:
        context = {
            'personas': personas,
            'radar_chart': radar_chart,
            'technologies': technologies
        }
    return render(request, 'home.html', context)

