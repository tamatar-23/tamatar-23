import os
import json
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
            "commits": 245,
            "followers": 13,
            "additions": 1780940,
            "deletions": 38024,
            "total_loc": 1742916
        }
        
    user_data = res["data"]["user"]
    created_at = user_data.get("createdAt", "2025-02-07T00:00:00Z")
    uptime_str = calculate_uptime(created_at)
    
    all_repos = user_data["repositories"]["nodes"]
    repos = [r for r in all_repos if "bhume" not in r["name"].lower()]
    
    total_repos = len(repos)
    contributed_count = user_data["repositoriesContributedTo"]["totalCount"]
    earned_stars = sum(r["stargazerCount"] for r in repos)
    followers_count = user_data["followers"]["totalCount"]
    
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

def generate_svg(stats):
    bg_color = "#0d1117"
    border_color = "#30363d"
    prompt_color = "#58a6ff"
    dash_color = "#484f58"
    label_color = "#e5c07b"
    value_color = "#c9d1d9"
    contrib_color = "#d19a66"
    green_color = "#73daca"
    red_color = "#f7768e"

    uptime = stats["uptime"]
    repos = f"{stats['repos']}"
    contributed = f"{stats['contributed']}"
    stars = f"{stats['stars']}"
    commits = f"{stats['commits']:,}"
    followers = f"{stats['followers']}"
    loc_total = f"{stats['total_loc']:,}"
    loc_add = f"{stats['additions']:,}"
    loc_del = f"{stats['deletions']:,}"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="850" height="460" viewBox="0 0 850 460" fill="none">
  <style>
    .bg {{ fill: {bg_color}; stroke: {border_color}; stroke-width: 1px; rx: 8px; }}
    .prompt {{ font: bold 14px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {prompt_color}; }}
    .dash {{ font: 14px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {dash_color}; }}
    .label {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {label_color}; }}
    .dot {{ font: 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {dash_color}; }}
    .val {{ font: 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {value_color}; }}
    .contrib {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {contrib_color}; }}
    .green {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {green_color}; }}
    .red {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {red_color}; }}
  </style>

  <rect width="850" height="460" class="bg" />

  <g transform="translate(35, 30)">
    <!-- Header -->
    <text x="0" y="15" class="prompt">gourav@tamatar-23</text>
    <text x="145" y="15" class="dash">------------------------------------------------------------</text>

    <!-- Specs -->
    <text x="0" y="39" class="label">OS</text>
    <text x="25" y="39" class="dot">: ..........................</text>
    <text x="195" y="39" class="val">Linux, Windows 11, Web</text>

    <text x="0" y="59" class="label">Uptime</text>
    <text x="50" y="59" class="dot">: ......................</text>
    <text x="195" y="59" class="val">{uptime}</text>

    <text x="0" y="79" class="label">Host</text>
    <text x="35" y="79" class="dot">: ........................</text>
    <text x="195" y="79" class="val">Full-Stack AI &amp; Systems</text>

    <text x="0" y="99" class="label">IDE</text>
    <text x="30" y="99" class="dot">: .........................</text>
    <text x="195" y="99" class="val">VS Code, IntelliJ IDEA, Antigravity</text>

    <text x="0" y="127" class="label">Languages</text>
    <text x="75" y="127" class="dot">: ...................</text>
    <text x="195" y="127" class="val">Python, TypeScript, JavaScript, Java, C++</text>

    <text x="0" y="147" class="label">Spoken</text>
    <text x="50" y="147" class="dot">: ......................</text>
    <text x="195" y="147" class="val">English, Hindi, Odia, Spanish</text>

    <text x="0" y="167" class="label">Hobbies</text>
    <text x="55" y="167" class="dot">: .....................</text>
    <text x="195" y="167" class="val">Monkeytype, Photography, PC Building</text>

    <!-- Contact Header -->
    <text x="0" y="195" class="dash">-</text>
    <text x="12" y="195" class="val">Contact</text>
    <text x="70" y="195" class="dash">--------------------------------------------------------------</text>

    <text x="0" y="215" class="label">Email</text>
    <text x="45" y="215" class="dot">: .......................</text>
    <text x="195" y="215" class="val">gouravkrishna23@gmail.com</text>

    <text x="0" y="235" class="label">Portfolio</text>
    <text x="70" y="235" class="dot">: ...................</text>
    <text x="195" y="235" class="val">gouravk2304.vercel.app</text>

    <text x="0" y="255" class="label">GitHub</text>
    <text x="50" y="255" class="dot">: ......................</text>
    <text x="195" y="255" class="val">github.com/tamatar-23</text>

    <!-- GitHub Stats Header -->
    <text x="0" y="283" class="dash">-</text>
    <text x="12" y="283" class="val">GitHub Stats</text>
    <text x="105" y="283" class="dash">--------------------------------------------------</text>

    <text x="0" y="303" class="label">Repos</text>
    <text x="45" y="303" class="dot">: ....</text>
    <text x="80" y="303" class="val">{repos}</text>
    <text x="105" y="303" class="contrib">{{Contributed: {contributed}}}</text>

    <text x="220" y="303" class="dash">|</text>
    <text x="235" y="303" class="label">Stars</text>
    <text x="275" y="303" class="dot">: ...........</text>
    <text x="370" y="303" class="val">{stars}</text>

    <text x="0" y="323" class="label">Commits</text>
    <text x="60" y="323" class="dot">: .................</text>
    <text x="175" y="323" class="val">{commits}</text>

    <text x="220" y="323" class="dash">|</text>
    <text x="235" y="323" class="label">Followers</text>
    <text x="305" y="323" class="dot">: .......</text>
    <text x="370" y="323" class="val">{followers}</text>

    <text x="0" y="343" class="label">Lines of Code on GitHub</text>
    <text x="165" y="343" class="dot">:</text>
    <text x="175" y="343" class="val">{loc_total}</text>
    <text x="245" y="343" class="val">(</text>
    <text x="255" y="343" class="green">{loc_add}++</text>
    <text x="345" y="343" class="val">,</text>
    <text x="355" y="343" class="red">{loc_del}--</text>
    <text x="420" y="343" class="val">)</text>

    <text x="0" y="363" class="dash">----------------------------------------------------------------------</text>
  </g>
</svg>"""
    return svg

def update_readme():
    stats = get_github_stats()
    print("Fetched Stats:", stats)
    
    svg_content = generate_svg(stats)
    
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        base_dir = os.getcwd()
    card_path = os.path.join(base_dir, "card.svg")
    
    with open(card_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg_content)
        
    readme_path = os.path.join(base_dir, "README.md")
    readme_content = '<p align="center">\n  <img src="./card.svg?v=2.0" alt="Gourav\'s Fastfetch Profile" width="100%">\n</p>\n'
    with open(readme_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(readme_content)
        
    print(f"Successfully updated card.svg and README.md")

if __name__ == "__main__":
    update_readme()
