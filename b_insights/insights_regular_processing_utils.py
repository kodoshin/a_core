from management.ai_bases import async_get_response_ai_1, async_get_response_ai_2 #get_response_ai_1, get_response_ai_2
from .insights_prompts_variables import pe_components_xml, pe_final_answer, pe_final_answer_format, none_answer, no_components_answer
from .models import InsightChatMessage, InsightProcessingStep, InsightChatCategory
import xml.etree.ElementTree as ET
import re
from django.db.models import Max

from asgiref.sync import sync_to_async


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


async def filter_components_from_xml(xml_string, components):
    root = ET.fromstring(xml_string)
    filtered_components = []

    for component_element in root.findall("component"):
        file_path = component_element.find("file").text
        name = component_element.find("name").text

        # Filtrer les composants qui ont le même fichier et le même nom
        matching_components = await sync_to_async(list)(components.filter(file__path=file_path, name=name))
        filtered_components.extend(matching_components)

    return filtered_components


def generate_components_string(components):
    component_strings = []
    for component in components:
        component_strings.append(f"{component.file.path}")  # ou component.file.name si pertinent
        component_strings.append(f"{component.name}")
        component_strings.append(f"{component.content}")

    return "\n".join(component_strings)  # Séparation par des retours à la ligne


async def ai_processing(prompt, components, chat, is_first_prompt, technology, attempt):
    technology_name = await sync_to_async(lambda: technology.name)()
    technology_format_example = await sync_to_async(lambda: technology.prompt_example)()
    chat_category = await sync_to_async(InsightChatCategory.objects.get)(type='navigator')
    processing_steps = await sync_to_async(lambda: {f'{chat_category} : {step.order}': step
                                                    for step in
                                                    InsightProcessingStep.objects.filter(chat_category=chat_category)})()

    if is_first_prompt:
        await save_prompt(chat, prompt, chat_category, processing_steps, attempt)
        engineered_prompt_1 = await build_engineered_prompt_1(pe_components_xml.format(technology=technology_name), components, prompt, chat, chat_category,processing_steps, attempt)
        ai_answer_1 = await async_get_response_ai_1(engineered_prompt_1, chat)
        match = re.search(r'<components>[\s\S]*?</components>', ai_answer_1)
        if match:
            related_components_xml = match.group(0)
            related_components = await filter_components_from_xml(related_components_xml, components)
        else:
            related_components = []
        await sync_to_async(InsightChatMessage.objects.create)(
            chat=chat, type='ai', content=ai_answer_1, order=3, api_key=None,
            processing_step=processing_steps.get(f'{chat_category} : 3')
        )
        engineered_prompt_2 = await build_engineered_prompt_2(pe_final_answer.format(technology=technology_name), pe_final_answer_format.replace("{technology}", technology_name).replace('{code_example}',technology_format_example), related_components, prompt, chat, chat_category, processing_steps, attempt)
        ai_answer_2 = await async_get_response_ai_2(engineered_prompt_2, chat)
        ai_answer_2 = ai_answer_2.replace("&gt;", ">").replace("&lt;", "<")
        await sync_to_async(InsightChatMessage.objects.create)(
            chat=chat, type='gpt-a', content=ai_answer_2, order=5, api_key=None,
            processing_step=processing_steps.get(f'{chat_category} : 5'), attempt_number=attempt
        )
        return ai_answer_2
    else:
        await save_prompt(chat, prompt, chat_category, processing_steps, attempt)
        last_prompt_obj = await sync_to_async(lambda: InsightChatMessage.objects.filter(chat=chat, type='r-prompt').last())()
        last_engineered_prompt = last_prompt_obj.content.replace(pe_final_answer_format.replace("{technology}", technology_name).replace('{code_example}',technology_format_example), '')
        last_ai_answer_obj = await sync_to_async(lambda: InsightChatMessage.objects.filter(chat=chat, type='gpt-a').last())()
        last_ai_answer = last_ai_answer_obj.content
        engineered_adjustment_prompt = await build_engineered_adjustment_prompt(chat, last_engineered_prompt, last_ai_answer, prompt, chat_category, processing_steps, attempt)
        ai_adjustment_answer = await async_get_response_ai_2(engineered_adjustment_prompt, chat)
        ai_adjustment_answer = ai_adjustment_answer.replace("&gt;", ">").replace("&lt;", "<")
        max_order = await sync_to_async(lambda: InsightChatMessage.objects.filter(chat=chat).aggregate(Max('order'))['order__max'])()
        await sync_to_async(InsightChatMessage.objects.create)(
            chat=chat, type='gpt-a', content=ai_adjustment_answer, order=max_order + 1, api_key=None,
            processing_step=processing_steps.get(f'{chat_category} : 7'), attempt_number=attempt
        )
        return ai_adjustment_answer

async def save_prompt(chat, prompt, chat_category_id, processing_steps, attempt_number):
    chat.prompts_count = chat.prompts_count + 1
    chat.chat_category = chat_category_id
    max_order = await sync_to_async(lambda: InsightChatMessage.objects.filter(chat=chat).aggregate(Max('order'))['order__max'])() or 0
    await sync_to_async(chat.save, thread_sensitive=True)()
    # Enregistrer le message utilisateur
    await sync_to_async(InsightChatMessage.objects.create)(
        chat=chat,
        type='prompt',
        processing_step=processing_steps.get(f"{chat_category_id} : 1"),
        content=prompt,
        order=max_order+1,
        api_key=None,
        attempt_number=attempt_number
    )


async def build_engineered_prompt_1(components_xml, components, prompt, chat, chat_category_id, processing_steps, attempt):
    components_str = await sync_to_async(generate_components_xml)(components)
    final_prompt = components_xml + '\nComponents:\n' + components_str + '\nRequest:\n' + prompt
    await sync_to_async(InsightChatMessage.objects.create)(
        chat=chat,
        type='r-prompt',
        content=final_prompt,
        order=2,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 2"),
        attempt_number=attempt
    )
    return final_prompt


async def get_related_components(engineered_prompt_1, components, chat, chat_category_id, processing_steps, attempt):
    try:
        ai_response = await async_get_response_ai_1(engineered_prompt_1, chat)
        match = re.search(r"<components>[\s\S]*?</components>", ai_response)
        if match:
            related_components_xml = match.group(0)  # Extraction de la chaîne XML
            print(related_components_xml)
            related_components = filter_components_from_xml(related_components_xml, components)
        else:
            related_components = []
        InsightChatMessage.objects.create(
            chat=chat,
            type='ai',
            content=ai_response,
            order=3,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 3"),
            attempt_number=attempt
        )
    except:
        related_components = None
    return related_components


async def build_engineered_prompt_2 (pe_final_answer, pe_final_answer_format, related_components, prompt, chat, chat_category_id, processing_steps, attempt):
    if related_components is None:
        return "None"
    elif related_components==[]:
        return "No components"
    else:
        related_components_str = await sync_to_async(generate_components_string)(related_components)
        final_prompt = pe_final_answer + '\nResources:\n' + related_components_str + '\nRequest:\n' + prompt +  '\nFinal answer format instructions:\n' + pe_final_answer_format
        await sync_to_async(InsightChatMessage.objects.create)(
            chat=chat,
            type='r-prompt',
            content=final_prompt,
            order=4,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 4"),
            attempt_number=attempt
        )
        return final_prompt


async def get_final_solution(engineered_prompt_2, chat, chat_category_id, processing_steps, attempt):
    if engineered_prompt_2 == "None":
        InsightChatMessage.objects.create(
            chat=chat,
            type='gpt-a',
            content=none_answer,
            status='none',
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 5"),
            attempt_number=attempt
        )
        return none_answer
    elif engineered_prompt_2 == "No components":
        InsightChatMessage.objects.create(
            chat=chat,
            type='gpt-a',
            content=no_components_answer,
            status='no-components',
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 5"),
            attempt_number=attempt
        )
        return no_components_answer
    else:
        ai_response = await async_get_response_ai_2(engineered_prompt_2, chat)
        ai_response = ai_response.replace("&gt;", ">").replace("&lt;", "<")
        InsightChatMessage.objects.create(
            chat=chat,
            type='gpt-a',
            content=ai_response,
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 5"),
            attempt_number=attempt
        )
        return ai_response


async def build_engineered_adjustment_prompt(chat, last_engineered_prompt, last_ai_answer, prompt, chat_category_id, processing_steps, attempt):
    # This is my initial prompt + ep_2 + This is your solution + ai_answer_2 + this is my next prompt to adjust the solution + prompt + formatting variable
    engineered_adjustment_prompt = "This is my initial prompt: \n\n" + last_engineered_prompt + "\n\nThis was your solution:\n\n" + last_ai_answer + "\n\nthis is my next prompt to adjust the solution:\n\n" + prompt + "\n\n" + pe_final_answer_format
    max_order = await sync_to_async(
        lambda: InsightChatMessage.objects.filter(chat=chat)
        .aggregate(Max('order'))['order__max']
    )()
    await sync_to_async(InsightChatMessage.objects.create)(
        chat=chat,
        type='r-prompt',
        content=engineered_adjustment_prompt,
        order=max_order+1,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 6"),
        attempt_number=attempt
    )

    return engineered_adjustment_prompt

async def get_adjusted_solution(chat, engineered_adjustment_prompt, chat_category_id, processing_steps, attempt):
    # appel à l'API IA
    ai_response = await async_get_response_ai_2(engineered_adjustment_prompt, chat).replace("</text>\n<text>","\n")
    ai_response = ai_response.replace("&gt;", ">").replace("&lt;", "<")
    max_order = await sync_to_async(
        lambda: InsightChatMessage.objects.filter(chat=chat)
        .aggregate(Max('order'))['order__max']
    )()
    await sync_to_async(InsightChatMessage.objects.create)(
        chat=chat,
        type='gpt-a',
        content=ai_response,
        order=max_order+1,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 7"),
        attempt_number=attempt
    )
    return ai_response



