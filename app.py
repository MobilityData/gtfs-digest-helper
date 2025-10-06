# app.py

import os

# Secure token retrieval
try:
    # st.secrets acts like a Python dictionary
    github_token = st.secrets["github"]["token"] 
except KeyError:
    # Try to get from environment variables
    github_token = os.environ.get("GITHUB_TOKEN")
    
    if not github_token:
        st.error("⚠️ GitHub token not configured. Please add GITHUB_TOKEN to your environment variables or Streamlit secrets.")
        st.info("To configure: Add `GITHUB_TOKEN` as an environment variable or create `.streamlit/secrets.toml` with your token.")
        st.stop()  # Stop application execution
