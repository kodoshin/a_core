import requests
import json
import tiktoken
from b_coding.models import TokenUsage, CodingChatMessage
from a_projects.models import Project, File

import httpx
from asgiref.sync import sync_to_async
from .utils import get_api_key, release_api_key




def get_gpt_output (content):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer sk-1AnK40d0CI1zIkiAygmvnC2YqyMcoSBisq0v7_OuEBT3BlbkFJnvlA3ukhO5fsl8V924aXeXjKCMLHZfxILOyNBm-jYA",
        "Content-Type": "application/json"
    }
    body = {
        "model": "o4-mini",
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))
    if response.status_code == 200:
        output = response.json()
        # print(json.dumps(output, indent=4))
        return output['choices'][0]['message']['content'].replace("'", "''")
    else:
        print(f"Request failed with status code {response.status_code}")
        return response.text


#get_openai_response_ai_1 est pour retourner les components au bon format
def get_response_ai_1(prompt, chat):
    model = "o4-mini"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        #"temperature": 0.4,
        "messages": [
            {
                "role": "user",
                "content": prompt

            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        output = response.json()
        ai_answer = output['choices'][0]['message']['content']
        enc = tiktoken.get_encoding("cl100k_base")
        tokens_used = len(enc.encode(prompt))
        tokens_used_response = len(enc.encode(ai_answer))
        # Store token usage in the database
        TokenUsage.objects.create(prompt=prompt, tokens_used=tokens_used, coding_chat=chat)
        TokenUsage.objects.create(prompt=ai_answer, tokens_used=tokens_used_response, coding_chat=chat)
        return ai_answer.replace("''", "'").replace("(')","('')")
    else:
        print(f"Request failed with status code {response.status_code}")
        return response.text


def get_response_ai_2(prompt, chat):
    model = "o4-mini"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        #"reasoning_effort": "high",
        "messages": [
            {
                "role": "user",
                "content": prompt

            }
        ]

    }
    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        output = response.json()
        ai_answer = output['choices'][0]['message']['content']
        enc = tiktoken.get_encoding("cl100k_base")
        tokens_used = len(enc.encode(prompt))
        tokens_used_response = len(enc.encode(ai_answer))
        # Store token usage in the database
        TokenUsage.objects.create(prompt=prompt, tokens_used=tokens_used, coding_chat=chat)
        TokenUsage.objects.create(prompt=ai_answer, tokens_used=tokens_used_response, coding_chat=chat)
        return ai_answer.replace("''", "'").replace("(')","('')")
    else:
        print(f"Request failed with status code {response.status_code}")
        return response.text


async def async_get_gpt_output(content):
    key = await sync_to_async(get_api_key)('chat')
    if not key:
        raise RuntimeError('No active API Key available for chat')
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {key.api_key}',
            'Content-Type': 'application/json'
        }
        body = {
            'model': await sync_to_async(lambda k: k.ai_model.name)(key),
            'messages': [{'role': 'user', 'content': content}]
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=body)
        if response.status_code == 200:
            output = response.json()
            return output['choices'][0]['message']['content'].replace("'", "'")
        return response.text
    finally:
        await sync_to_async(release_api_key)(key)

async def async_get_response_ai_1(prompt, chat):
    key = await sync_to_async(get_api_key)('chat')
    if not key:
        raise RuntimeError('No active API Key available for chat')
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {key.api_key}',
            'Content-Type': 'application/json'
        }
        body = {
            'model': await sync_to_async(lambda k: k.ai_model.name)(key),
            'reasoning_effort': 'high',
            'messages': [{'role': 'user', 'content': prompt}]
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=body)
        if response.status_code == 200:
            output = response.json()
            ai_answer = output['choices'][0]['message']['content']
            enc = tiktoken.get_encoding('cl100k_base')
            tokens_used = len(enc.encode(prompt))
            tokens_used_response = len(enc.encode(ai_answer))
            await sync_to_async(TokenUsage.objects.create)(
                prompt=prompt, tokens_used=tokens_used, coding_chat=chat
            )
            await sync_to_async(TokenUsage.objects.create)(
                prompt=ai_answer, tokens_used=tokens_used_response, coding_chat=chat
            )
            return ai_answer.replace("'", "'").replace("('')", "('')")
        return response.text
    finally:
        await sync_to_async(release_api_key)(key)

async def async_get_response_ai_2(prompt, chat):
    key = await sync_to_async(get_api_key)('chat')
    if not key:
        raise RuntimeError('No active API Key available for chat')
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {key.api_key}',
            'Content-Type': 'application/json'
        }
        body = {
            'model': await sync_to_async(lambda k: k.ai_model.name)(key),
            'reasoning_effort': 'high',
            'messages': [{'role': 'user', 'content': prompt}]
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=body)
        if response.status_code == 200:
            output = response.json()
            ai_answer = output['choices'][0]['message']['content']
            enc = tiktoken.get_encoding('cl100k_base')
            tokens_used = len(enc.encode(prompt))
            tokens_used_response = len(enc.encode(ai_answer))
            await sync_to_async(TokenUsage.objects.create)(
                prompt=prompt, tokens_used=tokens_used, coding_chat=chat
            )
            await sync_to_async(TokenUsage.objects.create)(
                prompt=ai_answer, tokens_used=tokens_used_response, coding_chat=chat
            )
            return ai_answer.replace("'", "'").replace("('')", "('')")
        return response.text
    finally:
        await sync_to_async(release_api_key)(key)

async def async_get_ai_title(content):
    key = await sync_to_async(get_api_key)('title')
    if not key:
        raise RuntimeError('No active API Key available for documentation')
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {key.api_key}',
            'Content-Type': 'application/json'
        }
        body = {
            'model': await sync_to_async(lambda k: k.ai_model.name)(key),
            'messages': [
                {'role': 'user', 'content': f"Generate a concise title for the following text:\n\n{content}, absolute maximum is 25 characters, not more than 25 characters, no special annotation in the beginning or the end"}
            ]
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=body)
        if response.status_code == 200:
            output = response.json()
            return output['choices'][0]['message']['content'].strip()
        return response.text
    finally:
        await sync_to_async(release_api_key)(key)
