import streamlit as st

def set_page_config():
    st.set_page_config(
        page_title="OCR Processor (Parallel)",
        page_icon="📄",
        layout="wide",
    )

def inject_css():
    st.markdown(r"""
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