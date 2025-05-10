from django.shortcuts import render
from .models import Persona
from a_projects.models import Project, Status, Technology
from .ai_tools_radar_chart import create_ai_tools_radar_chart


def home(request):
    personas = Persona.objects.all()
    radar_chart = create_ai_tools_radar_chart()
    technologies = Technology.objects.exclude(name='Other')
    try:
        status = Status.objects.get(code=1)
    except :
        status = None
    try:
        user = request.user
        user_projects = Project.objects.filter(user=user, status=status)
        context = {'personas': personas, 'projects': user_projects, 'technologies': technologies}
    except:
        context = {'personas': personas, 'radar_chart': radar_chart, 'technologies': technologies}


    return render(request, 'home.html', context)

