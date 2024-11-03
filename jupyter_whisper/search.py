import requests

def search_online(style, question):
    url = "https://api.perplexity.ai/chat/completions"

    payload = {
    "model": "llama-3.1-sonar-large-128k-online",
    "messages": [
        {
            "role": "system",
            "content": f"{style}"
        },
        {
            "role": "user",
            "content": question
        }
    ],
    "temperature": 0.2,
    "top_p": 0.9,
    "return_citations": True,
    "search_domain_filter": ["perplexity.ai"],
    "return_images": False,
    "return_related_questions": False,
    "search_recency_filter": "month",
    "top_k": 0,
    "stream": False,
    "presence_penalty": 0,
        "frequency_penalty": 1
    }
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers).json().get("choices", [{}])[0].get("message", {}).get("content")
    # Create new markdown cell below with the response
    a = get_ipython()
    a.set_next_input(response, replace=False)
    return response
