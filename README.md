# Deepnote Hackhaton Project

## Our use case: AI Powered B2B Fintech company that needs to assess potential clients
The goal is using AI to analyze financial statements and assess the likelihood of companies paying their invoices on time.

## Overview
This project leverages a finetuned AWS OCR model to extract financial data from scanned PDFs, a web scraping LLM to gather supplementary company information, and a financial analysis LLM to evaluate liquidity, profitability, and debt. The combined analysis helps determine if a company is likely to pay invoices on time.

![Project Diagram](hackathon.drawio.png)

## Features
- **OCR Processing:**  
  Extracts key financial metrics from balance sheets ("rozvaha") and income statements ("vysledovka") using AWS Textract with custom queries.
- **LLM Integration:**  
  Utilizing Amazong Bedrock to perform prompt engineering, tool use, function calling, summarization, etc.
- **Web Scraping with Tavily API:**  
  Is a search engine specializing to enhance AI apps. Output of Tavily search is futher enhanced by Anthropic Claude Sonnet to provide a comprehensive overview of the company.
- **Financial Analysis:**  
  Using Anthropic Claude Sonnet to assess financial health and generate recommendations.
- **AWS S3 Integration:**  
  Stores input files and raw analysis results in an S3 bucket.
- **Interactive Interface:**  
  Built with Streamlit, featuring file upload, spinners for processing states, and a summary table displaying key financial metrics.

## Getting Started
1. **Setup Environment:**  
   - Install the required Python packages: `streamlit`, `boto3`, `python-dotenv`, etc.  
   - Configure AWS credentials and necessary environment variables.
2. **Run the Application:**  
   Execute the command `streamlit run app.py` in the project directory.
3. **Usage:**  
   - Upload PDF files containing financial statements.  
   - Follow the interactive prompts as files upload, process, and the LLM executes the analysis.
   - Review the summary table and detailed financial insights on the web interface.

## Project Structure
- **app.py:** Main application logic implementing OCR, web scraping, and financial analysis.
- **scraper.py:** Contains the code for web scraping utilized by the LLM.
- **README.md:** Project documentation.

## Next steps
Large scale finetuning with more training and annotated data for more accurate and robust results.
Expansion to other languages and financial documents.
Utilize multi-agent AI architectures in order to be able to provide more complex and comprehensive analysis.
More proper document classification.

