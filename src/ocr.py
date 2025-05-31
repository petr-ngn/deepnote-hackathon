# pylint: disable=too-few-public-methods
"""
This module provides functionality to perform OCR on financial documents
using AWS Textract and S3 for storage. It extracts relevant information from
PDF files, such as balance sheets and profit and loss statements, and
uploads them to an S3 bucket for further processing.
"""
import os
import uuid
import json
from datetime import datetime
from typing import Dict, Any

from src.aws import (
    S3,
    Textract,
)

class OCR:
    """
    A class for performing Optical Character Recognition (OCR) on financial documents
    using AWS Textract and S3 for storage.

    Attributes:
        config (Dict[str, Any]): Configuration settings for the OCR process.
        s3 (S3): An instance of the S3 class for uploading files.
        textract (Textract): An instance of the Textract class for document analysis.

    Methods:
        _get_pdf_attrs: Extracts attributes from the uploaded PDF file.
        extract: Processes the uploaded PDF file, uploads it to S3, and extracts
                 text using AWS Textract based on the document type.
    """

    def __init__(
            self,
            config: Dict[str, Any],
    ):
        self.config = config

        self.s3 = S3()
        self.textract = Textract()

    def _get_pdf_attrs(
            self,
            file: Any,
    ) -> Dict[str, str]:

        """
        Extracts attributes from the uploaded PDF file.
        Args:
            file: The uploaded PDF file object.
        Returns:
            Dict[str, str]: A dictionary containing the file ID, file name,
                            company name extracted from the file name, and a
                            unique filename ID.
        """
        file_id = str(uuid.uuid4())
        file_name = file.name
        company_name = file_name.split('_')[0]
        filename_id = f"inputs/{file_id}_{file_name}"

        return {
            'file_id': file_id,
            'file_name': file_name,
            'company_name': company_name,
            'filename_id': filename_id,
        }

    def extract(
            self,
            file: Any,
            export_results: bool = True,
    ) -> Dict[str, Any]:
        """
        Processes the uploaded PDF file, uploads it to S3, and extracts text
        using AWS Textract based on the document type (balance sheet or profit and loss statement).
        Args:
            file: The uploaded PDF file object.
            export_results (bool): If True, exports the OCR results to S3.
        Returns:
            Dict[str, Any]: A dictionary containing the document type, company name,
                            file ID, and OCR results.
        """
        attrs = self._get_pdf_attrs(file)

        self.s3.upload(
            file,
            os.environ["S3_BUCKET_NAME"],
            attrs['filename_id'],
        )

        # rozvaha (CZ) = balance sheet (EN)
        if any(
            keyword in attrs['file_name'].lower() for keyword in
            [
                'rozvaha',
                'balancesheet',
                'bsheet',
                'balance_sheet',
            ]
        ):
            adapter_id = os.environ["TEXTRACT_ADAPTER_BALANCE_SHEET_ID"]
            doc_type = "balance_sheet"
            queries = self.config[doc_type]

        # vysledovka (CZ) = profit and loss statement (EN)
        elif any(
            keyword in attrs['file_name'].lower() for keyword in
            [
                'vysledovka',
                'income_statement',
                'incomestatement',
                'profit_loss',
                'profitandloss',
                'profit_and_loss'
                '_pnl_',
                '_pl_',
            ]
        ):
            adapter_id = os.environ["TEXTRACT_ADAPTER_PROFIT_LOSS_ID"]
            doc_type = "profit_loss"
            queries = self.config[doc_type]

        else:
            raise TypeError(f"Unsupported file type: {attrs['file_name']}")

        ocr_results = self.textract.extract(
            file_name = attrs['filename_id'],
            queries = queries,
            adapter_id = adapter_id,
        )

        if export_results:
            self.s3.s3_client.put_object(
                Bucket = os.environ["S3_BUCKET_NAME"],
                Key = f"raw_analysis/analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                Body = json.dumps(
                    ocr_results,
                    ensure_ascii = False,
                ),
                ContentType = "application/json",
            )

        return {
            'doc_type': doc_type,
            'company_name': attrs['company_name'],
            'file_id': attrs['file_id'],
            'ocr_results': ocr_results,
        }
