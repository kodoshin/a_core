from management.ai_bases import get_response_ai_1, get_response_ai_2
from .prompts_variables import pe_components_xml, pe_final_answer, pe_final_answer_format, none_answer, no_components_answer
from .models import CodingChatMessage, ProcessingStep, ChatCategory
import xml.etree.ElementTree as ET
import re
from django.db.models import Max



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


def filter_components_from_xml(xml_string, components):
    root = ET.fromstring(xml_string)
    filtered_components = []

    for component_element in root.findall("component"):
        file_path = component_element.find("file").text
        name = component_element.find("name").text

        # Filtrer les composants qui ont le même fichier et le même nom
        matching_components = components.filter(file__path=file_path, name=name)
        filtered_components.extend(matching_components)

    return filtered_components


def generate_components_string(components):
    component_strings = []
    for component in components:
        component_strings.append(f"{component.file.path}")  # ou component.file.name si pertinent
        component_strings.append(f"{component.name}")
        component_strings.append(f"{component.content}")

    return "\n".join(component_strings)  # Séparation par des retours à la ligne


def ai_processing(prompt, components, chat, is_first_prompt):
    chat_category_id = ChatCategory.objects.get(type='regular')
    processing_steps = {f"{chat_category_id} : {step.order}": step for step in ProcessingStep.objects.filter(chat_category=chat_category_id)}
    if is_first_prompt:
        save_prompt(chat, prompt, chat_category_id, processing_steps)
        engineered_prompt_1 = build_engineered_prompt_1(pe_components_xml, components, prompt, chat, chat_category_id, processing_steps)
        ai_answer_1 = get_related_components(engineered_prompt_1, components, chat, chat_category_id, processing_steps)  #returns related components in XML or JSON format
        engineered_prompt_2 = build_engineered_prompt_2(pe_final_answer, pe_final_answer_format, ai_answer_1, prompt, chat, chat_category_id, processing_steps) #ai_answer_1 est les related_components string
        ai_answer_2 = get_final_solution(engineered_prompt_2, chat, chat_category_id, processing_steps)
        return ai_answer_2
    else:
        save_prompt(chat, prompt, chat_category_id, processing_steps)
        last_engineered_prompt = CodingChatMessage.objects.filter(chat=chat, type='r-prompt').last().content.replace(pe_final_answer_format,"")
        print("LAST EP")
        print(last_engineered_prompt)
        last_ai_answer = CodingChatMessage.objects.filter(chat=chat, type='gpt-a').last().content
        print("LAST AI ANSWER")
        print(last_ai_answer)
        engineered_adjustment_prompt = build_engineered_adjustment_prompt(chat, last_engineered_prompt, last_ai_answer, prompt, chat_category_id, processing_steps)
        print(engineered_adjustment_prompt)
        ai_adjustment_answer = get_adjusted_solution(chat, engineered_adjustment_prompt, chat_category_id, processing_steps)
        print(ai_adjustment_answer)
        return ai_adjustment_answer

def save_prompt(chat, prompt, chat_category_id, processing_steps):
    chat.prompts_count = chat.prompts_count + 1
    chat.chat_category = chat_category_id
    chat.save()
    max_order = CodingChatMessage.objects.filter(chat=chat).aggregate(Max('order'))['order__max'] or 0
    # Enregistrer le message utilisateur
    CodingChatMessage.objects.create(
        chat=chat,
        type='prompt',
        processing_step=processing_steps.get(f"{chat_category_id} : 1"),
        content=prompt,
        order=max_order+1,
        api_key=None
    )


def build_engineered_prompt_1(components_xml, components, prompt, chat, chat_category_id, processing_steps):
    components_str = generate_components_xml(components)
    final_prompt = components_xml + '\nComponents:\n' + components_str + '\nRequest:\n' + prompt
    CodingChatMessage.objects.create(
        chat=chat,
        type='r-prompt',
        content=final_prompt,
        order=2,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 2")
    )
    return final_prompt


def get_related_components(engineered_prompt_1, components, chat, chat_category_id, processing_steps):
    try:
        ai_response = get_response_ai_1(engineered_prompt_1, chat)
        match = re.search(r"<components>[\s\S]*?</components>", ai_response)
        if match:
            related_components_xml = match.group(0)  # Extraction de la chaîne XML
            print(related_components_xml)
            related_components = filter_components_from_xml(related_components_xml, components)
        else:
            related_components = []
        CodingChatMessage.objects.create(
            chat=chat,
            type='ai',
            content=ai_response,
            order=3,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 3")
        )
    except:
        related_components = None
    return related_components


def build_engineered_prompt_2 (pe_final_answer, pe_final_answer_format, related_components, prompt, chat, chat_category_id, processing_steps):
    if related_components is None:
        return "None"
    elif related_components==[]:
        return "No components"
    else:
        related_components_str = generate_components_string(related_components)
        final_prompt = pe_final_answer + '\nResources:\n' + related_components_str + '\nRequest:\n' + prompt +  '\nFinal answer format instructions:\n' + pe_final_answer_format
        CodingChatMessage.objects.create(
            chat=chat,
            type='r-prompt',
            content=final_prompt,
            order=4,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 4")
        )
        return final_prompt


def get_final_solution(engineered_prompt_2, chat, chat_category_id, processing_steps):
    if engineered_prompt_2 == "None":
        CodingChatMessage.objects.create(
            chat=chat,
            type='gpt-a',
            content=none_answer,
            status='none',
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 5")
        )
        return none_answer
    elif engineered_prompt_2 == "No components":
        CodingChatMessage.objects.create(
            chat=chat,
            type='gpt-a',
            content=no_components_answer,
            status='no-components',
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 5")
        )
        return no_components_answer
    else:
        ai_response = get_response_ai_2(engineered_prompt_2, chat)
        CodingChatMessage.objects.create(
            chat=chat,
            type='gpt-a',
            content=ai_response,
            order=5,
            api_key=None,
            processing_step=processing_steps.get(f"{chat_category_id} : 5")
        )
        return ai_response


def build_engineered_adjustment_prompt(chat, last_engineered_prompt, last_ai_answer, prompt, chat_category_id, processing_steps):
    # This is my initial prompt + ep_2 + This is your solution + ai_answer_2 + this is my next prompt to adjust the solution + prompt + formatting variable
    engineered_adjustment_prompt = "This is my initial prompt: \n\n" + last_engineered_prompt + "\n\nThis was your solution:\n\n" + last_ai_answer + "\n\nthis is my next prompt to adjust the solution:\n\n" + prompt + "\n\n" + pe_final_answer_format
    max_order = CodingChatMessage.objects.filter(chat=chat).aggregate(Max('order'))['order__max']
    CodingChatMessage.objects.create(
        chat=chat,
        type='r-prompt',
        content=engineered_adjustment_prompt,
        order=max_order+1,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 6")
    )

    return engineered_adjustment_prompt

def get_adjusted_solution(chat, engineered_adjustment_prompt, chat_category_id, processing_steps):
    # appel à l'API IA
    ai_response = get_response_ai_2(engineered_adjustment_prompt, chat)
    max_order = CodingChatMessage.objects.filter(chat=chat).aggregate(Max('order'))['order__max']
    CodingChatMessage.objects.create(
        chat=chat,
        type='gpt-a',
        content=ai_response,
        order=max_order+1,
        api_key=None,
        processing_step=processing_steps.get(f"{chat_category_id} : 7")
    )
    return ai_response



