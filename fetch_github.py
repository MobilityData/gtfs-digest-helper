import os
import requests
import json

OWNER = "google"
REPO = "transit"
OUTDIR = "./github_export"
TOKEN = os.getenv("GITHUB_TOKEN")     

os.makedirs(OUTDIR, exist_ok=True)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {TOKEN}" if TOKEN else None
}

def fetch_all(endpoint, filename):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{endpoint}?state=all&per_page=100"
    out_path = os.path.join(OUTDIR, filename)
    all_data = [] 

    while url:
        print(f"👉  {url}")
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("⚠️  Erreur :", r.status_code, r.text[:300])
            break

        data = r.json()
        if isinstance(data, list):
            all_data.extend(data)
        else:
            print("⚠️  Réponse inattendue :", data)
            break

        link = r.links.get("next", {})
        url = link.get("url")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print(f"✅  {endpoint} -> {out_path}")

if __name__ == "__main__":
    fetch_all("issues",          "issues.json")
    fetch_all("pulls",           "pulls.json")
    fetch_all("issues/comments", "issues_comments.json")
    fetch_all("pulls/comments",  "pr_comments.json")

    print("🎉  Export terminé !")
