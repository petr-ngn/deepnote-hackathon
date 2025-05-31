#pylint: disable=too-few-public-methods
"""
A module that combines web scraping with LLM analysis using the Tavily API and AWS Bedrock.
"""
import copy
from typing import Dict, Any
from src.aws import Bedrock
from src.scraper import TavilyScraper


class LLMScraper(
        TavilyScraper,
        Bedrock,
):
    """
    A class that combines web scraping with LLM analysis using the Tavily API and AWS Bedrock.
    This class inherits from both TavilyScraper and Bedrock, allowing it to scrape data
    and then analyze it using a large language model (LLM).
    Attributes:
        config (Dict[str, Any]): Configuration settings for the Tavily API and AWS Bedrock.
        payload (Dict[str, Any]): The base payload structure for the LLM request.

    Methods:
        _format_payload(company_name, scrape_response): Formats the payload for the LLM request
            by injecting the company name and scraped data.
        analyze(company_name): Scrapes data for a given company name and invokes the LLM
            to analyze the scraped data.
    """
    def __init__(
            self,
            config: Dict[str, Any],
            payload: Dict[str, Any],
    ):
        self.config = config
        self.payload = payload

        TavilyScraper.__init__(self, config)
        Bedrock.__init__(self)


    def _format_payload(
            self,
            company_name: str,
            scrape_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Formats the payload for the LLM request by injecting the company name and scraped data.
        Args:
            company_name (str): The name of the company to be analyzed.
            scrape_response (Dict[str, Any]): The response from the scraping process,
        Returns:
            Dict[str, Any]: A dictionary representing the formatted payload for the LLM request.
        """
        formmatted_payload = copy.deepcopy(self.payload)

        (
            formmatted_payload
            ['messages']
            [0]
            ['content']
            [-1]
            ['text']
        ) = (
            formmatted_payload
            ['messages']
            [0]
            ['content']
            [-1]
            ['text']
            .replace(
                "<<company_name>>",
                company_name,
            )
            .replace(
                "<<scrape_data>>",
                str(scrape_response),
            )
        )

        return formmatted_payload


    def analyze(
            self,
            company_name: str,
    ) -> Dict[str, Any]:
        """
        Scrapes data for a given company name and invokes the LLM to analyze the scraped data.
        Args:
            company_name (str): The name of the company to be analyzed.
        Returns:
            Dict[str, Any]: The response from the LLM after analyzing the scraped data.
        """

        scrape_response = self.scrape(company_name)

        payload = self._format_payload(
            company_name,
            scrape_response,
        )

        llm_response = self.invoke(payload)

        return (
            llm_response
            ['output']
            ['message']
            ['content']
            [0]
            ['text']
        )


class LLMFinAnalyzer(Bedrock):
    """
    A class that provides financial analysis using AWS Bedrock's LLM capabilities.
    This class is designed to analyze financial data by
        processing OCR results and LLM scrape results.
    Attributes:
        payload (Dict[str, Any]): The base payload structure for the LLM request.
    Methods:
        _format_payload(ocr_results, llm_scrape_results): Formats the payload for the LLM request
            by injecting OCR results and LLM scrape results.
        analyze(ocr_results, llm_scrape_results): Analyzes financial data using OCR results and
            LLM scrape results, returning the response from the LLM.
    """

    def __init__(
            self,
            payload: Dict[str, Any],
    ):

        self.payload = payload
        super().__init__()


    def _format_payload(
            self,
            ocr_results: Dict[str, Any],
            llm_scrape_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Formats the payload for the LLM request by injecting OCR results and LLM scrape results.
        Args:
            ocr_results (Dict[str, Any]): The results from OCR processing.
            llm_scrape_results (Dict[str, Any]): The results from LLM scraping.
        Returns:
            Dict[str, Any]: A dictionary representing the formatted payload for the LLM request.
        """

        formmatted_payload = copy.deepcopy(self.payload)

        for i, (placeholder, val) in enumerate(
            {
                '<<ocr_results>>': ocr_results,
                '<<llm_scrape_results>>': llm_scrape_results,
            }.items()
        ):
            (
                formmatted_payload
                ['messages']
                [0]
                ['content']
                [i]
                ['text']
            ) = (
                formmatted_payload
                ['messages']
                [0]
                ['content']
                [i]
                ['text']
                .replace(
                    placeholder,
                    val if isinstance(val, str) else str(val),
                )
            )

        return formmatted_payload


    def analyze(
            self,
            ocr_results: Dict[str, Any],
            llm_scrape_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyzes financial data for a given company name using OCR results and LLM scrape results.
        Args:
            company_name (str): The name of the company to be analyzed.
            ocr_results (Dict[str, Any]): The results from OCR processing.
            llm_scrape_results (Dict[str, Any]): The results from LLM scraping.
        Returns:
            Dict[str, Any]: The response from the LLM after analyzing the financial data.
        """

        payload = self._format_payload(
            ocr_results,
            llm_scrape_results,
        )

        llm_response = self.invoke(payload)

        return (
            llm_response
            ['output']
            ['message']
            ['content']
            [0]
            ['toolUse']
            ['input']
        )
