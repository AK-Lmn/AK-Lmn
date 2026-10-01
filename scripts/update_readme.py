#!/usr/bin/env python3

import os
import sys
import time
import requests

GITHUB_USERNAME = "AK-Lmn"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")
AESPA_CYAN = "22d3ee"
AESPA_BLACK = "0d1117"

TYPE_BADGE = {
    "feat": "feat",
    "fix": "fix",
    "docs": "docs",
    "refactor": "refactor",
    "chore": "chore",
    "perf": "perf",
    "test": "test",
    "style": "style",
    "ci": "ci",
    "build": "build",
}
DEFAULT_BADGE = "contrib"


def search_prs(query: str) -> list[dict]:
    results = []
    page = 1
    while True:
        resp = requests.get(
            "https://api.github.com/search/issues",
            headers=HEADERS,
            params={
                "q": query,
                "per_page": 100,
                "page": page,
                "sort": "created",
                "order": "desc",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        results.extend(items)
        print(f"  Page {page}: got {len(items)} items (total so far: {len(results)})")
        if len(items) < 100 or len(results) >= data["total_count"]:
            break
        page += 1
        time.sleep(1)
    return results


def extract_repo(pr: dict) -> str:
    parts = pr["repository_url"].split("/")
    return f"{parts[-2]}/{parts[-1]}"


def parse_pr(title: str) -> tuple[str, str]:
    low = title.lower()
    for key, label in TYPE_BADGE.items():
        if low.startswith(key):
            colon = title.find(":")
            text = title[colon + 1:].strip() if colon != -1 else title
            if len(text) > 72:
                text = text[:69] + "..."
            return label, text

    label = DEFAULT_BADGE
    text = title if len(title) <= 72 else title[:69] + "..."
    return label, text


def build_readme(all_prs: list[dict]) -> str:
    feed_lines: list[str] = []
    for pr in sorted(all_prs, key=lambda p: p["created_at"], reverse=True):
        repo = extract_repo(pr)
        repo_url = f"https://github.com/{repo}"
        repo_name = repo.split("/")[1]
        label, text = parse_pr(pr["title"])
        feed_lines.append(
            f"`›` [`{repo_name}`]({repo_url}) &nbsp;·&nbsp; "
            f"`[{label.upper()}]` &nbsp;·&nbsp; "
            f"[{text}]({pr['html_url']})<br/>"
        )

    feed_str = "\n".join(feed_lines)

    return f"""<div align="center">

<img src="https://img.shields.io/badge/%C3%A6%20contributions-{AESPA_CYAN}?style=for-the-badge&labelColor={AESPA_BLACK}&color={AESPA_CYAN}&label=%C3%A6" />

</div>

---

{feed_str}
"""


def get_issue(endpoint: str) -> dict:
    url = f"https://api.github.com{endpoint}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    print(f"Fetching merged PRs for @{GITHUB_USERNAME} (external repos only)...")
    merged_prs = search_prs(
        f"author:{GITHUB_USERNAME} is:pr is:merged -user:{GITHUB_USERNAME}"
    )

    print(f"\nFetching open PRs for @{GITHUB_USERNAME} (external repos only)...")
    open_prs = search_prs(
        f"author:{GITHUB_USERNAME} is:pr is:open -user:{GITHUB_USERNAME}"
    )

    shipped_prs = []
    for endpoint in ["/repos/Graphify-Labs/graphify/issues/3923"]:
        try:
            extra = get_issue(endpoint)
            shipped_prs.append(extra)
        except Exception as e:
            print(f"Warning: could not fetch {endpoint}: {e}")

    all_prs = merged_prs + open_prs + shipped_prs
    print(
        f"\nSummary: {len(merged_prs)} merged + {len(open_prs)} open + {len(shipped_prs)} shipped = {len(all_prs)} total PRs"
    )

    print("\nBuilding README...")
    readme_content = build_readme(all_prs)

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(readme_content)

    print(f"README written -> {os.path.abspath(README_PATH)}")


if __name__ == "__main__":
    main()
