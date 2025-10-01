# analyse_transit.py
import streamlit as st
import pandas as pd
import os
import datetime
from generate_digest import generate_monthly_digest
from datetime import timezone
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from github import Github



# --- Step 1: Data Loading ---
BASE_PATH = os.path.join('data', 'cleaned-data')
FILES_TO_LOAD = {
    "issues": "issues.json",
    "issues_comments": "issues_comments.json",
    "pulls": "pulls.json",
    "pr_comments": "pr_comments.json",
}

@st.cache_data
def load_all_data():
    dataframes = {}
    for key, file_name in FILES_TO_LOAD.items():
        path = os.path.join(BASE_PATH, file_name)
        try:
            dataframes[key] = pd.read_json(path)
        except FileNotFoundError:
            st.error(f"File not found: {path}")
            return None
        except Exception as e:
            st.error(f"Error loading {file_name}: {e}")
            return None
    return dataframes

all_data = load_all_data()
if all_data and all(k in all_data for k in ["issues", "issues_comments", "pr_comments", "pulls"]):
    issues_df = all_data["issues"]
    issues_comments_df = all_data["issues_comments"]
    pr_comments_df = all_data["pr_comments"]
    pulls_df = all_data["pulls"]

    

    # --- Data Cleaning ---
    for col in ['created_at', 'updated_at', 'closed_at']:
        if col in issues_df.columns:
            issues_df[col] = pd.to_datetime(issues_df[col], errors='coerce', utc=True)
    if 'user' in issues_df.columns:
        issues_df['username'] = issues_df['user'].apply(lambda u: u.get('login') if isinstance(u, dict) else None)

    issues_comments_df['body'] = issues_comments_df['body'].fillna('')
    pr_comments_df['body'] = pr_comments_df['body'].fillna('')

# --- Streamlit UI ---
st.title("🚆 Google Transit - Contribution Analyzer")
st.info("Use the sidebar to generate a monthly digest or filter issues/PRs.")

# --- Sidebar for Digest ---
st.sidebar.header("🗓️ Monthly Digest")
year = st.sidebar.selectbox("Year", [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015], index=0)
month = st.sidebar.selectbox("Month", list(range(1, 13)), index=datetime.date.today().month - 1)


# -------------------------------
# 1. GTFS DIGEST
# -------------------------------
# --- Sélection du mois et de l'année dans la page principale ---
st.header("🗓️ Generate Monthly Digest")
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Year", [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015], index=0)
with col2:
    month = st.selectbox("Month", list(range(1, 13)), index=datetime.date.today().month - 1)

# --- Bouton Generate Digest ---
if st.button(f"✨Generate {month}-{year} Digest"):
    with st.spinner("Fetching data from GitHub..."):
        issues, pulls, issue_comments, pr_comments = generate_monthly_digest(
            st.secrets["github"]["token"],
            year,
            month
        )

    start_date = datetime.datetime(year, month, 1, tzinfo=timezone.utc)
    end_date = (start_date + pd.offsets.MonthEnd(1)).to_pydatetime().replace(tzinfo=timezone.utc)

    def created_within(item):
        dt = pd.to_datetime(item.get('created_at'), utc=True)
        return start_date <= dt <= end_date

    # --- 1a. Top Contributors ---
    contrib_counter = Counter()
    for i in issues:
        if created_within(i):
            login = i.get('user', {}).get('login')
            if login: contrib_counter[login] += 1
    for p in pulls:
        if created_within(p):
            login = p.get('user', {}).get('login')
            if login: contrib_counter[login] += 1
    for c in issue_comments + pr_comments:
        created = pd.to_datetime(c.get('created_at'), utc=True)
        if start_date <= created <= end_date:
            login = c.get('user', {}).get('login')
            if login: contrib_counter[login] += 1
    contrib_df = pd.DataFrame.from_dict(contrib_counter, orient='index', columns=['count']).sort_values('count', ascending=False)
    st.subheader("1️⃣ Top Contributors (comments, issues, PRs)")
    st.bar_chart(contrib_df.head(10))

    # --- 1b. Most Commented ---
    st.subheader("2️⃣ Most Commented Issues & PRs")
    comment_counts = {}
    for c in issue_comments + pr_comments:
        created = pd.to_datetime(c.get('created_at'), utc=True)
        if start_date <= created <= end_date:
            num = c.get('issue_url') or c.get('pull_request_url')
            if num:
                num = num.split('/')[-1]
                comment_counts[num] = comment_counts.get(num, 0) + 1
    top_comments = sorted(comment_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for num, count in top_comments:
        match = next((i for i in issues if str(i.get('number')) == str(num)), None)
        if not match:
            match = next((p for p in pulls if str(p.get('number')) == str(num)), None)
        if match:
            st.markdown(f"- [{match.get('title')}]({match.get('html_url')}) - {count} comments")

    # --- 1c. Word Cloud ---
    st.subheader("3️⃣ Word Cloud (issues, PRs, comments)")
    text_corpus = []

    for i in issues + pulls:
        if created_within(i):
            text_corpus.append(i.get('title',''))
    for c in issue_comments + pr_comments:
        created = pd.to_datetime(c.get('created_at'), utc=True)
        if start_date <= created <= end_date:
            text_corpus.append(c.get('body',''))

    stopwords = {
        "the","with","that","this","what","would","could","should","have","from",
        "your","their","there","were","when","them","then","also","these","they",
        "been","about","than","into","like","over","some","such","only","more",
        "most","many","make","just","will","who","whom","each","other","after",
        "before","while","where","here","how","why","which","and","but","for","are",
        "not","you","all","our","its","was","had","can","may","get","use","using",
        "does","did","done","very", "it's", "that's"
    }
    words = [w.lower() for txt in text_corpus for w in txt.split()
             if len(w) >= 4 and w.lower() not in stopwords]
    word_freq = dict(Counter(words).most_common(10))

    if word_freq:
        wc = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_freq)
        fig, ax = plt.subplots(figsize=(10,5))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    else:
        st.info("No words to generate word cloud.")

    # --- 1d. New Contributors ---
st.subheader("🆕 New Contributors This Month")

def extract_logins_df(df):
    """Extrait les logins depuis une colonne 'user' ou 'username' d'un DataFrame"""
    if 'username' in df.columns:
        return set(df['username'].dropna())
    elif 'user' in df.columns:
        return set(df['user'].apply(lambda u: u.get('login') if isinstance(u, dict) else None).dropna())
    return set()

# --- Contributeurs du mois sélectionné ---
month_issues = issues_df[
    (issues_df['created_at'] >= pd.Timestamp(year, month, 1, tz='UTC')) &
    (issues_df['created_at'] <= pd.Timestamp(year, month, 1, tz='UTC') + pd.offsets.MonthEnd(1))
]
month_pulls = pulls_df[
    (pulls_df['created_at'] >= pd.Timestamp(year, month, 1, tz='UTC')) &
    (pulls_df['created_at'] <= pd.Timestamp(year, month, 1, tz='UTC') + pd.offsets.MonthEnd(1))
]
month_issue_comments = issues_comments_df[
    (issues_comments_df['created_at'] >= pd.Timestamp(year, month, 1, tz='UTC')) &
    (issues_comments_df['created_at'] <= pd.Timestamp(year, month, 1, tz='UTC') + pd.offsets.MonthEnd(1))
]
month_pr_comments = pr_comments_df[
    (pr_comments_df['created_at'] >= pd.Timestamp(year, month, 1, tz='UTC')) &
    (pr_comments_df['created_at'] <= pd.Timestamp(year, month, 1, tz='UTC') + pd.offsets.MonthEnd(1))
]

current_month_contribs = (
    extract_logins_df(month_issues) |
    extract_logins_df(month_pulls) |
    extract_logins_df(month_issue_comments) |
    extract_logins_df(month_pr_comments)
)

# --- Contributeurs avant le mois sélectionné ---
past_issues = issues_df[issues_df['created_at'] < pd.Timestamp(year, month, 1, tz='UTC')]
past_pulls = pulls_df[pulls_df['created_at'] < pd.Timestamp(year, month, 1, tz='UTC')]
past_issue_comments = issues_comments_df[issues_comments_df['created_at'] < pd.Timestamp(year, month, 1, tz='UTC')]
past_pr_comments = pr_comments_df[pr_comments_df['created_at'] < pd.Timestamp(year, month, 1, tz='UTC')]

past_contribs = (
    extract_logins_df(past_issues) |
    extract_logins_df(past_pulls) |
    extract_logins_df(past_issue_comments) |
    extract_logins_df(past_pr_comments)
)

# --- Nouveaux contributeurs ---
new_contribs = current_month_contribs - past_contribs

if new_contribs:
    for login in sorted(new_contribs):
        profile_url = f"https://github.com/{login}"
        st.markdown(f"- [{login}]({profile_url})")
else:
    st.info("No new contributors this month.")



# -------------------------------
# 2. State of PR (active PRs)
# -------------------------------
@st.cache_data(ttl=3600)  #Cache for 1 hour
def fetch_live_prs():
    token = st.secrets["github"]["token"]
    gh = Github(token)
    repo = gh.get_repo("google/transit")
    pulls = repo.get_pulls(state="open")
    prs = []
    for pr in pulls:
        prs.append({
            "number": pr.number,
            "title": pr.title,
            "html_url": pr.html_url,
            "labels": [ {"name": lbl.name} for lbl in pr.get_labels() ]
        })
    return prs


st.header("🚨 State of Active PRs (Live)")
live_prs = fetch_live_prs()

label_to_prs = {
    "Discussion Period": [p for p in live_prs if any(l["name"] == "Discussion Period" for l in p["labels"])],
    "Vote to Adopt": [p for p in live_prs if any(l["name"] == "Vote to Adopt" for l in p["labels"])],
    "Vote to Test": [p for p in live_prs if any(l["name"] == "Vote to Test" for l in p["labels"])]
}

if not any(label_to_prs.values()):
    st.info("No active PRs found at the moment.")
else:
    for label, prs in label_to_prs.items():
        if prs:
            st.markdown(f"**{label}**")
            for p in prs:
                st.markdown(f"- [{p['title']}]({p['html_url']})")



# -------------------------------
# 3. Searchable Stats (Issues/PRs + Comments)
# -------------------------------
st.header("🔍 Searchable Stats")
st.sidebar.header("Filters for Search")

# --- Sidebar Filters ---
users = sorted(issues_df['username'].dropna().unique()) if 'username' in issues_df.columns else []
selected_users = st.sidebar.multiselect("Filter by user", users)

min_date = min(issues_df['created_at'].min(), pulls_df['created_at'].min())
max_date = max(issues_df['created_at'].max(), pulls_df['created_at'].max())
selected_dates = st.sidebar.date_input(
    "Filter by creation date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

search_term = st.sidebar.text_input("Search keyword in title or comments")

# --- Filter Issues/PRs ---
filtered_issues = issues_df.copy()
filtered_pulls = pulls_df.copy()

if selected_users:
    filtered_issues = filtered_issues[filtered_issues['username'].isin(selected_users)]
    filtered_pulls = filtered_pulls[filtered_pulls['user'].apply(lambda u: u.get('login') if isinstance(u, dict) else None).isin(selected_users)]

if len(selected_dates) == 2:
    start_date, end_date = pd.to_datetime(selected_dates[0]), pd.to_datetime(selected_dates[1])
    filtered_issues = filtered_issues[
        (filtered_issues['created_at'].dt.date >= start_date.date()) &
        (filtered_issues['created_at'].dt.date <= end_date.date())
    ]
    filtered_pulls = filtered_pulls[
        (filtered_pulls['created_at'].dt.date >= start_date.date()) &
        (filtered_pulls['created_at'].dt.date <= end_date.date())
    ]

if search_term:
    # Filter titles
    issue_title_mask = filtered_issues['title'].str.contains(search_term, case=False, na=False)
    pull_title_mask = filtered_pulls['title'].str.contains(search_term, case=False, na=False)
    filtered_issues = filtered_issues[issue_title_mask]
    filtered_pulls = filtered_pulls[pull_title_mask]

# --- Display Issues & PRs ---
st.subheader(f"Issues found: {len(filtered_issues)}")
st.dataframe(filtered_issues[['number', 'title', 'username', 'state', 'created_at']])

st.subheader(f"Pull Requests found: {len(filtered_pulls)}")
st.dataframe(filtered_pulls[['number', 'title', 'user', 'state', 'created_at']])

# --- Filter Comments ---
filtered_issue_comments = issues_comments_df.copy()
filtered_pr_comments = pr_comments_df.copy()

# Filter by date
if len(selected_dates) == 2:
    filtered_issue_comments = filtered_issue_comments[
        (pd.to_datetime(filtered_issue_comments['created_at']).dt.date >= start_date.date()) &
        (pd.to_datetime(filtered_issue_comments['created_at']).dt.date <= end_date.date())
    ]
    filtered_pr_comments = filtered_pr_comments[
        (pd.to_datetime(filtered_pr_comments['created_at']).dt.date >= start_date.date()) &
        (pd.to_datetime(filtered_pr_comments['created_at']).dt.date <= end_date.date())
    ]

# Filter by search term
if search_term:
    filtered_issue_comments = filtered_issue_comments[filtered_issue_comments['body'].str.contains(search_term, case=False, na=False)]
    filtered_pr_comments = filtered_pr_comments[filtered_pr_comments['body'].str.contains(search_term, case=False, na=False)]

# --- Extract pseudo/login ---
filtered_issue_comments['login'] = filtered_issue_comments['user'].apply(lambda u: u.get('login') if isinstance(u, dict) else None)
filtered_pr_comments['login'] = filtered_pr_comments['user'].apply(lambda u: u.get('login') if isinstance(u, dict) else None)

# Add type column
filtered_issue_comments['type'] = 'Issue Comment'
filtered_pr_comments['type'] = 'PR Comment'

# Combine comments
filtered_comments = pd.concat([filtered_issue_comments, filtered_pr_comments], ignore_index=True)

# --- Top Contributors (comments) ---
top_contributors = filtered_comments['login'].value_counts().head(9).reset_index()
top_contributors.columns = ['Contributor', 'Comments Count']
st.subheader("🏆 Top Contributors (comments)")
st.dataframe(top_contributors)

# --- Display filtered comments ---
st.subheader(f"Comments found: {len(filtered_comments)}")
st.dataframe(filtered_comments[['login','type','body','created_at']].rename(columns={'login':'Contributor'}))
