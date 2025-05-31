# pylint: disable=too-few-public-methods
"""
This module provides a simple interface to interact with the Tavily API for scraping
information related to a company. It prepares a query based on a given company name
and sends a request to the Tavily API, returning the parsed JSON response.
"""

import os
import json
from urllib.request import (
    Request,
    urlopen,
)
import copy
from typing import Dict, Any

class TavilyScraper:
    """
    A scraper class for querying the Tavily API using a provided configuration.

    Attributes:
        config (Dict[str, Any]): A dictionary containing configuration settings,
                                 including URL, headers, and base payload structure.
    """

    def __init__(
            self,
            config: Dict[str, Any],
    ):
        """
        Initializes the TavilyScraper with the provided configuration.

        Args:
            config (Dict[str, Any]): Configuration for the Tavily API request,
                                     including URL, headers, and payload structure.
        """
        self.config = config

    def _format_data(
            self,
            company_name: str,
    ) -> Dict[str, Any]:
        """
        Constructs the payload for the Tavily API request by injecting the company name
        and API key into a copy of the base payload.

        Args:
            company_name (str): The name of the company to query, which will be
                                combined with 'czech republic' for context.

        Returns:
            Dict[str, Any]: A dictionary representing the completed payload.
        """
        payload = copy.deepcopy(self.config['payload'])
        payload['query'] = f"{company_name} czech republic"
        payload['api_key'] = os.environ['TAVILY_API_KEY']

        return (
            json.dumps(
                payload,
                ensure_ascii=False
            )
            .encode('utf-8')
        )

    def scrape(
            self,
            company_name: str,
    ):
        """
        Executes the web scraping process for a given company name by sending
        a formatted request to the Tavily API and parsing the response.

        Args:
            company_name (str): The name of the company to query.

        Returns:
            Any: The parsed JSON response from the Tavily API.
        """
        data = self._format_data(company_name)

        request = Request(
            url = self.config['url'],
            data= data,
            headers = self.config['headers'],
        )

        with urlopen(request) as response:
            output = json.loads(
                response.read()
                .decode('utf-8')
            )

        return output
