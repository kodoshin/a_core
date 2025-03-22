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



@login_required
def code_chat_view(request):
    user = request.user
    # Récupérer le profil de l'utilisateur
    profile = Profile.objects.get(user=request.user)

    # Récupérer le projet par défaut du profil
    default_project = profile.default_project
    default_chat_category = profile.default_chat_category
    available_credits = profile.available_credits

    components = Component.objects.filter(file__project=default_project)
    files = File.objects.filter(project=default_project)
    projects = Project.objects.filter(user=user).exclude(technology__name='Other')
    if request.method == 'POST':
        # Handle chat prompts
        if 'prompt' in request.POST:
            prompt = request.POST.get('prompt')
            #processing_step = ProcessingStep.objects.get(short_name = 'u1')
            # Créer ou récupérer le chat en cours
            chat_id = request.POST.get('chat_id')
            if chat_id:
                chat = CodingChat.objects.get(id=chat_id, user=user)
                is_first_prompt = False
            else:
                chat = CodingChat.objects.create(user=user, project=default_project)
                is_first_prompt = True
            if available_credits >= default_chat_category.price:
                # Assez de crédits disponibles
                #credits = True
                # Génerer le titre de la discussion avec l'IA
                #title_prompt = "This is my request : \n" + prompt + "\nI need you to give me a title to hilight this request in less than 25 characters, with no use of any special characters"
                #ai_title_response = get_gpt_output(title_prompt)
                #chat.title = ai_title_response
                chat.title = prompt[:25] + "..." if len(prompt)>=28 else prompt
                chat.save()
                # Obtenir la réponse de l'IA sur le prompt
                ######################################################################### PROCESSING À FAIRE #######################################################################################################
                if default_chat_category.type == 'regular' :
                    ai_response = regular_ai_processing(prompt, components, chat, is_first_prompt)
                elif default_chat_category.type == 'super' :
                    #print('super ai processing')
                    ai_response = super_ai_processing(prompt, files, components, chat, is_first_prompt)
                if is_first_prompt :
                    profile.available_credits = available_credits - default_chat_category.price
                    profile.save()
                else:
                    profile.available_credits = available_credits - default_chat_category.price_secondary_prompt
                    profile.save()
                # Parse the AI response
                steps = parse_steps(ai_response)
            else :
                #credits = False
                processing_steps = {f"{step.order} : {step.name}": step for step in ProcessingStep.objects.all()}
                chat.title = prompt[:25] + "..." if len(prompt)>=28 else prompt
                chat.save()
                CodingChatMessage.objects.create(
                    chat=chat,
                    type='prompt',
                    processing_step=processing_steps.get('1 : user prompt 1'),
                    content=prompt,
                    order=1,
                    api_key=None
                )
                ai_response = "<step1><Justifications>Please come back tomorrow to claim your free credits or buy more credits! </Justifications></step1>"
                steps = parse_steps(ai_response)

                CodingChatMessage.objects.create(
                    chat=chat,
                    type='gpt-a',
                    content=ai_response,
                    order=5,
                    api_key=None,
                    processing_step=processing_steps.get("5 : ai answer 2")
                )
            # Retourner les messages en JSON
            return JsonResponse({
                'user_message': prompt,
                'ai_response':ai_response,
                'ai_message': ai_response,
                'chat_id': chat.id,
                'steps': steps  # Include steps in the JSON response
            })


        # Handle rating updates
        elif 'rate' in request.POST:
            chat_id = request.POST.get('chat_id')
            if chat_id:
                rating_value = int(request.POST.get('rate'))
                chat = CodingChat.objects.get(id=chat_id, user=user)
                chat.rate = rating_value
                chat.save()
                return JsonResponse({'status': 'success', 'rate': chat.rate})


    else:
        # GET request: afficher la page avec les chats précédents
        chats = CodingChat.objects.filter(user=user, project=profile.default_project).order_by('-created_on')
        chat_id = request.GET.get('chat_id')
        if chat_id:
            current_chat = CodingChat.objects.get(id=chat_id, user=user)
            #messages = current_chat.messages.all().order_by('id')
            messages = current_chat.messages.filter(type__in=['prompt', 'gpt-a', 'gpt-q']).order_by('id')
        else:
            current_chat = None
            messages = []
        # Process messages to include parsed steps
        processed_messages = []
        for message in messages:
            if message.type == 'gpt-a':
                steps = parse_steps(message.content)
                processed_messages.append({
                    'type': message.type,
                    'steps': steps
                })
            else:
                processed_messages.append({
                    'type': message.type,
                    'content': message.content
                })
        #try:
        #    count_steps = len(steps)
        #except:
        #    count_steps = 0

        chatcategories = ChatCategory.objects.all()
        context = {
            'chats':chats,
            'components':components,
            'messages':processed_messages,
            #'count_steps':count_steps,
            'default_project':default_project,
            'projects':projects,
            'current_chat':current_chat,
            'profile':profile,
            'chatcategories':chatcategories
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