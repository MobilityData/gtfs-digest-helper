# app.py

import os

github_token = os.environ.get("GITHUB_TOKEN")

except KeyError:
    if not github_token:
        st.error("⚠️ GitHub token not configured. Please add GITHUB_TOKEN to your environment variables or Streamlit secrets.")
        st.info("To configure: Add `GITHUB_TOKEN` as an environment variable or create `.streamlit/secrets.toml` with your token.")
        st.stop()  # Stop application execution
