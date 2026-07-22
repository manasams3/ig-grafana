import os, csv, json, datetime, requests

TOKEN = os.environ["IG_TOKEN"]
BASE  = "https://graph.instagram.com"   # Instagram Login API

def get(path, params=None):
    params = params or {}
    params["access_token"] = TOKEN
    r = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def metric_value(ins):
    # Handles both response shapes Instagram uses for insights
    d = ins["data"][0]
    if "total_value" in d:
        return d["total_value"]["value"]
    return d["values"][0]["value"]

# 1) Account snapshot ("me" = the token's own account)
acct = get("me", {"fields": "user_id,username,followers_count,follows_count,media_count"})

# 2) All media (paginated) -> keep reels
media, url = [], f"{BASE}/me/media"
params = {"fields": "id,media_product_type,caption,permalink,timestamp,like_count,comments_count",
          "limit": 100, "access_token": TOKEN}
while url:
    r = requests.get(url, params=params, timeout=30); r.raise_for_status()
    data = r.json(); media += data.get("data", [])
    url = data.get("paging", {}).get("next"); params = {}  # 'next' already carries params

reels = [m for m in media if m.get("media_product_type") == "REELS"]

# 3) Views per reel
total_views = 0
for reel in reels:
    try:
        reel["views"] = metric_value(get(f"{reel['id']}/insights", {"metric": "views"}))
    except Exception:
        reel["views"] = 0
    total_views += reel["views"]

# 4) Write a history row
row = {
    "date": datetime.date.today().isoformat(),
    "followers": acct.get("followers_count", 0),
    "following": acct.get("follows_count", 0),
    "posts": acct.get("media_count", 0),
    "reels_count": len(reels),
    "reels_total_views": total_views,
}
os.makedirs("data", exist_ok=True)
file_exists = os.path.exists("data/metrics.csv")
with open("data/metrics.csv", "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=row.keys())
    if not file_exists: w.writeheader()
    w.writerow(row)

# 5) Snapshot of reels for the table panel
with open("data/reels.json", "w") as f:
    json.dump([{ "caption": (r.get("caption") or "")[:60],
                 "views": r.get("views", 0),
                 "likes": r.get("like_count", 0),
                 "comments": r.get("comments_count", 0),
                 "permalink": r.get("permalink"),
                 "timestamp": r.get("timestamp") } for r in reels], f, indent=2)

print("Saved:", row)