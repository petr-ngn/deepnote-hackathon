import streamlit as st
import boto3
import uuid
from botocore.exceptions import NoCredentialsError, ClientError
import os
from dotenv import load_dotenv
import time
from concurrent.futures import ThreadPoolExecutor
import random
import json  # added import for json handling
import base64
from datetime import datetime
from scraper import scraper
import functools
load_dotenv(override=True)
def exponential_backoff(max_retries=5, base_delay=1, max_delay=60):
    """
    Decorator to retry a function with exponential backoff on specific exceptions.

    :param max_retries: Maximum number of retries before giving up.
    :param base_delay: Initial delay in seconds.
    :param max_delay: Maximum delay between retries.
    :param exceptions: Tuple of exception classes to catch.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt >= max_retries:
                        raise
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    jitter = random.uniform(0, 0.5 * delay)  # Optional: add jitter to reduce collisions
                    total_delay = delay + jitter
                    print(f"Caught {e.__class__.__name__}: Retrying in {total_delay:.2f} seconds (attempt {attempt + 1})")
                    time.sleep(total_delay)
                    attempt += 1
        return wrapper
    return decorator
# ─── AWS Clients ─────────────────────────────────────────────────────────────
BUCKET_NAME = "bucket-dabada"

# S3 and Textract clients
s3 = boto3.client('s3',
                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                  region_name=os.getenv('AWS_REGION'))

textract = boto3.client('textract',
                        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                        region_name=os.getenv('AWS_REGION'))

bedrock_runtime = boto3.client('bedrock-runtime',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

def upload_to_s3(file, bucket, filename):
    try:
        s3.upload_fileobj(file, bucket, f'inputs/{filename}')
        return True, f"Uploaded {filename} to S3 bucket {bucket}."
    except NoCredentialsError:
        return False, "AWS credentials not found. Please configure your environment."
    except Exception as e:
        return False, f"Failed to upload {filename}: {e}"
    
@exponential_backoff(max_retries=5, base_delay=1, max_delay=60)
def summarize_scrape(scrape_json, company_name):
    """
    Summarize the scraped data.
    :param scrape_json: The JSON data from the web scraping.
    :return: A summary of the scraped data.
    """
    scrape_response = bedrock_runtime.converse(
        ** {
                    'modelId':'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
        'inferenceConfig':{
            'temperature': 0.3,
            'maxTokens': 4096,
        },
        'messages': [{
            'role': 'user',
            'content': [
                {
                    'text': (
                        f'Based on provided web scraping data about company {company_name}, '
                        f'please analyze the following information and provide a summary: '
                        f'{json.dumps(scrape_json, indent=2)}'
                    )
                }
            ]

        }]
        }
    )

    scrape_out = scrape_response['output']['message']['content'][0]['text']

    return scrape_out

def process_file(file):
    file_id = str(uuid.uuid4())
    file_name = file.name
    company_name = file_name.split('_')[0]
    filename = f"{file_id}_{file.name}"
    success, msg = upload_to_s3(file, BUCKET_NAME, filename)

    if not success:
        return filename, {"error": msg}

    if 'rozvaha' in filename:
        adapter_id = '41a4b189bf2f'
        queries = [
    {
        "Text": "aktiva celkem bezne netto",
        "Alias": "ASSETS_TOTAL",
        "Pages": ["*"],
    },
    {
        "Text": "stala aktiva bezne netto",
        "Alias": "FIXED_ASSETS"
    },
    {
        "Text": "obezna aktiva bezne netto",
        "Alias": "CURRENT_ASSETS",
        "Pages": ["*"],
    },
    {
        "Text": "zasoby bezne netto",
        "Alias": "INVENTORIES",
        "Pages": ["*"],
    },
    {
        "Text": "pohledavky bezne netto",
        "Alias": "RECEIVABLES",
        "Pages": ["*"],
    },
    {
        "Text": "penezni prostredky bezne netto",
        "Alias": "CASH_AND_CASH_EQUIVALENTS",
        "Pages": ["*"],
    },
    {
        "Text": "vlastni kapital bezne",
        "Alias": "EQUITY",
        "Pages": ["*"],
    },
    {
        "Text": "zakladni kapital bezne",
        "Alias": "REGISTERED_CAPITAL",
        "Pages": ["*"],
    },
    {
        "Text": "vysledek hospodareni minulych let bezne",
        "Alias": "RETAINED_EARNINGS_PREVIOUS_YEARS",
        "Pages": ["*"],
    },
    {
        "Text": "vysledek hospodareni bezneho ucetniho obdobi bezne",
        "Alias": "PROFIT_LOSS_CURRENT_PERIOD",
        "Pages": ["*"],
    },
    {
        "Text": "cizi zdroje bezne",
        "Alias": "LIABILITIES",
        "Pages": ["*"],
    },
    {
        "Text": "rezervy bezne",
        "Alias": "PROVISIONS",
        "Pages": ["*"],
    },
    {
        "Text": "zavazky bezne",
        "Alias": "PAYABLES",
        "Pages": ["*"],
    }
]  # Keep same as original
    elif 'vysledovka' in filename:
        adapter_id = '0927eda0d229'
        queries = [
    {
        "Text": "bezny provozni vysledek hospodareni",
        "Alias": "OPERATING_PROFIT",
        "Pages": ["*"],
    },
    {
        "Text": "bezny vysledek hospodareni pred zdanenim",
        "Alias": "PROFIT_BEFORE_TAXES"
    },
    {
        "Text": "bezny vysledek hospodareni po zdaneni",
        "Alias": "PROFIT_AFTER_TAXES",
        "Pages": ["*"],
    },
    {
        "Text": "bezny cisty obrat za ucetni obdobi",
        "Alias": "NET_TURNOVER",
        "Pages": ["*"],
    }
] # Keep same as original
    else:
        raise ValueError("Unsupported file type. Only 'rozvaha' and 'vysledovka' are supported.")
    try:
        response = textract.start_document_analysis(
            DocumentLocation={'S3Object': {'Bucket': BUCKET_NAME, 'Name': f"inputs/{filename}"}},
            FeatureTypes=["QUERIES"],
            QueriesConfig={'Queries': queries},
            AdaptersConfig={'Adapters': [{'AdapterId': adapter_id, 'Pages': ['*'], 'Version': '1'}]}
        )

        # Wait for completion
        while True:
            fu_response = textract.get_document_analysis(JobId=response['JobId'])
            status = fu_response['JobStatus']
            if status in ['SUCCEEDED', 'FAILED']:
                break
            time.sleep(5)

        if status == 'SUCCEEDED':
            result = {}
            blocks = fu_response['Blocks']
            for block in blocks:
                if block['BlockType'] == 'QUERY' and 'Relationships' in block:
                    rel_ids = block['Relationships'][0]['Ids']
                    for rel_id in rel_ids:
                        for b in blocks:
                            if b['BlockType'] == 'QUERY_RESULT' and b['Id'] == rel_id:
                                result[block['Query']['Text']] = b['Text']
            return filename, company_name, result
        else:
            raise Exception(f"Textract job failed with status: {status}")
    except Exception as e:
        raise Exception(f"Error processing file {filename}: {e}")

def safe_converse(client, payload, max_retries=5, base_delay=1):
    retries = 0
    while retries < max_retries:
        try:
            response = client.converse(**payload)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == "ThrottlingException":
                wait_time = base_delay * (2 ** retries) + random.uniform(0, 0.5)
                time.sleep(wait_time)
                retries += 1
            else:
                raise
    raise Exception("Max retries exceeded for Converse operation due to throttling.")

def main():
    st.title("OCR Company Analyser")
    uploaded = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    if not uploaded:
        return

    st.info(f"📂 {len(uploaded)} file(s) selected. Processing…")
    
    # Added spinner for uploading files
    with st.spinner("Uploading files..."):
        with ThreadPoolExecutor() as ex:
            results = list(ex.map(process_file, uploaded))

    # with ThreadPoolExecutor() as ex:
    #     results = list(ex.map(process_file, uploaded))

        for res in results:
            filename, company_name,_ = res
    
    # Save raw analysis results to a local json file and upload to S3
    analysis_filename = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(analysis_filename, "w") as f:
        json.dump(results, f)
    try:
        s3.upload_file(analysis_filename, BUCKET_NAME, f"raw_analysis/{analysis_filename}")
        st.success(f"Raw analysis file {analysis_filename} uploaded to S3.")
    except Exception as e:
        st.error(f"Failed to upload raw analysis file: {e}")

    with st.spinner("Scraping info about company..."):
        scrape_json = scraper(company_name)
        scrape_out = summarize_scrape(scrape_json, company_name)

    st.write(f"Scraped data summary: {scrape_out}")
    payload = {
        'modelId':'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        'inferenceConfig':{
            'temperature': 0.3,
            'maxTokens': 4096,
        },
        'system': [{
            'text': 'You are a financial analyst. Analyze the provided financial data and determine if the company is liquid, profitable, and not heavily in debt. Based on your findings, assess whether they are likely to pay invoices on time. Conclude with a short summary: Business with this company is recommended or not recommended. Use Bold and CAPS LOCK for making important parts of text highlighted. Especially the final recommendation.',
        }],

        'toolConfig': {
            'tools': [
                {
                    'toolSpec': {
                        'name': 'financial_analysis_tool',
                        'description': 'This tool provides financial analysis based on the data provided.',
                        'inputSchema': {
                            'json': {
                                'type': 'object',
                                'properties': {
                                    'financial_analysis': {
                                        'type': 'string',
                                        'description': 'The financial analysis result.'
                                    },
                                    'recommendations': {
                                        'type': 'string',
                                        'description': 'Recommendations based on the financial analysis.'
                                    }
                                },
                                'required': ['financial_analysis', 'recommendations']
                            }
                        }
                    }
                }
            ],
            'toolChoice': {
                'tool': {
                    'name': 'financial_analysis_tool',
                }
            }
        },
        'messages': [{
            'role': 'user',
            'content': [
                {
                    'text': f'<content>Financial Statements: {str(results)}</content>',
                },
                {
                    'text': f'<content>Web scraped Results: {scrape_out}</content>',
                },
                {
                    'text': 'Please use the financial analysis tool to analyze the data within <content> tags and provide insights.',
                }
            ]
        }]
    }

    with st.spinner("Model is thinking..."):
        response = safe_converse(bedrock_runtime, payload)
    tool_out = response['output']['message']['content'][0]['toolUse']['input']

    # Use native Streamlit header instead of a CSS card for Tool Output
    st.header("💡 Financial Analysis Tool Output")
    for key, val in tool_out.items():
        st.write(f"**{key}**: {val}")

if __name__ == "__main__":
    main()
