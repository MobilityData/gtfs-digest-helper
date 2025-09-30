# generate_digest.py
import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

GITHUB_API = "https://api.github.com"
REPO = "google/transit"  # repo cible



def fetch_github_data(token: str, start_date: str, end_date: str):
    """
    Récupère Issues, PRs et Comments du repo google/transit
    entre start_date et end_date (au format YYYY-MM-DD).
    Retourne toujours un tuple: (issues, pulls, issue_comments, pr_comments)
    """
    import requests
    import pandas as pd

    headers = {"Authorization": f"token {token}"}

    def paginated_get(url, params=None):
        items = []
        page = 1
        while True:
            p = params.copy() if params else {}
            p.update({"per_page": 100, "page": page})
            try:
                r = requests.get(url, headers=headers, params=p, timeout=10)
                r.raise_for_status()
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
                break

            data = r.json()
            if not data:
                break
            items.extend(data)
            page += 1
        return items

    # Fonction interne pour filtrer les dates
    def within_period(item, field="created_at"):
        c = pd.to_datetime(item.get(field), errors="coerce")
        if pd.isna(c):
            return False
        # Convertir tz-aware en tz-naive
        if c.tzinfo is not None:
            c = c.tz_convert(None) if hasattr(c, "tz_convert") else c.tz_localize(None)
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        return start <= c <= end

    try:
        # Récupérer les données
        issues = paginated_get(f"{GITHUB_API}/repos/{REPO}/issues", params={"state": "all", "since": start_date})
        pulls = paginated_get(f"{GITHUB_API}/repos/{REPO}/pulls", params={"state": "all"})
        issue_comments = paginated_get(f"{GITHUB_API}/repos/{REPO}/issues/comments", params={"since": start_date})
        pr_comments = paginated_get(f"{GITHUB_API}/repos/{REPO}/pulls/comments", params={"since": start_date})

        # Filtrage sur la période
        issues = [i for i in issues if within_period(i)]
        pulls = [p for p in pulls if within_period(p)]
        issue_comments = [c for c in issue_comments if within_period(c)]
        pr_comments = [c for c in pr_comments if within_period(c)]

        return issues, pulls, issue_comments, pr_comments

    except Exception as e:
        print(f"Error fetching GitHub data: {e}")
        return [], [], [], []


    # Issues
    issues_url = f"{GITHUB_API}/repos/{REPO}/issues"
    issues = paginated_get(
        issues_url, params={"state": "all", "since": start_date}
    )

    # PRs (GitHub traite PR comme issues avec 'pull_request' key)
    pulls_url = f"{GITHUB_API}/repos/{REPO}/pulls"
    pulls = paginated_get(
        pulls_url, params={"state": "all"}
    )

    # Comments
    issues_comments_url = f"{GITHUB_API}/repos/{REPO}/issues/comments"
    issue_comments = paginated_get(
        issues_comments_url, params={"since": start_date}
    )

    pr_comments_url = f"{GITHUB_API}/repos/{REPO}/pulls/comments"
    pr_comments = paginated_get(
        pr_comments_url, params={"since": start_date}
    )

# Filtrer sur la période
def within_period(item, field="created_at"):
    c = pd.to_datetime(item.get(field), errors="coerce")

    # si le timestamp a un fuseau horaire, on le convertit en tz-naive
    if c.tzinfo is not None:
        c = c.tz_convert(None)

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    return (c >= start) and (c <= end)


    issues = [i for i in issues if within_period(i)]
    pulls = [p for p in pulls if within_period(p)]
    issue_comments = [c for c in issue_comments if within_period(c)]
    pr_comments = [c for c in pr_comments if within_period(c)]

    return issues, pulls, issue_comments, pr_comments


def save_to_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_json(path, orient="records", indent=2)


def generate_monthly_digest(token: str, year: int, month: int, out_dir="data/raw-digest"):
    first_day = datetime(year, month, 1)
    last_day = datetime(year + (month // 12), (month % 12) + 1, 1) - pd.Timedelta(days=1)

    issues, pulls, issue_comments, pr_comments = fetch_github_data(
        token, first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")
    )

    folder = Path(out_dir) / f"{year}_{month:02d}"
    save_to_json(issues, folder / "issues.json")
    save_to_json(pulls, folder / "pulls.json")
    save_to_json(issue_comments, folder / "issues_comments.json")
    save_to_json(pr_comments, folder / "pr_comments.json")

    # Retourner les quatre listes
    return issues, pulls, issue_comments, pr_comments
