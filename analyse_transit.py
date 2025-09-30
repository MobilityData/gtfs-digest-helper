# analyse_transit.py
import streamlit as st
import pandas as pd
import os
import datetime
from generate_digest import generate_monthly_digest

# --- Step 1: Data Loading ---

BASE_PATH = os.path.join('data', 'cleaned-data')

FILES_TO_LOAD = {
    "issues": "issues_fixed.json",
    "issues_comments": "issues_comments_fixed.json",
    "pulls": "pulls_fixed.json",
    "pr_comments": "pr_comments_fixed.json",
}

@st.cache_data
def load_all_data():
    """Load all JSON files into pandas DataFrames."""
    dataframes = {}
    for key, file_name in FILES_TO_LOAD.items():
        path = os.path.join(BASE_PATH, file_name)
        try:
            dataframes[key] = pd.read_json(path)
        except FileNotFoundError:
            st.error(f"File not found: {path}. Please check your folder structure.")
            return None
        except Exception as e:
            st.error(f"Error loading {file_name}: {e}")
            return None
    return dataframes

all_data = load_all_data()

if all_data and "issues" in all_data and "issues_comments" in all_data and "pr_comments" in all_data:
    issues_df = all_data["issues"]
    issues_comments_df = all_data["issues_comments"]
    pr_comments_df = all_data["pr_comments"]

    # --- Step 2: Data Cleaning ---
    for col in ['created_at', 'updated_at', 'closed_at']:
        if col in issues_df.columns:
            issues_df[col] = pd.to_datetime(issues_df[col], errors='coerce')

    if 'user' in issues_df.columns:
        issues_df['username'] = issues_df['user'].apply(lambda u: u.get('login') if isinstance(u, dict) else None)

    issues_comments_df['body'] = issues_comments_df['body'].fillna('')
    pr_comments_df['body'] = pr_comments_df['body'].fillna('')

    # --- Step 3: Streamlit UI ---
    st.title("Google Transit - Contribution Analyzer")
    st.header("Explore Issues and Pull Requests")
    st.info("Use the filters in the sidebar to refine your search.")
    st.sidebar.header("Monthly Digest")

# --- Step 4: Digest Selection ---
year = st.sidebar.selectbox("Year", [2025, 2024, 2023], index=0)
month = st.sidebar.selectbox("Month", list(range(1,13)), index=datetime.date.today().month-1)

if st.sidebar.button(f"Generate {month}-{year} Digest"):
    with st.spinner("Fetching data from GitHub..."):
        issues, pulls, issue_comments, pr_comments = generate_monthly_digest(
            st.secrets["github"]["token"],
            year,
            month
        )

    # --- Monthly Stats ---
    total_issues = len(issues)
    total_pulls = len(pulls)
    total_comments = len(issue_comments) + len(pr_comments)

    st.success(f"Digest generated: {total_issues} issues, "
               f"{total_pulls} PRs, "
               f"{total_comments} comments.")

    # Top contributors and issue/PR status
    if issues:
        issues_month_df = pd.DataFrame(issues)
        if 'user' in issues_month_df.columns:
            issues_month_df['username'] = issues_month_df['user'].apply(
                lambda u: u.get('login') if isinstance(u, dict) else None
            )
            st.subheader("Top Contributors This Month")
            st.bar_chart(issues_month_df['username'].value_counts().head(10))

        st.subheader("Status of Issues/PRs This Month")
        st.bar_chart(issues_month_df['state'].value_counts())

    st.subheader("Comments This Month")
    st.write(f"Issue comments: {len(issue_comments)}, PR comments: {len(pr_comments)}")

# --- Step 5: Sidebar Filters ---
st.sidebar.header("Filters")

# Filter by user
if 'username' in issues_df.columns:
    users = sorted(issues_df['username'].dropna().unique())
    selected_users = st.sidebar.multiselect("Filter by user", users)
else:
    selected_users = []

# Filter by date range
min_date = issues_df['created_at'].min().to_pydatetime()
max_date = issues_df['created_at'].max().to_pydatetime()
selected_dates = st.sidebar.date_input(
    "Filter by creation date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Filter by keyword
search_term = st.sidebar.text_input("Search keyword in title or comments")

# --- Step 6: Filtering Logic ---
filtered_issues = issues_df.copy()

if selected_users:
    filtered_issues = filtered_issues[filtered_issues['username'].isin(selected_users)]

if len(selected_dates) == 2:
    start_date, end_date = pd.to_datetime(selected_dates[0]), pd.to_datetime(selected_dates[1])
    filtered_issues = filtered_issues[
        (filtered_issues['created_at'].dt.date >= start_date.date()) &
        (filtered_issues['created_at'].dt.date <= end_date.date())
    ]

if search_term:
    # Matching titles
    title_mask = filtered_issues['title'].str.contains(search_term, case=False, na=False)

    # Matching issue comments
    matching_issue_comments = issues_comments_df[issues_comments_df['body'].str.contains(search_term, case=False)]
    issue_numbers_from_comments = matching_issue_comments['issue_url'].str.split('/').str[-1].astype(int).unique()

    # Matching PR comments
    matching_pr_comments = pr_comments_df[pr_comments_df['body'].str.contains(search_term, case=False)]
    pr_numbers_from_comments = matching_pr_comments['pull_request_url'].str.split('/').str[-1].astype(int).unique()

    all_comment_numbers = set(issue_numbers_from_comments) | set(pr_numbers_from_comments)
    comment_mask = filtered_issues['number'].isin(all_comment_numbers)

    filtered_issues = filtered_issues[title_mask | comment_mask]

# --- Step 7: Display Results ---
st.header(f"Results: {len(filtered_issues)} items found")
st.dataframe(filtered_issues[['number', 'title', 'username', 'state', 'created_at']])

# Matching comments if search_term is provided
if search_term and not filtered_issues.empty:
    st.subheader("Matching Comments")

    matching_issue_comments = issues_comments_df[
        (issues_comments_df['body'].str.contains(search_term, case=False, na=False)) &
        (issues_comments_df['issue_url'].str.split('/').str[-1].astype(int)
             .isin(filtered_issues['number']))
    ]

    matching_pr_comments = pr_comments_df[
        (pr_comments_df['body'].str.contains(search_term, case=False, na=False)) &
        (pr_comments_df['pull_request_url'].str.split('/').str[-1].astype(int)
             .isin(filtered_issues['number']))
    ]

    combined_comments = pd.concat([
        matching_issue_comments[['issue_url', 'user', 'body', 'created_at']],
        matching_pr_comments[['pull_request_url', 'user', 'body', 'created_at']]
    ], ignore_index=True)

    if not combined_comments.empty:
        combined_comments['username'] = combined_comments['user'].apply(
            lambda u: u.get('login') if isinstance(u, dict) else None
        )
        st.dataframe(combined_comments[['username', 'body', 'created_at']])
    else:
        st.info("No comments matched the search term in the selected issues/PRs.")

# --- Step 8: Visualizations ---
st.header("Statistics for the Current Selection")

if not filtered_issues.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Contributors")
        st.bar_chart(filtered_issues['username'].value_counts().head(10))

    with col2:
        st.subheader("Status of Issues/PRs")
        st.bar_chart(filtered_issues['state'].value_counts())
else:
    st.warning("No data to display for the current selection.")
