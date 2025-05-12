from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from a_users.models import Profile
from a_projects.models import Project, Component, File
from .models import CodingChat, ProcessingStep, CodingChatMessage, ChatCategory
from django.http import JsonResponse
from management.ai_bases import get_gpt_output
from .utils import parse_steps
from django.views.decorators.http import require_POST
from .ai_regular_processing_utils import ai_processing as regular_ai_processing
from .ai_super_processing_utils import ai_processing as super_ai_processing
from django.views.decorators.csrf import csrf_exempt

from asgiref.sync import sync_to_async
import asyncio


MAX_REGENERATIONS = 3
def fix_response_format(response):
    response = response.replace(", ')", ",'')")
    response = response.replace(",')", ",'')")
    return response

async def code_chat_view(request):
    user = request.user
    #profile = await sync_to_async(Profile.objects.get)(user=user)
    profile = await sync_to_async(lambda: Profile.objects.select_related('default_project', 'default_chat_category').get(user=user))()
    default_project = profile.default_project
    default_chat_category = profile.default_chat_category
    available_credits = profile.available_credits
    components = await sync_to_async(lambda: Component.objects.filter(file__project=default_project))()
    files = await sync_to_async(list)(File.objects.filter(project=default_project))
    try :
        technology = await sync_to_async(lambda: default_project.technology)()
    except :
        technology = None
    projects = await sync_to_async(lambda: list(Project.objects.filter(user=user).exclude(technology__name='Other').exclude(status__name='inactive')))()

    if request.method == 'POST':

        ############################################## Regenerate #########################################3
        # Handle regeneration
        if 'regenerate' in request.POST:
            print('regenerating')
            try:
                chat_id = int(request.POST.get('chat_id'))
                # Load chat with its category in a non-blocking way
                chat = await sync_to_async(CodingChat.objects.select_related('chat_category').get)(id=chat_id,
                                                                                                   user=user)
                # Count existing messages without blocking
                msg_count = await sync_to_async(chat.messages.count)()
                # Enforce max 3 regenerations
                if chat.regeneration_count < 3:
                    # Fetch last user prompt
                    last_prompt_obj = await sync_to_async(
                        lambda: chat.messages.filter(type='prompt').order_by('-id').first())()
                    prompt = last_prompt_obj.content if last_prompt_obj else ''
                    # Next attempt number
                    attempt_no = chat.regeneration_count + 2
                    # Call AI based on category
                    if chat.chat_category.type == 'regular':
                        ai_response = await regular_ai_processing(prompt, components, chat, False, technology)
                    else:
                        ai_response = await super_ai_processing(prompt, files, components, chat, False, technology)
                    # Update regeneration count
                    chat.regeneration_count += 1
                    await sync_to_async(chat.save)()
                    # Prepare processing steps map
                    steps_map = await sync_to_async(
                        lambda: {f'{s.order} : {s.name}': s for s in ProcessingStep.objects.all()})()
                    # Save regenerated prompt
                    await sync_to_async(CodingChatMessage.objects.create)(
                        chat=chat,
                        type='prompt',
                        content=prompt,
                        order=msg_count + 1,
                        attempt_number=attempt_no,
                        processing_step=steps_map.get('1 : user prompt 1')
                    )
                    # Save regenerated AI answer
                    await sync_to_async(CodingChatMessage.objects.create)(
                        chat=chat,
                        type='gpt-a',
                        content=ai_response,
                        order=msg_count + 2,
                        attempt_number=attempt_no,
                        processing_step=steps_map.get('5 : ai answer 2')
                    )
                    return JsonResponse({'status': 'success', 'chat_id': chat.id})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Max regenerations reached'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        ################################################## FIRST PROMPT #########################################3
        if 'prompt' in request.POST and 'regenerate' not in request.POST:
            print('PROMPT !!!')
            prompt = request.POST.get('prompt')
            chat_id = request.POST.get('chat_id')
            if chat_id:
                chat = await sync_to_async(CodingChat.objects.get)(id=chat_id, user=user)
                default_chat_category = await sync_to_async(lambda: chat.chat_category)()
                is_first_prompt = False
            else:
                chat = await sync_to_async(CodingChat.objects.create)(user=user, project=default_project)
                is_first_prompt = True
            if available_credits >= default_chat_category.price:
                if chat.title is None :
                    chat.title = prompt[:25] + '...' if len(prompt) >= 28 else prompt
                    await sync_to_async(chat.save)()

                if default_chat_category.type == 'regular':
                    ai_response = await regular_ai_processing(prompt, components, chat, is_first_prompt, technology)
                elif default_chat_category.type == 'super':
                    ai_response = await super_ai_processing(prompt, files, components, chat, is_first_prompt, technology )
                if is_first_prompt:
                    profile.available_credits = available_credits - default_chat_category.price
                else:
                    profile.available_credits = available_credits - default_chat_category.price_secondary_prompt
                await sync_to_async(profile.save)()
                steps = parse_steps(fix_response_format(ai_response))
                return JsonResponse({
                    'user_message': prompt,
                    'ai_response': ai_response,
                    'ai_message': ai_response,
                    'chat_id': chat.id,
                    'steps': steps
                })
            else:
                processing_steps = await sync_to_async(lambda: {f'{step.order} : {step.name}': step
                                                                for step in ProcessingStep.objects.all()})()
                if chat.title is None:
                    chat.title = prompt[:25] + '...' if len(prompt) >= 28 else prompt
                    await sync_to_async(chat.save)()
                await sync_to_async(CodingChatMessage.objects.create)(
                    chat=chat, type='prompt', processing_step=processing_steps.get('1 : user prompt 1'),
                    content=prompt, order=1, api_key=None
                )
                ai_response = '<step1><Justifications>Please come back tomorrow to claim your free credits or buy more credits! </Justifications></step1>'
                steps = parse_steps(fix_response_format(ai_response))
                await sync_to_async(CodingChatMessage.objects.create)(
                    chat=chat, type='gpt-a', content=ai_response, order=5, api_key=None,
                    processing_step=processing_steps.get('5 : ai answer 2')
                )
                return JsonResponse({
                    'user_message': prompt,
                    'ai_response': ai_response,
                    'ai_message': ai_response,
                    'chat_id': chat.id,
                    'steps': steps
                })
        elif 'rate' in request.POST:
            chat_id = request.POST.get('chat_id')
            if chat_id:
                rating_value = int(request.POST.get('rate'))
                chat = await sync_to_async(CodingChat.objects.get)(id=chat_id, user=user)
                chat.rate = rating_value
                await sync_to_async(chat.save)()
                return JsonResponse({'status': 'success', 'rate': chat.rate})
    else:
        chats = await sync_to_async(
            lambda: list(CodingChat.objects.filter(user=user, project=default_project).order_by('-created_on')))()
        chat_id = request.GET.get('chat_id')
        selected_attempt = int(request.GET.get('attempt', '1'))
        if chat_id:
            current_chat = await sync_to_async(
                lambda: CodingChat.objects.select_related('chat_category').get(id=chat_id, user=user))()
            # total attempts = regeneration_count+1
            total_attempts = current_chat.regeneration_count + 1
            # clamp selected
            if selected_attempt < 1 or selected_attempt > total_attempts:
                selected_attempt = total_attempts
            raw_messages = await sync_to_async(lambda: list(
                current_chat.messages.filter(attempt_number=selected_attempt,
                                             type__in=['prompt', 'gpt-a', 'gpt-q']).order_by('id')
            ))()
            messages = []
            for msg in raw_messages:
                msg_dict = {
                    'type': msg.type,
                    'attempt_number': msg.attempt_number,
                }
                if msg.type == 'gpt-a':
                    msg_dict['steps'] = parse_steps(fix_response_format(msg.content))
                else:
                    msg_dict['content'] = msg.content
                messages.append(msg_dict)
        else:
            current_chat = None
            messages = []
            total_attempts = 1
            selected_attempt = 1
        chatcategories = await sync_to_async(lambda: list(ChatCategory.objects.all()))()
        context = {
            'chats': chats, 'messages': messages, 'current_chat': current_chat,
            'projects': projects, 'default_project': default_project, 'profile': profile,
            'chatcategories': chatcategories,
            'selected_attempt': selected_attempt, 'total_attempts': total_attempts
        }
        return render(request, 'b_coding/code_chat.html', context)


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
        chats = CodingChat.objects.filter(project=project).order_by('-created_on')
        chats_data = []
        for chat in chats:
            chats_data.append({
                'id': chat.id,
                'title': chat.title,
            })

        return JsonResponse({
            'status': 'success',
            'chats': chats_data,
        })
    except Project.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=400)


@login_required
def update_default_chatcategory(request):
    if request.method == 'POST':
        chatcategory_id = request.POST.get('chatcategory_id')
        try:
            chatcategory = ChatCategory.objects.get(id=chatcategory_id)
            profile = request.user.profile
            profile.default_chat_category = chatcategory
            profile.save()
            return JsonResponse({'status': 'success'})
        except ChatCategory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'ChatCategory does not exist'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



@csrf_exempt
def delete_chat(request):
    if request.method == 'POST':
        chat_id = request.POST.get('chat_id')
        try:
            chat = CodingChat.objects.get(pk=chat_id)
            chat.delete()
            return JsonResponse({'status': 'success'})
        except Chat.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Chat not found.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


async def get_processing_updates(request):
    await asyncio.sleep(5)
    chat_id = request.GET.get('chat_id')
    if chat_id:
        latest_chat = await sync_to_async(lambda: CodingChat.objects.filter(id=chat_id, user=request.user).first())()
    else:
        latest_chat = await sync_to_async(
            lambda: CodingChat.objects.filter(user=request.user).order_by('-created_on').first())()
    if not latest_chat:
        return JsonResponse({'messages': []})
    last_id = int(request.GET.get('last_id', 0))
    messages = await sync_to_async(lambda: list(
        CodingChatMessage.objects
        .filter(chat_id=latest_chat.id, type='ai', id__gt=last_id)
        .order_by('id')
        .values('id', 'content')
    ))()
    return JsonResponse({'messages': messages})