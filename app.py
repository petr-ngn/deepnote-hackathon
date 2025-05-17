import streamlit as st
import boto3
import uuid
from botocore.exceptions import NoCredentialsError
import os
from dotenv import load_dotenv
import time
from concurrent.futures import ThreadPoolExecutor

load_dotenv(override=True)

# Configuration
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


def main():
    st.title("OCR Processor (Parallel)")
    st.write("Upload your PDFs (rozvaha or vysledovka)")

    uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        st.write(f"{len(uploaded_files)} file(s) selected. Processing in parallel...")

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(process_file, uploaded_files))

        for filename, result in results:
            st.subheader(f"Results for {filename}:")
            if "error" in result:
                st.error(result["error"])
            else:
                for key, value in result.items():
                    st.write(f"**{key}**: {value}")

        results_ = {
            filename: result for filename, result in results
        }

        payload = {
            'modelId':'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            'inferenceConfig':{
                'temperature': 0.3,
                'maxTokens': 4096,
            },
            'system': [{
                'text': 'You are a financial analyst. You will be given a list of financial data from a company. Your task is to analyze the data and provide insights.'
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

        response = bedrock_runtime.converse(**payload)

        tool_outputs = response['output']['message']['content'][0]['toolUse']['input']

        st.subheader("Financial Analysis Tool Output:")

        for tool_output_key, tool_output_value in tool_outputs.items():
            st.write(f"**{tool_output_key}**: {tool_output_value}")




if __name__ == "__main__":
    main()
