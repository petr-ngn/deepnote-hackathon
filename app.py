import streamlit as st
import boto3
import uuid
from botocore.exceptions import NoCredentialsError, ClientError
import os
from dotenv import load_dotenv
import time
from concurrent.futures import ThreadPoolExecutor
import random

load_dotenv(override=True)


# ─── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="OCR Processor (Parallel)",
    page_icon="📄",
    layout="wide",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
    <style>
    /* Overall background & containers */
    .stApp {
        background-color: #f5f7fa;
        color: #273240;
    }
    .reportview-container .main .block-container {
        padding: 2rem 3rem;
    }

    /* Header styling */
    .header {
        background: linear-gradient(90deg, #eaf2fb 0%, #ffffff 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.03);
    }
    .header h1 {
        color: #007acc;
        font-size: 2.5rem;
        margin: 0;
    }
    .header p {
        margin: 0;
        font-size: 1.1rem;
        color: #495057;
    }

    /* Card containers for results */
    .card {
        background: #ffffff;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    .card h3 {
        color: #007acc;
        margin-bottom: 0.5rem;
    }

    /* Button tweaks */
    .stButton>button {
        background-color: #ffb629;
        color: #ffffff;
        border: none;
        padding: 0.5rem 1rem;
        font-size: 1rem;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #e09e22;
        color: #fff;
    }
    </style>
""", unsafe_allow_html=True)


# ─── App Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="header">
  <h1>OCR Processor (Parallel)</h1>
  <p>Upload your balance sheet (“rozvaha”) or income statement (“vysledovka”) PDFs for instant analysis</p>
</div>
""", unsafe_allow_html=True)


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
        queries = queries = [
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
    uploaded = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    if not uploaded:
        return

    st.markdown(f"<div class='card'><h3>📂 {len(uploaded)} file(s) selected. Processing…</h3></div>", unsafe_allow_html=True)

    with ThreadPoolExecutor() as ex:
        results = list(ex.map(process_file, uploaded))

    # Display each result in a card
    #for filename, result in results:
    #    display_name = "_".join(filename.split("_")[1:])
    #    if "error" in result:
    #       st.markdown(f"<div class='card'><h3>❗ {display_name}</h3><p>{result['error']}</p></div>", unsafe_allow_html=True)
    #    else:
    #        st.markdown(f"<div class='card'><h3>✅ Results for {display_name}</h3></div>", unsafe_allow_html=True)
    #        for k, v in result.items():
    #            st.write(f"**{k}**: {v}")

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

    response = safe_converse(bedrock_runtime, payload)
    tool_out = response['output']['message']['content'][0]['toolUse']['input']

    st.markdown("<div class='card'><h3>💡 Financial Analysis Tool Output</h3></div>", unsafe_allow_html=True)
    for key, val in tool_out.items():
        st.write(f"**{key}**: {val}")

    #for tool_output_key, tool_output_value in tool_outputs.items():
    #    st.write(f"**{tool_output_key}**: {tool_output_value}")

if __name__ == "__main__":
    main()