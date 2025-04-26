from management.ai_bases import async_get_response_ai_1, async_get_response_ai_2 #get_response_ai_1, get_response_ai_2
from .prompts_variables import pe_files_xml, pe_components_xml, pe_final_answer, pe_final_answer_format, none_answer, no_components_answer
from .models import CodingChatMessage, ProcessingStep, ChatCategory
import xml.etree.ElementTree as ET
import re
from django.db.models import Max

from asgiref.sync import sync_to_async



def generate_files_xml(files):
    root = ET.Element("files")

    for file in files:
        file_element = ET.SubElement(root, "file")

        file_element = ET.SubElement(file_element, "file")
        file_element.text = file.path

        content_element = ET.SubElement(file_element, "content")
        content_element.text = file.content

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def generate_components_xml(components):
    root = ET.Element("components")

    for component in components:
        component_element = ET.SubElement(root, "component")

        file_element = ET.SubElement(component_element, "file")
        file_element.text = component.file.path

        name_element = ET.SubElement(component_element, "name")
        name_element.text = component.name

        content_element = ET.SubElement(component_element, "content")
        content_element.text = component.content

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def generate_components_xml(components):
    root = ET.Element("components")

    for component in components:
        component_element = ET.SubElement(root, "component")

        file_element = ET.SubElement(component_element, "file")
        file_element.text = component.file.path

        name_element = ET.SubElement(component_element, "name")
        name_element.text = component.name

        content_element = ET.SubElement(component_element, "content")
        content_element.text = component.content

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


def filter_files_from_xml(xml_string, files):
    print(xml_string)
    root = ET.fromstring(xml_string)
    filtered_files = []
    for file_element in root.findall("file"):
        file_path = file_element.text
        #print(file_path)
        # Filtrer le fichier  qui ont le même fichier et le même nom
        matching_file = next((f for f in files if f.path == file_path), None)
        #print('MATCHING FILE !!!!!!!!')
        #print(matching_file)
        filtered_files.append(matching_file)

    return filtered_files


async def filter_components_from_xml(xml_string, components):
    print(xml_string)
    root = ET.fromstring(xml_string)
    filtered_components = []

    for component_element in root.findall("component"):
        file_path = component_element.find("file").text
        name = component_element.find("name").text

        # Filtrer les composants qui ont le même fichier et le même nom
        #matching_components = components.filter(file__path=file_path, name=name)
        matching_components = await sync_to_async(list)(components.filter(file__path=file_path, name=name))
        filtered_components.extend(matching_components)
    print('Related components!!!!!!!!')
    #print(filtered_components)
    return filtered_components


def generate_components_string(components):
    component_strings = []
    for component in components:
        component_strings.append(f"{component.file.path}")  # ou component.file.name si pertinent
        component_strings.append(f"{component.name}")
        component_strings.append(f"{component.content}")

    return "\n".join(component_strings)  # Séparation par des retours à la ligne


async def ai_processing(prompt, files, components, chat, is_first_prompt):
    chat_category = await sync_to_async(ChatCategory.objects.get)(type='super')
    processing_steps = await sync_to_async(lambda: {f'{chat_category} : {step.order}': step
                                                    for step in
                                                    ProcessingStep.objects.filter(chat_category=chat_category)})()

    if is_first_prompt:
        await sync_to_async(save_prompt)(chat, prompt, chat_category, processing_steps)
        engineered_prompt_0 = await build_engineered_prompt_0(pe_files_xml, files, prompt, chat, chat_category, processing_steps)
        relevant_files = await get_related_files(engineered_prompt_0, files, chat, chat_category, processing_steps)
        #print('Relevant files !!!!!!!!!!1')
        #print(relevant_files[0])
        files_to_use = relevant_files or []
        relevant_files_components = await sync_to_async(lambda: components.filter(file__in=files_to_use))()
        engineered_prompt_1 = await build_engineered_prompt_1(pe_components_xml, relevant_files_components, prompt, chat, chat_category, processing_steps)
        print("EP1 !!!!!!!!!!!!!!!!!!!")
        #print(engineered_prompt_1)
        ai_answer_1 = await async_get_response_ai_1(engineered_prompt_1, chat)
        match = re.search(r'<components>[\s\S]*?</components>', ai_answer_1)
        if match:
            related_components_xml = match.group(0)
            print('Related components xml !!!!!!!')
            #print(related_components_xml)
            related_components = await filter_components_from_xml(related_components_xml, components)

        else:
            related_components = []
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat, type='ai', content=ai_answer_1, order=3, api_key=None,
            processing_step=processing_steps.get(f'{chat_category} : 3')
        )
        engineered_prompt_2 = await build_engineered_prompt_2(pe_final_answer, pe_final_answer_format, related_components, prompt, chat, chat_category, processing_steps)
        print('EP2 !!!!!!!!!!!!!')
        #print(engineered_prompt_2)
        ai_answer_2 = await async_get_response_ai_2(engineered_prompt_2, chat)
        print('AI ANSWER 2!!!!!!')
        #print(ai_answer_2)
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat, type='gpt-a', content=ai_answer_2, order=5, api_key=None,
            processing_step=processing_steps.get(f'{chat_category} : 7')
        )
        return ai_answer_2
    else:
        await sync_to_async(save_prompt)(chat, prompt, chat_category, processing_steps)
        last_prompt_obj = await sync_to_async(lambda: CodingChatMessage.objects.filter(chat=chat, type='r-prompt').last())()
        last_engineered_prompt = last_prompt_obj.content.replace(pe_final_answer_format, '')
        last_ai_answer_obj = await sync_to_async(lambda: CodingChatMessage.objects.filter(chat=chat, type='gpt-a').last())()
        last_ai_answer = last_ai_answer_obj.content
        engineered_adjustment_prompt = await build_engineered_adjustment_prompt(chat, last_engineered_prompt, last_ai_answer,prompt, chat_category, processing_steps)
        ai_adjustment_answer = await async_get_response_ai_2(engineered_adjustment_prompt, chat)
        max_order = await sync_to_async(lambda: CodingChatMessage.objects.filter(chat=chat).aggregate(Max('order'))['order__max'])()
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat, type='gpt-a', content=ai_adjustment_answer, order=max_order + 1, api_key=None,
            processing_step=processing_steps.get(f'{chat_category} : 7')
        )
        return ai_adjustment_answer


def save_prompt(chat, prompt, chat_category_id, processing_steps):
    chat.prompts_count = chat.prompts_count + 1
    chat.chat_category = chat_category_id
    max_order = CodingChatMessage.objects.filter(chat=chat).aggregate(Max('order'))['order__max'] or 0
    chat.save()
    # Enregistrer le message utilisateur
    CodingChatMessage.objects.create(
        chat=chat,
        type='prompt',
        processing_step=processing_steps.get(f"{chat_category_id} : 1"),
        content=prompt,
        order=max_order+1,
        api_key=None
    )


async def build_engineered_prompt_0(pe_files_xml, files, prompt, chat, chat_category_id, processing_steps):
    #components_str = generate_files_xml(files)
    #print('BUILDING EP0!!!!!!!!!!!!!!!!!')
    components_str = await sync_to_async(generate_files_xml)(files)
    final_prompt = pe_files_xml + '\nFiles:\n' + components_str + '\nRequest:\n' + prompt
    await sync_to_async(CodingChatMessage.objects.create)(
        chat=chat,
        type='r-prompt',
        content=final_prompt,
        order=2,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 2")
    )
    return final_prompt


async def get_related_files(engineered_prompt_0, files, chat, chat_category_id, processing_steps):
    #print('Engineered Prompt 0 !!!!!!!!!!')
    #print(engineered_prompt_0)
    try:
        ai_response = await async_get_response_ai_1(engineered_prompt_0, chat)
        match = re.search(r"<files>[\s\S]*?</files>", ai_response)
        if match :
            related_files_xml = match.group(0)  # Extraction de la chaîne XML
            #print(related_files_xml)
            print('getting files from XML')
            related_files = filter_files_from_xml(related_files_xml, files)
        else:
            related_files = []
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat,
            type='ai',
            content=ai_response,
            order=3,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 3")
        )
    except:
        related_files = None
    return related_files

async def build_engineered_prompt_1(components_xml, relevant_files_components, prompt, chat, chat_category_id, processing_steps):
    components_str = await sync_to_async(generate_components_xml)(relevant_files_components)
    final_prompt = components_xml + '\nComponents:\n' + components_str + '\nRequest:\n' + prompt
    await sync_to_async(CodingChatMessage.objects.create)(
        chat=chat,
        type='r-prompt',
        content=final_prompt,
        order=2,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 4")
    )
    return final_prompt


async def get_related_components(engineered_prompt_1, components, chat, chat_category_id, processing_steps):
    try:
        ai_response = await async_get_response_ai_1(engineered_prompt_1, chat)
        match = re.search(r"<components>[\s\S]*?</components>", ai_response)
        if match:
            related_components_xml = match.group(0)  # Extraction de la chaîne XML
            print('Related components XML !!!!!!!!!!!!')
            #print(related_components_xml)
            related_components = await filter_components_from_xml(related_components_xml, components)
            print('related components 2 !!!!!!!!!')
            #print(related_components)
        else:
            related_components = []
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat,
            type='ai',
            content=ai_response,
            order=3,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 5")
        )
    except:
        related_components = None
    return related_components


async def build_engineered_prompt_2 (pe_final_answer, pe_final_answer_format, related_components, prompt, chat, chat_category_id, processing_steps):
    print('Related components 2 !!!!!!!!')
    if related_components is None:
        return "None"
    elif related_components==[]:
        return "No components"
    else:
        related_components_str = await sync_to_async(generate_components_string)(related_components)
        final_prompt = pe_final_answer + '\nResources:\n' + related_components_str + '\nRequest:\n' + prompt +  '\nFinal answer format instructions:\n' + pe_final_answer_format
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat,
            type='r-prompt',
            content=final_prompt,
            order=4,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 6")
        )
        return final_prompt


async def get_final_solution(engineered_prompt_2, chat, chat_category_id, processing_steps):
    if engineered_prompt_2 == "None":
        CodingChatMessage.objects.create(
            chat=chat,
            type='gpt-a',
            content=none_answer,
            status='none',
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 7")
        )
        return none_answer
    elif engineered_prompt_2 == "No components":
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat,
            type='gpt-a',
            content=no_components_answer,
            status='no-components',
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 7")
        )
        return no_components_answer
    else:
        ai_response = await async_get_response_ai_2(engineered_prompt_2, chat)
        await sync_to_async(CodingChatMessage.objects.create)(
            chat=chat,
            type='gpt-a',
            content=ai_response,
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 7")
        )
        return ai_response


async def build_engineered_adjustment_prompt(chat, last_engineered_prompt, last_ai_answer, prompt, chat_category_id, processing_steps):
    # This is my initial prompt + ep_2 + This is your solution + ai_answer_2 + this is my next prompt to adjust the solution + prompt + formatting variable
    engineered_adjustment_prompt = "This is my initial prompt: \n\n" + last_engineered_prompt + "\n\nThis was your solution: \n\n" + last_ai_answer + "\n\nthis is my next prompt to adjust the solution: \n\n" + prompt + "\n\n" + pe_final_answer_format
    max_order = await sync_to_async(
        lambda: CodingChatMessage.objects.filter(chat=chat)
        .aggregate(Max('order'))['order__max']
    )()
    await sync_to_async(CodingChatMessage.objects.create)(
        chat=chat,
        type='r-prompt',
        content=engineered_adjustment_prompt,
        order=max_order+1,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 6")
    )

    return engineered_adjustment_prompt

async def get_adjusted_solution(chat, engineered_adjustment_prompt, chat_category_id, processing_steps):
    # appel à l'API IA
    ai_response = await async_get_response_ai_2(engineered_adjustment_prompt, chat)
    max_order = await sync_to_async(
        lambda: CodingChatMessage.objects.filter(chat=chat)
        .aggregate(Max('order'))['order__max']
    )()
    await sync_to_async(CodingChatMessage.objects.create)(
        chat=chat,
        type='gpt-a',
        content=ai_response,
        order=max_order+1,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 7")
    )
    return ai_response
