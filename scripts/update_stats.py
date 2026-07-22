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
            "commits": 233,
            "followers": 13,
            "additions": 1780068,
            "deletions": 37263,
            "total_loc": 1742805
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

def generate_svg(stats, dark=True):
    bg_color = "#0d1117" if dark else "#ffffff"
    border_color = "#30363d" if dark else "#d0d7de"
    prompt_color = "#58a6ff" if dark else "#0969da"
    key_color = "#e5c07b" if dark else "#9a6a00"
    val_color = "#c9d1d9" if dark else "#24292f"
    dot_color = "#484f58" if dark else "#8c959f"
    add_color = "#3fb950" if dark else "#1a7f37"
    del_color = "#f85149" if dark else "#cf222e"
    accent_color = "#d2a8ff" if dark else "#8250df"
    sub_color = "#79c0ff" if dark else "#0550ae"

    uptime = stats["uptime"]
    repos = f"{stats['repos']}"
    contributed = f"{stats['contributed']}"
    stars = f"{stats['stars']}"
    commits = f"{stats['commits']:,}"
    followers = f"{stats['followers']}"
    loc_total = f"{stats['total_loc']:,}"
    loc_add = f"{stats['additions']:,}"
    loc_del = f"{stats['deletions']:,}"

    ascii_art = [
        "+-----------------------+",
        "|  TAMATAR-23 // CORE   |",
        "|  -------------------  |",
        "|  [AI / ML PIPELINES]  |",
        "|  [AGENTIC RAG]        |",
        "|  [QUANT SYSTEMS]      |",
        "+-----------------------+"
    ]

    ascii_svg_lines = []
    for i, line in enumerate(ascii_art):
        ascii_svg_lines.append(f'<text x="0" y="{i*22}" class="ascii">{line}</text>')
    ascii_content = "\n      ".join(ascii_svg_lines)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="850" height="340" viewBox="0 0 850 340" fill="none">
  <style>
    .bg {{ fill: {bg_color}; stroke: {border_color}; stroke-width: 1.5px; rx: 10px; }}
    .prompt {{ font: bold 14px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {prompt_color}; }}
    .bar {{ font: 14px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {dot_color}; }}
    .key {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {key_color}; }}
    .dot {{ font: 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {dot_color}; }}
    .val {{ font: 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {val_color}; }}
    .section {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {accent_color}; }}
    .add {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {add_color}; }}
    .del {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {del_color}; }}
    .accent {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {accent_color}; }}
    .sub {{ font: bold 13px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {sub_color}; }}
    .ascii {{ font: 12px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; fill: {prompt_color}; opacity: 0.85; }}
  </style>

  <rect width="850" height="340" class="bg" />

  <!-- Left ASCII Terminal Box -->
  <g transform="translate(30, 75)">
    {ascii_content}
  </g>

  <!-- Right Fastfetch Specs -->
  <g transform="translate(290, 35)">
    <!-- Header -->
    <text x="0" y="0" class="prompt">gourav@tamatar-23</text>
    <text x="145" y="0" class="bar">----------------------------------</text>

    <!-- Specs -->
    <text x="0" y="28" class="key">OS</text>
    <text x="25" y="28" class="dot">: ..........................</text>
    <text x="195" y="28" class="val">Linux, Windows 11, Web</text>

    <text x="0" y="52" class="key">Uptime</text>
    <text x="50" y="52" class="dot">: ......................</text>
    <text x="195" y="52" class="val">{uptime}</text>

    <text x="0" y="76" class="key">Host</text>
    <text x="35" y="76" class="dot">: ........................</text>
    <text x="195" y="76" class="val">Full-Stack AI &amp; Systems</text>

    <text x="0" y="100" class="key">IDE</text>
    <text x="30" y="100" class="dot">: .........................</text>
    <text x="195" y="100" class="val">VS Code, IntelliJ IDEA, Antigravity</text>

    <text x="0" y="132" class="key">Languages</text>
    <text x="75" y="132" class="dot">: ...................</text>
    <text x="195" y="132" class="val">Python, TypeScript, JS, Java, C++</text>

    <text x="0" y="156" class="key">Spoken</text>
    <text x="50" y="156" class="dot">: ......................</text>
    <text x="195" y="156" class="val">English, Hindi, Odia, Spanish</text>

    <text x="0" y="180" class="key">Hobbies</text>
    <text x="55" y="180" class="dot">: .....................</text>
    <text x="195" y="180" class="val">Monkeytype, Photography, PC Building</text>
  </g>

  <!-- Bottom Contact & GitHub Stats Section -->
  <g transform="translate(30, 245)">
    <!-- Contact Header -->
    <text x="0" y="0" class="section">- Contact</text>
    <text x="75" y="0" class="bar">-------------------------------------------------------------------------</text>

    <text x="0" y="22" class="key">Email</text>
    <text x="45" y="22" class="dot">:</text>
    <text x="55" y="22" class="val">gouravkrishna23@gmail.com</text>

    <text x="280" y="22" class="key">Portfolio</text>
    <text x="355" y="22" class="dot">:</text>
    <text x="365" y="22" class="val">gouravk2304.vercel.app</text>

    <text x="580" y="22" class="key">GitHub</text>
    <text x="635" y="22" class="dot">:</text>
    <text x="645" y="22" class="val">github.com/tamatar-23</text>

    <!-- GitHub Stats Header -->
    <text x="0" y="50" class="section">- GitHub Stats</text>
    <text x="110" y="50" class="bar">--------------------------------------------------------------------</text>

    <text x="0" y="72" class="key">Repos</text>
    <text x="45" y="72" class="dot">:</text>
    <text x="55" y="72" class="val">{repos}</text>
    <text x="80" y="72" class="accent">{{Contributed: {contributed}}}</text>
    
    <text x="210" y="72" class="bar">|</text>
    <text x="230" y="72" class="key">Stars</text>
    <text x="275" y="72" class="dot">:</text>
    <text x="285" y="72" class="val">{stars}</text>

    <text x="340" y="72" class="bar">|</text>
    <text x="360" y="72" class="key">Commits</text>
    <text x="425" y="72" class="dot">:</text>
    <text x="435" y="72" class="val">{commits}</text>

    <text x="510" y="72" class="bar">|</text>
    <text x="530" y="72" class="key">Followers</text>
    <text x="610" y="72" class="dot">:</text>
    <text x="620" y="72" class="val">{followers}</text>

    <text x="0" y="94" class="key">Lines of Code</text>
    <text x="110" y="94" class="dot">:</text>
    <text x="120" y="94" class="sub">{loc_total}</text>
    <text x="210" y="94" class="val">(</text>
    <text x="220" y="94" class="add">{loc_add}++</text>
    <text x="315" y="94" class="val">,</text>
    <text x="330" y="94" class="del">{loc_del}--</text>
    <text x="400" y="94" class="val">)</text>
  </g>
</svg>"""
    return svg

def update_readme():
    stats = get_github_stats()
    print("Fetched Stats:", stats)
    
    dark_svg = generate_svg(stats, dark=True)
    light_svg = generate_svg(stats, dark=False)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dark_path = os.path.join(base_dir, "dark_mode.svg")
    light_path = os.path.join(base_dir, "light_mode.svg")
    
    with open(dark_path, "w", encoding="utf-8") as f:
        f.write(dark_svg)
        
    with open(light_path, "w", encoding="utf-8") as f:
        f.write(light_svg)
        
    print(f"Successfully generated {dark_path} and {light_path}")

if __name__ == "__main__":
    update_readme()
