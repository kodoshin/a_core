from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from a_users.models import Profile
from a_projects.models import Project, Component, File
from .models import PlanningChat, PlanningProcessingStep, PlanningChatMessage, PlanningChatCategory, PlanningProcessingError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
#from management.ai_bases import get_gpt_output

from django.views.decorators.csrf import csrf_exempt
from management.ai_bases import async_get_ai_title
from asgiref.sync import sync_to_async
import asyncio
from django.db.models import Max



def fix_response_format(response):
    response = response.replace(", ')", ",'')")
    response = response.replace(",')", ",'')")
    return response



def planning_chat_view(request):
    user = request.user
    profile = Profile.objects.select_related('default_project', 'default_chat_category').get(user=user)
    default_project = profile.default_project
    default_chat_category = profile.default_chat_category
    chats = PlanningChat.objects.filter(user=user, project=default_project).order_by('-created_on')
    projects = Project.objects.filter(user=user).exclude(technology__name='Other').exclude(status__name='inactive')
    chatcategories = PlanningChatCategory.objects.filter(is_active=True).order_by('price')
    context = {
        'chats': chats,
        'projects': projects,
        'default_project': default_project,
        'profile': profile,
        'chatcategories': chatcategories,
        'default_chat_category': default_chat_category,
        'access_advanced_models': profile.current_plan.advanced_models
    }
    return render(request, 'b_planning/planning_chat.html', context)



@login_required
@require_POST
def update_default_project(request):
    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id, user=request.user)
        profile = Profile.objects.get(user=request.user)
        profile.default_project = project
        profile.save()

        # Récupérer la liste des chats du projet
        chats = PlanningChat.objects.filter(project=project).order_by('-created_on')
        chats_data = []
        for chat in chats:
            chats_data.append({
                'id': chat.public_id,
                'title': chat.title,
                'important': chat.important,
            })
        print('PLANNING CHATS :')
        print(chats_data)
        # Prepare chat categories
        chatcategories = PlanningChatCategory.objects.all().order_by('price')
        chatcategories_data = []
        for cat in chatcategories:
            chatcategories_data.append({
                'id': cat.id,
                'name': cat.name,
                'price': str(cat.price),
                'is_large': cat.is_large,
                'is_advanced': cat.is_advanced,
            })

        # Permission flags
        access_large = profile.current_plan.large_models
        access_advanced = profile.current_plan.advanced_models
        default_is_large = project.is_large

        return JsonResponse({
            'status': 'success',
            'chats': chats_data,
            'chatcategories': chatcategories_data,
            'default_project_is_large': default_is_large,
            'access_large_models': access_large,
            'access_advanced_models': access_advanced,
        })
    except Project.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=400)




@login_required
def update_planning_default_chatcategory(request):
    if request.method == 'POST':
        chatcategory_id = request.POST.get('planning_chatcategory_id')
        print('UPDATING CHAT CAT')
        try:
            print(chatcategory_id)
            chatcategory = PlanningChatCategory.objects.get(id=chatcategory_id)
            profile = request.user.profile
            profile.default_planning_chat_category = chatcategory
            profile.save()
            return JsonResponse({'status': 'success'})
        except PlanningChatCategory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'ChatCategory does not exist'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



@csrf_exempt
@login_required
def delete_chat(request):
    if request.method == 'POST':
        chat_id = request.POST.get('chat_id')
        try:
            chat = PlanningChat.objects.get(public_id=chat_id, user=request.user)
            chat.delete()
            return JsonResponse({'status': 'success'})
        except PlanningChat.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Chat not found.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

"""
async def get_processing_updates(request):
    await asyncio.sleep(5)
    chat_id = request.GET.get('chat_id')
    if chat_id:
        latest_chat = await sync_to_async(lambda: PlanningChat.objects.filter(public_id=chat_id, user=request.user).first())()
    else:
        latest_chat = await sync_to_async(
            lambda: PlanningChat.objects.filter(user=request.user).order_by('-created_on').first())()
    if not latest_chat:
        return JsonResponse({'messages': []})
    last_id = int(request.GET.get('last_id', 0))
    last_attempt_data = await sync_to_async(
        lambda: PlanningChatMessage.objects.filter(chat=latest_chat).aggregate(max_attempt=Max('attempt_number'))
    )()
    last_attempt = last_attempt_data.get('max_attempt') or 1
    messages = await sync_to_async(lambda: list(
        PlanningChatMessage.objects
        .filter(chat_id=latest_chat.id, type='ai', attempt_number=last_attempt, id__gt=last_id)
        .order_by('id')
        .values('id', 'content')
    ))()
    return JsonResponse({'messages': messages})
"""



@require_POST
@login_required
def toggle_chat_importance(request):
    chat_id = request.POST.get('chat_id')
    try:
        chat = PlanningChat.objects.get(public_id=chat_id, user=request.user)
        chat.important = not chat.important
        chat.save()
        return JsonResponse({'status': 'success', 'important': chat.important})
    except PlanningChat.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Chat not found.'}, status=404)

"""
async def chat_category_comparison_view(request):
    chatcategories = await sync_to_async(
        lambda: list(PlanningChatCategory.objects.filter(is_active=True).order_by('price'))
    )()
    return render(
        request,
        'b_coding/chat_category_comparison.html',
        {'chatcategories': chatcategories}
    )
"""

async def planning_chat_category_comparison_view(request):
    chatcategories = await sync_to_async(
        lambda: list(PlanningChatCategory.objects.filter(is_active=True).order_by('price'))
    )()
    return render(
        request,
        'b_planning/chat_category_comparison.html',
        {'chatcategories': chatcategories}
    )


