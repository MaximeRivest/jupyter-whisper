import requests
from .config import get_config_manager

def search_online(style, question):
    config = get_config_manager()
    api_key = config.get_api_key('PERPLEXITY_API_KEY')
    
    if not api_key:
        raise ValueError("Perplexity API key not found. Please run setup_jupyter_whisper() to configure.")

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
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    response.raise_for_status()  # Raise exception for bad status codes
    return response.json().get("choices", [{}])[0].get("message", {}).get("content")
