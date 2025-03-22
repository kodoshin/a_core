import requests
import json
import tiktoken
from b_coding.models import TokenUsage, CodingChatMessage
from a_projects.models import Project, File



def get_gpt_output (content):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer sk-1AnK40d0CI1zIkiAygmvnC2YqyMcoSBisq0v7_OuEBT3BlbkFJnvlA3ukhO5fsl8V924aXeXjKCMLHZfxILOyNBm-jYA",
        "Content-Type": "application/json"
    }
    body = {
        "model": "o3-mini",
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
    model = "o1-mini"
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
        enc = tiktoken.encoding_for_model(model)
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
    model = "o3-mini"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        "reasoning_effort": "high",
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
        enc = tiktoken.encoding_for_model(model)
        tokens_used = len(enc.encode(prompt))
        tokens_used_response = len(enc.encode(ai_answer))
        # Store token usage in the database
        TokenUsage.objects.create(prompt=prompt, tokens_used=tokens_used, coding_chat=chat)
        TokenUsage.objects.create(prompt=ai_answer, tokens_used=tokens_used_response, coding_chat=chat)
        return ai_answer.replace("''", "'").replace("(')","('')")
    else:
        print(f"Request failed with status code {response.status_code}")
        return response.text


