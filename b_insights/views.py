from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from a_users.models import Profile
from .utils import parse_steps
from a_projects.models import Project, Component, File
from .models import InsightChat, InsightProcessingStep, InsightChatMessage, InsightChatCategory, InsightProcessingError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
#from management.ai_bases import get_gpt_output
from .insights_regular_processing_utils import ai_processing as regular_ai_processing

from django.views.decorators.csrf import csrf_exempt
from management.ai_bases import async_get_ai_title
from asgiref.sync import sync_to_async
import asyncio
from django.db.models import Max



def fix_response_format(response):
    response = response.replace(", ')", ",'')")
    response = response.replace(",')", ",'')")
    return response



async def insights_chat_view(request):
    user = request.user
    # profile = await sync_to_async(Profile.objects.get)(user=user)
    profile = await sync_to_async(
        lambda: Profile.objects.select_related('default_project', 'default_chat_category').get(user=user))()
    default_project = await sync_to_async(lambda: profile.default_insights_project)()
    default_chat_category = await sync_to_async(lambda: profile.default_insight_chat_category)()
    available_credits = profile.available_credits
    max_attempts = await sync_to_async(lambda: profile.current_plan.regeneration_attempts)()
    components = await sync_to_async(lambda: Component.objects.filter(file__project=default_project))()
    files = await sync_to_async(list)(File.objects.filter(project=default_project))
    in_progress = False
    try:
        technology = await sync_to_async(lambda: default_project.technology)()
    except:
        technology = None
    projects = await sync_to_async(lambda: list(
        Project.objects.filter(user=user).exclude(technology__name='Other').exclude(status__name='inactive')))()

    if request.method == 'POST':

        ############################################## Regenerate #########################################
        # Handle regeneration
        if 'regenerate' in request.POST:
            print('regenerating')
            try:
                chat_id = request.POST.get('chat_id')
                # Load chat with its category in a non-blocking way
                chat = await sync_to_async(InsightChat.objects.select_related('chat_category').get)(
                    public_id=chat_id,
                    user=user)
                # Count existing messages without blocking
                msg_count = await sync_to_async(chat.messages.count)()
                # Enforce max regenerations number
                if chat.regeneration_count < max_attempts:
                    # Fetch last user prompt
                    last_prompt_obj = await sync_to_async(
                        lambda: chat.messages.filter(type='prompt').order_by('id').first())()
                    prompt = last_prompt_obj.content if last_prompt_obj else ''
                    # Next attempt number
                    attempt_count = chat.regeneration_count + 2
                    # Call AI based on category
                    if chat.chat_category.type == 'navigator':
                        ai_response = await regular_ai_processing(prompt, components, chat, True, technology, attempt_count)
                    elif chat.chat_category.type == 'oracle':
                        print('regenerating super prompt')
                        ai_response = await regular_ai_processing(prompt, files, components, chat, True, technology, attempt_count)
                    elif chat.chat_category.type == 'large':
                        print('regenerating large prompt')
                        ai_response = await regular_ai_processing(prompt, files, components, chat, True, technology, attempt_count)
                    elif chat.chat_category.type == 'ultimate':
                        print('regenerating ultimate prompt')
                        ai_response = await regular_ai_processing(prompt, files, components, chat, True, technology, attempt_count)
                    elif chat.chat_category.type == 'supreme':
                        print('regenerating supreme prompt')
                        ai_response = await regular_ai_processing(prompt, files, components, chat, True, technology, attempt_count)

                    # Update regeneration count
                    chat.regeneration_count += 1
                    await sync_to_async(chat.save)()
                    # Prepare processing steps map
                    return JsonResponse({'status': 'success', 'chat_id': chat.public_id})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Max regenerations reached'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        ################################################## FIRST PROMPT #########################################
        if 'prompt' in request.POST and 'regenerate' not in request.POST:
            # print('PROMPT !!!')
            prompt = request.POST.get('prompt')
            chat_id = request.POST.get('chat_id')
            try:
                attempt_no = int(request.POST.get('attempt_no', '1'))
            except ValueError:
                attempt_no = 1
            # print(attempt_no)
            if chat_id:
                chat = await sync_to_async(InsightChat.objects.get)(public_id=chat_id, user=user)
                default_chat_category = await sync_to_async(lambda: chat.chat_category)()
                is_first_prompt = False
            else:
                chat = await sync_to_async(InsightChat.objects.create)(user=user, project=default_project)
                placeholder_title = prompt[:25] + '...' if len(prompt) > 25 else prompt
                chat.title = placeholder_title
                await sync_to_async(chat.save)()
                is_first_prompt = True

            if available_credits >= default_chat_category.price:
                # if chat.title is None :
                #    chat.title = prompt[:25] + '...' if len(prompt) >= 28 else prompt
                #    await sync_to_async(chat.save)()

                title_task = (
                    asyncio.create_task(async_get_ai_title(prompt))
                    if chat.title is None or chat.regeneration_count == 0
                    else None
                )

                if default_chat_category.type == 'navigator':
                    response_task = asyncio.create_task(
                        regular_ai_processing(
                            prompt, components, chat, is_first_prompt, technology, attempt_no
                        )
                    )
                elif default_chat_category.type == 'oracle':
                    response_task = asyncio.create_task(
                        regular_ai_processing(
                            prompt, files, components, chat, is_first_prompt, technology, attempt_no
                        )
                    )
                elif default_chat_category.type == 'large':
                    response_task = asyncio.create_task(
                        regular_ai_processing(
                            prompt, files, components, chat, is_first_prompt, technology, attempt_no
                        )
                    )
                elif default_chat_category.type == 'ultimate':
                    response_task = asyncio.create_task(
                        regular_ai_processing(
                            prompt, files, components, chat, is_first_prompt, technology, attempt_no
                        )
                    )
                elif default_chat_category.type == 'supreme':
                    response_task = asyncio.create_task(
                        regular_ai_processing(
                            prompt, files, components, chat, is_first_prompt, technology, attempt_no
                        )
                    )

                # Await the AI response
                ai_response = await response_task
                ai_response = ai_response.replace("&gt;", ">").replace("&lt;", "<")

                if title_task:
                    ai_title = await title_task
                    chat.title = ai_title[:28]
                    await sync_to_async(chat.save)()

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
                    'chat_id': chat.public_id,
                    'steps': steps
                })
            else:
                processing_steps = await sync_to_async(lambda: {f'{step.order} : {step.name}': step
                                                                for step in InsightProcessingStep.objects.all()})()
                if chat.title is None:
                    chat.title = prompt[:25] + '...' if len(prompt) >= 28 else prompt
                    await sync_to_async(chat.save)()
                await sync_to_async(InsightChatMessage.objects.create)(
                    chat=chat, type='prompt', processing_step=processing_steps.get('1 : user prompt 1'),
                    content=prompt, order=1, api_key=None
                )
                ai_response = '<step1><Justifications>Please come back tomorrow to claim your free credits or buy more credits! </Justifications></step1>'
                steps = parse_steps(fix_response_format(ai_response))
                await sync_to_async(InsightChatMessage.objects.create)(
                    chat=chat, type='gpt-a', content=ai_response, order=5, api_key=None,
                    processing_step=processing_steps.get('5 : ai answer 2')
                )
                return JsonResponse({
                    'user_message': prompt,
                    'ai_response': ai_response,
                    'ai_message': ai_response,
                    'chat_id': chat.public_id,
                    'steps': steps
                })
        elif 'rate' in request.POST:
            chat_id = request.POST.get('chat_id')
            if chat_id:
                rating_value = int(request.POST.get('rate'))
                chat = await sync_to_async(InsightChat.objects.get)(public_id=chat_id, user=user)
                chat.rate = rating_value
                await sync_to_async(chat.save)()
                return JsonResponse({'status': 'success', 'rate': chat.rate})
    else:
        chats = await sync_to_async(
            lambda: list(InsightChat.objects.filter(user=user, project=default_project).order_by('-created_on')))()
        chat_id = request.GET.get('chat_id')
        if chat_id:
            # On récupère le chat et le nombre total d'essais
            try:
                current_chat = await sync_to_async(
                    lambda: InsightChat.objects.select_related('chat_category').get(public_id=chat_id, user=user))()
            except InsightChat.DoesNotExist:
                return redirect('code_chat_view')
            total_attempts = current_chat.regeneration_count + 1

            # On récupère le paramètre "attempt" s'il existe, sinon on prend toujours le dernier essai
            attempt_param = request.GET.get('attempt')
            if attempt_param:
                try:
                    selected_attempt = int(attempt_param)
                except ValueError:
                    selected_attempt = total_attempts
            else:
                selected_attempt = total_attempts

            # On borne la valeur entre 1 et total_attempts
            if selected_attempt < 1 or selected_attempt > total_attempts:
                selected_attempt = total_attempts

            # On charge les messages pour l'essai sélectionné
            raw_messages = await sync_to_async(lambda: list(
                current_chat.messages.filter(attempt_number=selected_attempt,
                                             type__in=['prompt', 'gpt-a', 'gpt-q']).order_by('id')))()

            has_ai = await sync_to_async(lambda: current_chat.messages
                                         .filter(type='gpt-a', attempt_number=selected_attempt)
                                         .exists())()
            has_error = await sync_to_async(lambda: InsightProcessingError.objects
                                            .filter(insight_chat=current_chat)
                                            .exists())()
            in_progress = not (has_ai or has_error)

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
        chatcategories = await sync_to_async(
            lambda: list(InsightChatCategory.objects.filter(is_active=True).order_by('price')))()
        context = {
            'chats': chats,
            'messages': messages,
            'current_chat': current_chat,
            'projects': projects,
            'default_project': default_project,
            'profile': profile,
            'chatcategories': chatcategories,
            'default_chat_category': default_chat_category,
            'selected_attempt': selected_attempt,
            'total_attempts': total_attempts,
            'in_progress': in_progress,
            'access_large_models': await sync_to_async(lambda: profile.current_plan.large_models)(),
            'access_advanced_models': await sync_to_async(lambda: profile.current_plan.advanced_models)(),
        }
        return render(request, 'b_insights/insights_chat.html', context)


@login_required
@require_POST
def update_default_project(request):
    project_id = request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id, user=request.user)
        profile = Profile.objects.get(user=request.user)
        profile.default_insights_project = project
        profile.save()

        # Récupérer la liste des chats du projet
        chats = InsightChat.objects.filter(project=project).order_by('-created_on')
        chats_data = []
        for chat in chats:
            chats_data.append({
                'id': chat.public_id,
                'title': chat.title,
                'important': chat.important,
            })
        print('Insight CHATS :')
        print(chats_data)
        # Prepare chat categories
        chatcategories = InsightChatCategory.objects.all().order_by('price')
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
def update_insights_default_chatcategory(request):
    if request.method == 'POST':
        chatcategory_id = request.POST.get('chatcategory_id')
        print('UPDATING CHAT CAT')
        try:
            print(chatcategory_id)
            chatcategory = InsightChatCategory.objects.get(id=chatcategory_id)
            profile = request.user.profile
            profile.default_insight_chat_category = chatcategory
            profile.save()
            return JsonResponse({'status': 'success'})
        except InsightChatCategory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'ChatCategory does not exist'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



@csrf_exempt
@login_required
def insights_delete_chat(request):
    print('DELETE CHAT')
    if request.method == 'POST':
        chat_id = request.POST.get('chat_id')

        print(chat_id)
        try:
            chat = InsightChat.objects.get(public_id=chat_id, user=request.user)
            chat.delete()
            return JsonResponse({'status': 'success'})
        except InsightChat.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Chat not found.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

"""
async def get_processing_updates(request):
    await asyncio.sleep(5)
    chat_id = request.GET.get('chat_id')
    if chat_id:
        latest_chat = await sync_to_async(lambda: InsightChat.objects.filter(public_id=chat_id, user=request.user).first())()
    else:
        latest_chat = await sync_to_async(
            lambda: InsightChat.objects.filter(user=request.user).order_by('-created_on').first())()
    if not latest_chat:
        return JsonResponse({'messages': []})
    last_id = int(request.GET.get('last_id', 0))
    last_attempt_data = await sync_to_async(
        lambda: InsightChatMessage.objects.filter(chat=latest_chat).aggregate(max_attempt=Max('attempt_number'))
    )()
    last_attempt = last_attempt_data.get('max_attempt') or 1
    messages = await sync_to_async(lambda: list(
        InsightChatMessage.objects
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
        chat = InsightChat.objects.get(public_id=chat_id, user=request.user)
        chat.important = not chat.important
        chat.save()
        return JsonResponse({'status': 'success', 'important': chat.important})
    except InsightChat.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Chat not found.'}, status=404)

"""
async def chat_category_comparison_view(request):
    chatcategories = await sync_to_async(
        lambda: list(InsightChatCategory.objects.filter(is_active=True).order_by('price'))
    )()
    return render(
        request,
        'b_insights/chat_category_comparison.html',
        {'chatcategories': chatcategories}
    )
"""

async def insights_chat_category_comparison_view(request):
    chatcategories = await sync_to_async(
        lambda: list(InsightChatCategory.objects.filter(is_active=True).order_by('price'))
    )()
    return render(
        request,
        'b_insights/chat_category_comparison.html',
        {'chatcategories': chatcategories}
    )


