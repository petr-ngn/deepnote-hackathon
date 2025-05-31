# pylint: disable=too-few-public-methods
"""
A module that defines a Streamlit application for OCR, web scraping, and financial analysis
using Large Language Models (LLMs).
"""
from concurrent.futures import ThreadPoolExecutor
import streamlit as st

from src.ocr import OCR
from src.llm import (
    LLMScraper,
    LLMFinAnalyzer,
)

class App:
    """
    A Streamlit application class that integrates OCR, web scraping, and financial analysis
    using LLMs (Large Language Models).
    This class is responsible for setting up the Streamlit UI, handling file uploads,
    performing OCR on uploaded PDFs, scraping data using LLMs, and analyzing financial documents.
    Attributes:
        config (dict): Configuration dictionary containing UI, OCR, LLM, and scraper settings.
        ui_config (dict): UI configuration settings.
        ocr (OCR): An instance of the OCR class for text extraction from PDFs.
        scraper (LLMScraper): An instance of the LLMScraper class for web scraping.
        fin_analyzer (LLMFinAnalyzer): An instance of
            the LLMFinAnalyzer class for financial analysis.
    Methods:
        __init__(config): Initializes the App with the provided configuration.
        run(): Runs the Streamlit application, setting up the UI and processing uploaded files.
            It performs OCR, web scraping, and financial analysis, displaying results in the app.
    """

    def __init__(
            self,
            config: dict,
    ):
        self.config = config

        self.ui_config = config['ui']

        self.ocr = OCR(self.config['ocr'])
        self.scraper = LLMScraper(
            self.config['scraper'],
            self.config['llm']['web_scraping'],
        )
        self.fin_analyzer = LLMFinAnalyzer(
            self.config['llm']['fin_analyzer'],
        )

    def run(
            self,
    ):
        """
        Runs the Streamlit application.
        This method sets up the Streamlit UI, handles file uploads,
        performs OCR on the uploaded PDFs, scrapes data using the LLM,
        and analyzes financial documents using the LLM.
        It displays the results of each step in the Streamlit app.
        Returns:
            None
        """

        st.set_page_config(
            page_title = self.ui_config['title'],
            layout = self.ui_config['layout'],
            menu_items = self.ui_config['menu_items'],
        )

        st.title(self.config['ui']['title'])


        uploaded_files = st.file_uploader(
            "Upload PDFs",
            type = ["pdf"],
            accept_multiple_files = True,
        )

        if not uploaded_files:
            return

        st.info(f"📂 {len(uploaded_files)} file(s) selected. Processing…")

        with st.spinner('Performing OCR on uploaded files...'):
            with ThreadPoolExecutor() as executor:
                ocr_results = list(
                    executor.map(
                        self.ocr.extract,
                        uploaded_files,
                    )
                )

        st.success(f"✅ OCR completed for {len(ocr_results)} file(s).")

        company_name = list({res["company_name"] for res in ocr_results})[0]


        with st.spinner(f"🔍 Scraping data for company: {company_name}..."):
            scrape_response = self.scraper.analyze(company_name)
            st.success("✅ Web scraping completed.")
        st.header("LLM Scrape Results:")
        st.write(scrape_response)


        with st.spinner("💡 LLM analyzing financial documents..."):
            fin_results = self.fin_analyzer.analyze(
                ocr_results,
                scrape_response,
            )
            st.success("✅ Financial analysis completed.")
        st.header("Financial Analysis Results:")
        for k, v in fin_results.items():
            st.write(f"**{k}**: {v}")
