# app.py

import os

github_token = os.environ.get("GITHUB_TOKEN")

if not github_token:
    raise ValueError("⚠️ GitHub token not configured. Please add GITHUB_TOKEN to your environment variables or Streamlit secrets.")
    raise ValueError("To configure: Add `GITHUB_TOKEN` as an environment variable or create `.streamlit/secrets.toml` with your token.")
