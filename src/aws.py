# pylint: disable=too-few-public-methods
"""
A module for interacting with AWS services such as S3, Textract, and Bedrock.
"""
import os
from typing import Dict, Any
import boto3

from src.utils import (
    exponential_backoff,
    wait_for_completion,
)

class S3:
    """
    A class for interacting with AWS S3 to upload files.
    Attributes:
        s3_client (boto3.client): The S3 client for performing operations.
    Methods:
        upload: Uploads a file to the specified S3 bucket.
    """

    def __init__(self):

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY'],
            region_name = os.environ['AWS_REGION']
        )

    def upload(
            self,
            file: Any,
            bucket_name: str,
            file_name: str,
    ):
        """
        Uploads a file to the specified S3 bucket.
        Args:
            file: The file object to upload.
            bucket_name (str): The name of the S3 bucket.
            file_name (str): The name under which the file will be stored in the bucket.
        """
        self.s3_client.upload_fileobj(
            file,
            bucket_name,
            file_name,
        )



class Textract:
    """
    A class for interacting with AWS Textract to analyze documents.
    Attributes:
        textract_client (boto3.client): The Textract client for performing operations.
    Methods:
        _start_analyze:
            Starts a document analysis job with specified queries and adapter configuration.
        _analyze(job_response:
            Processes the response from a Textract document analysis job to extract query results.
        _wait_for_analyze:
            Waits for the Textract document analysis job to complete and retrieves the results.
        extract(file_name: str, queries: Dict[str, Any], adapter_id: str, version: str = '1'):
            Starts a document analysis job and waits for its completion, returning the results. 
    """

    def __init__(self):

        self.textract_client = boto3.client(
            'textract',
            aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY'],
            region_name = os.environ['AWS_REGION'],
        )

    def _start_analyze(
            self,
            file_name: str,
            queries: Dict[str, Any],
            adapter_id: str,
            version: str = '1',
    ) -> Dict[str, Any]:
        """
        Starts a document analysis job with specified queries and adapter configuration.
        Args:
            file_name (str): The name of the file to analyze.
            queries (Dict[str, Any]): A dictionary containing queries to be processed.
            adapter_id (str): The ID of the adapter to use for the analysis.
            version (str): The version of the adapter to use. Defaults to '1'.
        Returns:
            Dict[str, Any]: The response from the Textract service containing job details.
        """

        response = self.textract_client.start_document_analysis(
            DocumentLocation = {
                'S3Object': {
                    'Bucket': os.environ['S3_BUCKET_NAME'],
                    'Name': file_name,
                },
            },
            FeatureTypes = ["QUERIES"],
            QueriesConfig = {
                'Queries': queries,
            },
            AdaptersConfig = {
                'Adapters': [{
                    'AdapterId': adapter_id,
                    'Pages': ['*'],
                    'Version': version,
                }],
            },
        )

        return response

    def _analyze(
        self,
        job_response: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Processes the response from a Textract document analysis job to extract query results.
        Args:
            job_response (Dict[str, Any]): The response from the Textract service
                containing job details.
        Returns:
            Dict[str, str]: A dictionary mapping query texts to their corresponding results.
        """
        if job_response['JobStatus'] != 'SUCCEEDED':
            raise ValueError(
                f"Textract job failed with status: {job_response['JobStatus']}"
            )

        ocr_results = {}
        blocks = job_response['Blocks']

        query_results = {
            block['Id']: block['Text']
            for block in blocks
            if block['BlockType'] == 'QUERY_RESULT'
        }

        for block in blocks:
            if block['BlockType'] != 'QUERY' or 'Relationships' not in block:
                continue

            query_text = block['Query']['Text']
            for rel_id in block['Relationships'][0]['Ids']:
                if rel_id in query_results:
                    ocr_results[query_text] = query_results[rel_id]

        return ocr_results


    @wait_for_completion()
    def _wait_for_analyze(
            self,
            start_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Waits for the Textract document analysis job to complete and retrieves the results.
        Args:
            start_response (Dict[str, Any]): The response from the Textract service 
                containing job details.
        Returns:
            Dict[str, Any]: The response from the Textract service containing the analysis results.
        """

        response = self.textract_client.get_document_analysis(
            JobId = start_response['JobId'],
        )

        return response


    def extract(
            self,
            file_name: str,
            queries: Dict[str, Any],
            adapter_id: str,
            version: str = '1',
    ) -> Dict[str, str]:
        """
        Starts a document analysis job and waits for its completion, returning the results.
        Args:
            file_name (str): The name of the file to analyze.
            queries (Dict[str, Any]): A dictionary containing queries to be processed.
            adapter_id (str): The ID of the adapter to use for the analysis.
            version (str): The version of the adapter to use. Defaults to '1'.
        Returns:
            Dict[str, str]: A dictionary mapping query texts to their corresponding results.
        """

        start_response = self._start_analyze(
            file_name = file_name,
            queries = queries,
            adapter_id = adapter_id,
            version = version,
        )

        job_response = self._wait_for_analyze(
            start_response = start_response,
        )

        ocr_results = self._analyze(
            job_response = job_response,
        )

        return ocr_results






class Bedrock:
    """
    A class for interacting with AWS Bedrock LLM's.
    Attributes:
        bedrock_client (boto3.client): The Bedrock client for performing operations.
    Methods:
        invoke: Sends a request to the Bedrock LLM
            and returns the response.
    """

    def __init__(self):

        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY'],
            region_name = os.environ['AWS_REGION']
        )

    @exponential_backoff()
    def invoke(
            self,
            payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sends a request to the Bedrock LLM and returns the response.
        Args:
            payload (Dict[str, Any]): The payload to send to the Bedrock LLM.
        Returns:
            Dict[str, Any]: The response from the Bedrock LLM.
        """

        response = self.bedrock_client.converse(
            ** payload,
        )

        return response
