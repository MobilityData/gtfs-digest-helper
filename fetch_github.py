import os
import requests
import json
from datetime import datetime, timezone

OWNER = "google"
REPO = "transit"
OUTDIR = "./github_export"
TOKEN = os.getenv("GITHUB_TOKEN")

os.makedirs(OUTDIR, exist_ok=True)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {TOKEN}" if TOKEN else None
}

def get_latest_timestamp(file_path):
    """Retourne le timestamp le plus récent dans un fichier JSON existant."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        dates = []
        for item in data:
            if "created_at" in item:
                try:
                    dates.append(datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")))
                except Exception:
                    pass
        if dates:
            return max(dates)
    except Exception as e:
        print(f"⚠️ Erreur en lisant {file_path} : {e}")
    return None


def fetch_new_items(endpoint, filename):
    """Récupère uniquement les nouveaux éléments depuis la dernière date connue."""
    out_path = os.path.join(OUTDIR, filename)
    since_dt = get_latest_timestamp(out_path)
    since_param = ""

    if since_dt:
        since_param = f"&since={since_dt.isoformat()}Z"
        print(f"🕒 Dernière date connue pour {endpoint}: {since_dt}")
    else:
        print(f"🔄 Aucune donnée existante pour {endpoint}, récupération complète.")

    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{endpoint}?state=all&per_page=100&sort=created&direction=asc{since_param}"
    all_data = []

    while url:
        print(f"👉  {url}")
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("⚠️  Erreur :", r.status_code, r.text[:300])
            break

        data = r.json()
        if not isinstance(data, list):
            print("⚠️ Réponse inattendue :", data)
            break

        all_data.extend(data)
        url = r.links.get("next", {}).get("url")

    if all_data:
        print(f"➕ {len(all_data)} nouveaux éléments trouvés pour {endpoint}")

        if os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
        else:
            old_data = []

        existing_ids = {item["id"] for item in old_data if "id" in item}
        new_unique = [i for i in all_data if i.get("id") not in existing_ids]
        merged = old_data + new_unique

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)

        print(f"✅ {len(new_unique)} éléments ajoutés à {filename} ({len(merged)} total).")
    else:
        print(f"⏸ Aucun nouvel élément pour {endpoint}.")


if __name__ == "__main__":
    fetch_new_items("issues", "issues.json")
    fetch_new_items("pulls", "pulls.json")
    fetch_new_items("issues/comments", "issues_comments.json")
    fetch_new_items("pulls/comments", "pr_comments.json")
    print("🎉  Update done")
