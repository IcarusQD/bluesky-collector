import csv
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ACTOR = os.environ["BLUESKY_ACTOR"]
DATA_FILE = "data/snapshots.csv"
POST_FILE = "data/posts.csv"

API_BASE = "https://public.api.bsky.app/xrpc"


def get_json(endpoint, params):
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{endpoint}?{query}"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "bluesky-collector/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_file(path, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def load_existing(path):
    if not os.path.exists(path):
        return []

    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    observed_at = utc_now()

    posts = get_json(
        "app.bsky.feed.getAuthorFeed",
        {
            "actor": ACTOR,
            "limit": 100,
        },
    )["feed"]

    post_fields = [
        "post_uri",
        "posted_at",
        "text",
    ]

    snapshot_fields = [
        "observed_at",
        "post_uri",
        "posted_at",
        "likes",
        "reposts",
        "replies",
        "quotes",
    ]

    ensure_file(POST_FILE, post_fields)
    ensure_file(DATA_FILE, snapshot_fields)

    existing_posts = {
        row["post_uri"]
        for row in load_existing(POST_FILE)
    }

    with open(POST_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=post_fields)

        for item in posts:
            post = item["post"]
            author = post["author"]

            if author.get("handle") != ACTOR:
                continue

            record = {
                "post_uri": post["uri"],
                "posted_at": post["record"]["createdAt"],
                "text": post["record"].get("text", ""),
            }

            if record["post_uri"] not in existing_posts:
                writer.writerow(record)
                existing_posts.add(record["post_uri"])

    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=snapshot_fields)

        for item in posts:
            post = item["post"]
            author = post["author"]

            if author.get("handle") != ACTOR:
                continue

            writer.writerow(
                {
                    "observed_at": observed_at,
                    "post_uri": post["uri"],
                    "posted_at": post["record"]["createdAt"],
                    "likes": post.get("likeCount", 0),
                    "reposts": post.get("repostCount", 0),
                    "replies": post.get("replyCount", 0),
                    "quotes": post.get("quoteCount", 0),
                }
            )

    print(
        f"Collected {len(posts)} feed entries at {observed_at}"
    )


if __name__ == "__main__":
    main()
