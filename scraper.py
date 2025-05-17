import http.client
import json
import os
import urllib.parse
import urllib.request

from dotenv import load_dotenv
load_dotenv(override=True)

def scraper(company_name):
    base_url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {
        "api_key": os.environ["TAVILY_API_KEY"],
        "query": f'{company_name} czech republic',
        "search_depth": "advanced",
        "include_images": False,
        "include_answer": False,
        "include_raw_content": False,
        "max_results": 100,
        "exclude_domains": [],
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base_url, data=data, headers=headers)  # nosec: B310 fixed url we want to open

    response = urllib.request.urlopen(request)  # nosec: B310 fixed url we want to open
    response_data: str = response.read().decode("utf-8")

    json_response = json.loads(response_data)

    return json_response

