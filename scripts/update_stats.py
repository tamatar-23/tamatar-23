import os
import json
import re
import urllib.request
import time
from datetime import datetime

TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
USERNAME = "tamatar-23"

def graphql_query(query, variables=None):
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Python-GH-Stats"
    }
    data = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return None

def calculate_uptime(created_at_str):
    try:
        created_at = datetime.strptime(created_at_str[:10], "%Y-%m-%d")
        now = datetime.now()
        
        years = now.year - created_at.year
        months = now.month - created_at.month
        days = now.day - created_at.day
        
        if days < 0:
            months -= 1
            days += 30
        if months < 0:
            years -= 1
            months += 12
            
        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years > 1 else ''}")
        if months > 0:
            parts.append(f"{months} month{'s' if months > 1 else ''}")
        parts.append(f"{days} day{'s' if days > 1 else ''}")
        
        return ", ".join(parts)
    except Exception:
        return "1 year, 5 months, 15 days"

def get_github_stats():
    years_query = """
    query($username: String!) {
      user(login: $username) {
        createdAt
        followers { totalCount }
        repositoriesContributedTo { totalCount }
        contributionsCollection {
          contributionYears
        }
        repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR]) {
          nodes {
            name
            owner { login }
            stargazerCount
            isPrivate
            isFork
          }
        }
      }
    }
    """
    
    res = graphql_query(years_query, {"username": USERNAME})
    if not res or "data" not in res or not res["data"].get("user"):
        print("Fallback to default stats due to API error")
        return {
            "uptime": "1 year, 5 months, 15 days",
            "repos": 33,
            "contributed": 3,
            "stars": 7,
            "commits": 231,
            "followers": 13,
            "additions": 1779762,
            "deletions": 37248,
            "total_loc": 1742514
        }
        
    user_data = res["data"]["user"]
    created_at = user_data.get("createdAt", "2025-02-07T00:00:00Z")
    uptime_str = calculate_uptime(created_at)
    
    all_repos = user_data["repositories"]["nodes"]
    # Filter out bhume starter kit
    repos = [r for r in all_repos if "bhume" not in r["name"].lower()]
    
    total_repos = len(repos)
    contributed_count = user_data["repositoriesContributedTo"]["totalCount"]
    earned_stars = sum(r["stargazerCount"] for r in repos)
    followers_count = user_data["followers"]["totalCount"]
    
    # Commit history query across repos & forks
    repo_commit_query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100) {
                totalCount
                nodes {
                  additions
                  deletions
                  author {
                    user { login }
                    email
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    total_additions = 0
    total_deletions = 0
    matched_commits = 0
    
    for repo in repos:
        r_name = repo["name"]
        r_owner = repo["owner"]["login"]
        r_res = graphql_query(repo_commit_query, {"owner": r_owner, "name": r_name})
        if not r_res or "data" not in r_res or not r_res["data"] or not r_res["data"].get("repository"):
            continue
            
        ref = r_res["data"]["repository"].get("defaultBranchRef")
        if not ref or not ref.get("target"):
            continue
            
        nodes = ref["target"]["history"].get("nodes", [])
        for commit in nodes:
            author = commit.get("author") or {}
            author_user = author.get("user") or {}
            author_login = (author_user.get("login") or "").lower()
            author_email = (author.get("email") or "").lower()
            author_name = (author.get("name") or "").lower()
            
            is_me = (author_login == USERNAME.lower()) or \
                    ("tamatar" in author_email) or \
                    ("gourav" in author_email) or \
                    ("gourav" in author_name)
                    
            if is_me:
                total_additions += commit.get("additions", 0)
                total_deletions += commit.get("deletions", 0)
                matched_commits += 1
                
    net_loc = total_additions - total_deletions
    
    return {
        "uptime": uptime_str,
        "repos": total_repos,
        "contributed": contributed_count,
        "stars": earned_stars,
        "commits": matched_commits,
        "followers": followers_count,
        "additions": total_additions,
        "deletions": total_deletions,
        "total_loc": net_loc
    }

def format_fastfetch_block(stats):
    uptime = stats["uptime"]
    repos = f"{stats['repos']}"
    contributed = f"{stats['contributed']}"
    stars = f"{stats['stars']}"
    commits = f"{stats['commits']:,}"
    followers = f"{stats['followers']}"
    loc_total = f"{stats['total_loc']:,}"
    loc_add = f"{stats['additions']:,}"
    loc_del = f"{stats['deletions']:,}"

    block = f"""```text
gourav@tamatar-23 -------------------------------------------------------------
OS: .......................... Linux, Windows 11, Web
Uptime: ...................... {uptime}
Host: ........................ Full-Stack AI & Systems
IDE: ......................... VS Code, IntelliJ IDEA, Antigravity

Languages: ................... Python, TypeScript, JavaScript, Java, C++
Spoken: ...................... English, Hindi, Odia, Spanish
Hobbies: ..................... Monkeytype, Photography, PC Building

- Contact --------------------------------------------------------------------
Email: ....................... gouravkrishna23@gmail.com
Portfolio: ................... gouravk2304.vercel.app
GitHub: ...................... github.com/tamatar-23

- GitHub Stats ---------------------------------------------------------------
Repos: .... {repos.rjust(3)} {{Contributed: {contributed.rjust(3)}}} | Stars: ........... {stars.rjust(5)}
Commits: ................. {commits.rjust(5)} | Followers: ....... {followers.rjust(5)}
Lines of Code on GitHub: {loc_total.rjust(8)} ( {loc_add.rjust(8)}++, {loc_del.rjust(8)}-- )
------------------------------------------------------------------------------
```"""
    return block

def update_readme():
    stats = get_github_stats()
    print("Fetched Stats:", stats)
    fastfetch_block = format_fastfetch_block(stats)
    
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print("README.md not found!")
        return
        
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    start_marker = "<!--START_SECTION:fastfetch-->"
    end_marker = "<!--END_SECTION:fastfetch-->"
    
    if start_marker in content and end_marker in content:
        pattern = f"{re.escape(start_marker)}[\\s\\S]*?{re.escape(end_marker)}"
        new_section = f"{start_marker}\n{fastfetch_block}\n{end_marker}"
        updated_content = re.sub(pattern, new_section, content)
    else:
        updated_content = f"{start_marker}\n{fastfetch_block}\n{end_marker}\n\n" + content
        
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    print("Successfully updated README.md")

if __name__ == "__main__":
    update_readme()
