# Deepnote Hackhaton Project

## Overview
This project leverages a finetuned AWS OCR model to extract financial data from scanned PDFs, a web scraping LLM to gather supplementary company information, and a financial analysis LLM to evaluate liquidity, profitability, and debt. The combined analysis helps determine if a company is likely to pay invoices on time.

## Features
- **OCR Processing:**  
  Extracts key financial metrics from balance sheets ("rozvaha") and income statements ("vysledovka") using AWS Textract with custom queries.
- **Web Scraping with LLM:**  
  Enhances financial data by scraping online resources for additional insights about the company.
- **Financial Analysis:**  
  Uses a finetuned LLM to assess financial health and generate recommendations. Important parts of the output are highlighted.
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

## Contributing
Contributions and improvements are welcome. Please follow the standard fork/pull request workflow for submitting enhancements or bug fixes.

## License
This project is available under the MIT License.
