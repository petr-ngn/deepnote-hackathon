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

load_dotenv(override=True)

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

def process_file(file):
    file_id = str(uuid.uuid4())
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
        return filename, {"error": "Invalid file name. Must contain 'rozvaha' or 'vysledovka'."}

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
            return filename, result
        else:
            return filename, {"error": "Textract job failed."}
    except Exception as e:
        return filename, {"error": str(e)}

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
    st.title("OCR Processor (Parallel)")  # Added title within main()
    uploaded = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    if not uploaded:
        return

    # Use native Streamlit info box instead of a CSS card
    st.info(f"📂 {len(uploaded)} file(s) selected. Processing…")

    with st.spinner("Processing files..."):
        with ThreadPoolExecutor() as ex:
            results = list(ex.map(process_file, uploaded))
    st.markdown(f"<div class='card'><h3>📂 {len(uploaded)} file(s) selected. Processing…</h3></div>", unsafe_allow_html=True)
    for file in uploaded:
        bytes_data = file.read()
        base64_bytes = base64.b64encode(bytes_data).decode('utf-8')
        with st.expander(f"File: {file.name}", expanded=False):
            st.markdown(
                                f'''
                                <iframe src="data:application/pdf;base64,{base64_bytes}#zoom=3.0" 
                                width="500" height="600" type="application/pdf"></iframe>
                                ''',
                                unsafe_allow_html=True
            )
    with ThreadPoolExecutor() as ex:
        results = list(ex.map(process_file, uploaded))

    # Save raw analysis results to a local json file and upload to S3
    analysis_filename = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(analysis_filename, "w") as f:
        json.dump(results, f)
    try:
        s3.upload_file(analysis_filename, BUCKET_NAME, f"raw_analysis/{analysis_filename}")
        st.success(f"Raw analysis file {analysis_filename} uploaded to S3.")
    except Exception as e:
        st.error(f"Failed to upload raw analysis file: {e}")

    payload = {
        'modelId':'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        'inferenceConfig':{
            'temperature': 0.3,
            'maxTokens': 4096,
        },
        'system': [{
            'text': 'You are a financial analyst. Analyze the provided financial data and determine if the company is liquid, profitable, and not heavily in debt. Based on your findings, assess whether they are likely to pay invoices on time. Conclude with a short summary: Business with this company is recommended or not recommended.'
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
                    'text': f'<content>{str(results)}</content>',
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

