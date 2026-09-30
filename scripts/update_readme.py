#!/usr/bin/env python3
"""
Generates the AK-Lmn GitHub profile README from live contribution data.

Usage:
  GITHUB_TOKEN=<token> python scripts/update_readme.py

Called automatically by the weekly GitHub Actions workflow.
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone
from collections import defaultdict

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


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def search_prs(query: str) -> list[dict]:
    """Paginate the GitHub search API and return all matching PR items."""
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
        time.sleep(1)  # stay well inside the 30 req/min search rate limit
    return results


def get_repo_meta(repo_full_name: str) -> tuple[str, str]:
    """Return (description, html_url) for a public repo."""
    resp = requests.get(
        f"https://api.github.com/repos/{repo_full_name}",
        headers=HEADERS,
    )
    if resp.status_code == 200:
        d = resp.json()
        return (d.get("description") or ""), d.get("html_url", "")
    return "", f"https://github.com/{repo_full_name}"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def extract_repo(pr: dict) -> str:
    """owner/repo from a PR search result's repository_url."""
    parts = pr["repository_url"].split("/")
    return f"{parts[-2]}/{parts[-1]}"


def fmt_date(iso: str) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.strftime("%b %Y")


def badge(label: str, value: str, color: str, logo: str = "github") -> str:
    label_enc = label.replace(" ", "%20").replace("#", "%23")
    value_enc = str(value).replace(" ", "%20").replace("#", "%23").replace("+", "%2B")
    return (
        f"![{label}](https://img.shields.io/badge/"
        f"{label_enc}-{value_enc}-{color}?style=flat-square&logo={logo}&logoColor=white)"
    )

# ---------------------------------------------------------------------------
# README generator
# ---------------------------------------------------------------------------

def build_readme(all_prs: list[dict]) -> str:
    """
    Build a single flat contributions table:
      | Repository | PR | Description |
    All PRs (merged + open), sorted newest first.
    """
    lines: list[str] = [
        "## Contributions",
        "",
        "| Repository | PR | Description |",
        "|------------|----|-------------|",
    ]

    for pr in sorted(all_prs, key=lambda p: p["created_at"], reverse=True):
        repo = extract_repo(pr)
        lines.append(
            f"| `{repo}` "
            f"| [#{pr['number']}]({pr['html_url']}) "
            f"| {pr['title']} |"
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Fetching merged PRs for @{GITHUB_USERNAME} (external repos only)...")
    merged_prs = search_prs(
        f"author:{GITHUB_USERNAME} is:pr is:merged -user:{GITHUB_USERNAME}"
    )

    print(f"\nFetching open PRs for @{GITHUB_USERNAME} (external repos only)...")
    open_prs = search_prs(
        f"author:{GITHUB_USERNAME} is:pr is:open -user:{GITHUB_USERNAME}"
    )

    all_prs = merged_prs + open_prs
    print(
        f"\nSummary: {len(merged_prs)} merged + {len(open_prs)} open = {len(all_prs)} total PRs"
    )

    print("\nBuilding README...")
    readme_content = build_readme(all_prs)

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(readme_content)

    print(f"README written -> {os.path.abspath(README_PATH)}")


if __name__ == "__main__":
    main()
