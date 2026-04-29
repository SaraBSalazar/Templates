#!/usr/bin/env python3
"""
Cookiecutter post-generation hook.
1. Initialises git and creates the GitHub repo
2. Creates a new eLabFTW experiment from the Agendo_Project template
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from datetime import date

# ── Injected by cookiecutter ──────────────────────────────────────────────────
PROJECT_NAME = "{{cookiecutter.project_name}}"
DESCRIPTION  = "{{cookiecutter.description}}"
PRIVATE      = "{{cookiecutter.private_repo}}" == "yes"
GIT_USERNAME = "{{cookiecutter.github_username}}"
GIT_EMAIL    = "{{cookiecutter.github_email}}"

ELAB_BASE_URL      = "https://labbook.gimm.pt/api/v2"
ELAB_TEMPLATE_NAME = "Agendo_Project"  # id 436 — provides extra fields structure
ELAB_IGC_TEMPLATE_ID = 316  # "Experiments Template for IGC" — provides body text

# Body HTML from the IGC template (id 316)
ELAB_BODY_HTML = """<h2><span style="font-size:14pt;"><strong>Hypothesis or Goal</strong></span></h2>
<p>{Brief statement of purpose}</p>
<p>&nbsp;</p>
<h2><span style="font-size:14pt;"><strong>Procedure</strong></span></h2>
<p>{this section should include dates of individual steps if it is a multi-day experiment}<br>
{include protocols, calculations, reagents, equipment and catalog numbers for key reagents - ALL THIS CAN BE LINKED TO DATABASES, if they have been created in eLab}</p>
<p>&nbsp;</p>
<h2><span style="font-size:14pt;"><strong>Observations/Results</strong></span></h2>
<p>{All that happens - planned or unplanned}</p>
<p>&nbsp;</p>
<h2><span style="font-size:14pt;"><strong>Data storage location</strong></span></h2>
<p><span style="font-size:10pt;">data must be stored at the IGC server (<strong>files1)</strong> - use &quot;Extra Fields&quot; section to mention where your data is stored</span></p>
<p>&nbsp;</p>
<h2><span style="font-size:14pt;"><strong>Discussion and conclusion</strong></span></h2>"""

GITIGNORE_CONTENT = textwrap.dedent("""\
    # =========================
    # Dependencies
    # =========================
    node_modules/
    venv/
    env/
    .venv/

    # =========================
    # Environment Variables
    # =========================
    .env
    .env.*
    *.pem
    *.key

    # =========================
    # Build Outputs
    # =========================
    dist/
    build/
    out/
    coverage/

    # =========================
    # Logs
    # =========================
    *.log
    npm-debug.log*
    yarn-debug.log*
    yarn-error.log*

    # =========================
    # OS Files
    # =========================
    .DS_Store
    Thumbs.db
    Desktop.ini

    # =========================
    # VS Code
    # =========================
    .vscode/

    # =========================
    # Python
    # =========================
    __pycache__/
    *.pyc

    # =========================
    # Misc
    # =========================
    *.swp
    *.swo
    *.tmp
""")

# ── Utilities ─────────────────────────────────────────────────────────────────

def ensure_requests():
    try:
        import requests
        return requests
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
        import requests
        return requests


def run(cmd):
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n❌  Command failed: {' '.join(cmd)}")
        sys.exit(1)


def pick(label, options, id_key, name_key):
    print(f"\n    Available {label}:")
    for i, opt in enumerate(options, 1):
        print(f"      {i}) {opt[name_key]}")
    while True:
        raw = input(f"    Choose {label} (1-{len(options)}): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            chosen = options[int(raw) - 1]
            print(f"    ✔  {chosen[name_key]}")
            return chosen[id_key]
        print(f"    Please enter a number between 1 and {len(options)}.")


# ── GitHub ────────────────────────────────────────────────────────────────────

def prompt_git_credentials():
    username = GIT_USERNAME.strip()
    email    = GIT_EMAIL.strip()
    if not username:
        print()
        username = input("    GitHub username: ").strip()
        if not username:
            print("❌  Username required.")
            sys.exit(1)
    if not email:
        email = input("    GitHub email: ").strip()
        if not email:
            print("❌  Email required.")
            sys.exit(1)
    answer = input(f"    GitHub owner (press Enter to use '{username}'): ").strip()
    owner = answer if answer else username
    return username, email, owner


def create_github_repo(req, token, owner):
    check = req.get(
        f"https://api.github.com/users/{owner}",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    is_org = check.status_code == 200 and check.json().get("type") == "Organization"
    url = f"https://api.github.com/orgs/{owner}/repos" if is_org else "https://api.github.com/user/repos"

    print(f"\n🌐  Creating GitHub repo '{PROJECT_NAME}' under '{owner}'...")
    resp = req.post(
        url,
        json={"name": PROJECT_NAME, "description": DESCRIPTION, "private": PRIVATE, "auto_init": False},
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    if resp.status_code == 201:
        print(f"✅  Repo created: {resp.json()['html_url']}")
    elif resp.status_code == 422:
        print("⚠️   Repo already exists on GitHub, continuing.")
    else:
        print(f"❌  GitHub API error {resp.status_code}: {resp.json().get('message')}")
        sys.exit(1)
    repo_slug = PROJECT_NAME.replace(" ", "-")
    return f"https://{token}@github.com/{owner}/{repo_slug}.git"


# ── eLabFTW ───────────────────────────────────────────────────────────────────

def elab_hdrs(token):
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def find_template_id(req, token):
    resp = req.get(f"{ELAB_BASE_URL}/experiments_templates", headers=elab_hdrs(token))
    if resp.status_code != 200:
        print(f"⚠️   Could not fetch templates (HTTP {resp.status_code}).")
        return None
    templates = resp.json()
    for t in templates:
        if t.get("title", "").strip() == ELAB_TEMPLATE_NAME:
            print(f"    ✔  Template: {ELAB_TEMPLATE_NAME}")
            return t["id"]
    print(f"\n⚠️   Template '{ELAB_TEMPLATE_NAME}' not found. Pick one:")
    if not templates:
        print("    No templates available — blank experiment will be created.")
        return None
    return pick("template", templates, "id", "title")


def get_team_users(req, token):
    """Fetch team members to offer as Assigned To options."""
    resp = req.get(f"{ELAB_BASE_URL}/users", headers=elab_hdrs(token))
    if resp.status_code == 200:
        return resp.json()
    return []


def create_elab_experiment(req, token, github_repo_url, working_dir):
    print("\n📓  Setting up eLabFTW experiment...")

    template_id = find_template_id(req, token)

    # Status — try endpoint, fall back to known statuses on this instance
    statuses = []
    stat_resp = req.get(f"{ELAB_BASE_URL}/experiments_status", headers=elab_hdrs(token))
    if stat_resp.status_code == 200:
        try:
            statuses = stat_resp.json()
        except Exception:
            statuses = []
    if not statuses:
        statuses = [
            {"id": 196, "title": "Backlog"},
            {"id": 194, "title": "Running"},
            {"id": 195, "title": "Closed"},
            {"id": 316, "title": "Consulting"},
        ]

    # Categories — hardcoded (experiments_categories endpoint not available in this eLabFTW version)
    categories = [
        {"id": 92,  "title": "Statistical Data Analysis"},
        {"id": 93,  "title": "Transcriptomics"},
        {"id": 97,  "title": "Proteomics"},
        {"id": 98,  "title": "Metabolomics"},
        {"id": 100, "title": "Other Bioinformatic Analysis"},
    ]

    # Team users for Assigned To
    users = get_team_users(req, token)

    # ── Prompts ───────────────────────────────────────────────────────────────
    print()
    raw_title = input(f"    Experiment title (Enter = '{PROJECT_NAME}'): ").strip()
    title = raw_title if raw_title else PROJECT_NAME

    status_id   = pick("status",   statuses,   "id", "title") if statuses   else None
    category_id = pick("category", categories, "id", "title") if categories else None

    raw_tags = input("    Tags (comma-separated, e.g. RNA-seq,mouse,2026 — or Enter to skip): ").strip()
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    print("\n    📋  Project metadata:")
    user       = input("    User (main contact): ").strip()
    lab        = input("    Lab / Facility: ").strip()
    agendo_ref = input("    Agendo Reference: ").strip()

    # Assigned To — type a name, search for match
    assigned_to_userid = None
    if users:
        raw_name = input("    Assigned To (type a name, Enter to skip): ").strip().lower()
        if raw_name:
            matches = [u for u in users if raw_name in u.get("fullname", "").lower()]
            if len(matches) == 1:
                assigned_to_userid = matches[0]["userid"]
                print(f"    ✔  Assigned to: {matches[0]['fullname']}")
            elif len(matches) > 1:
                print(f"    Multiple matches:")
                for i, u in enumerate(matches, 1):
                    print(f"      {i}) {u.get('fullname', '?')}")
                while True:
                    raw = input(f"    Choose (1-{len(matches)}): ").strip()
                    if raw.isdigit() and 1 <= int(raw) <= len(matches):
                        assigned_to_userid = matches[int(raw) - 1]["userid"]
                        print(f"    ✔  Assigned to: {matches[int(raw)-1]['fullname']}")
                        break
                    print(f"    Please enter a number between 1 and {len(matches)}.")
            else:
                print(f"    ⚠️   No user found matching '{raw_name}' — Assigned To left blank.")

    # ── Auto-filled fields ────────────────────────────────────────────────────
    today         = date.today().isoformat()   # YYYY-MM-DD
    data_location = working_dir                 # pwd of the new project folder

    # ── Build extra_fields metadata ───────────────────────────────────────────
    extra_fields = {
        "Project Type": {"type": "select", "value": "Project"},
        "Starting Date": {"type": "date", "value": today},
        "Github": {"type": "url", "value": github_repo_url},
        "Data Location": {"type": "text", "value": data_location},
        "Analysis location": {"type": "text", "value": data_location},
    }
    if user:
        extra_fields["User"] = {"type": "text", "value": user}
    if lab:
        extra_fields["Lab"] = {"type": "text", "value": lab}
    if agendo_ref:
        extra_fields["Agendo Reference"] = {"type": "text", "value": agendo_ref}
    if assigned_to_userid:
        extra_fields["Assigned To"] = {"type": "users", "value": assigned_to_userid}

    # ── Create experiment (POST) ──────────────────────────────────────────────
    post_body = {}
    if template_id:
        post_body["template"] = template_id

    print(f"\n🧪  Creating experiment '{title}'...")
    create_resp = req.post(
        f"{ELAB_BASE_URL}/experiments",
        headers=elab_hdrs(token),
        json=post_body,
    )
    if create_resp.status_code != 201:
        print(f"❌  Failed to create experiment (HTTP {create_resp.status_code}): {create_resp.text}")
        return

    location = create_resp.headers.get("location", "")
    exp_id = location.rstrip("/").split("/")[-1]
    if not exp_id.isdigit():
        print(f"⚠️   Could not parse experiment ID from: {location}")
        return

    # ── PATCH title + status + metadata ──────────────────────────────────────
    # Build metadata JSON string — eLabFTW stores metadata as a JSON string in the DB
    metadata_obj = {
        "elabftw": {
            "extra_fields_groups": [
                {"id": 1, "name": "Metadata"},
                {"id": 2, "name": "Project Info"}
            ]
        },
        "extra_fields": extra_fields
    }

    patch_body = {
        "title": title,
        "body": ELAB_BODY_HTML,
        "metadata": json.dumps(metadata_obj),
    }
    if status_id:
        patch_body["status"] = status_id
    if category_id:
        patch_body["category"] = category_id  # older eLabFTW uses "status" not "status_id"

    patch_resp = req.patch(
        f"{ELAB_BASE_URL}/experiments/{exp_id}",
        headers=elab_hdrs(token),
        json=patch_body,
    )
    if patch_resp.status_code not in (200, 204):
        print(f"⚠️   Experiment created but patch failed (HTTP {patch_resp.status_code}): {patch_resp.text}")

    # ── Tags ──────────────────────────────────────────────────────────────────
    for tag in tags:
        req.post(
            f"{ELAB_BASE_URL}/experiments/{exp_id}/tags",
            headers=elab_hdrs(token),
            json={"tag": tag},
        )

    exp_url = f"https://labbook.gimm.pt/experiments.php?mode=view&id={exp_id}"
    print(f"✅  Experiment ready: {exp_url}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    req = ensure_requests()
    github_repo_url = ""

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("\n🔑  GITHUB_TOKEN not set.")
        github_token = input("    Enter your GitHub token: ").strip()

    git_username, git_email, github_owner = prompt_git_credentials()
    cwd = os.getcwd()
    print(f"\n📁  Project folder : {cwd}")

    with open(".gitignore", "w") as f:
        f.write(GITIGNORE_CONTENT)
    print("📝  .gitignore written.")

    if github_token:
        remote_url = create_github_repo(req, github_token, github_owner)
        repo_slug = PROJECT_NAME.replace(" ", "-")
        github_repo_url = f"https://github.com/{github_owner}/{repo_slug}"

        print("🧹  Removing any stray .git folders...")
        for root, dirs, _ in os.walk("."):
            if ".git" in dirs:
                stray = os.path.join(root, ".git")
                shutil.rmtree(stray)
                print(f"    Removed: {stray}")
            dirs[:] = [d for d in dirs if d != ".git"]

        run(["git", "init"])

        print("\n🔧  Setting up git...")
        run(["git", "config", "--local", "user.name",  git_username])
        run(["git", "config", "--local", "user.email", git_email])
        run(["git", "add", "."])
        run(["git", "commit", "-m", "Initiate git"])
        run(["git", "branch", "-M", "main"])
        subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
        run(["git", "remote", "add", "origin", remote_url])
        print("\n🚀  Pushing to GitHub...")
        run(["git", "push", "-u", "origin", "main"])
        print(f"✅  {github_repo_url}")

    # ── eLabFTW ───────────────────────────────────────────────────────────────
    elab_token = os.getenv("ELAB_TOKEN")
    if not elab_token:
        print("\n🔑  ELAB_TOKEN not set.")
        elab_token = input("    Enter your eLabFTW API key: ").strip()

    if elab_token:
        create_elab_experiment(req, elab_token, github_repo_url, cwd)
    else:
        print("⚠️   No eLabFTW token — skipping experiment creation.")

    print(f"\n🎉  All done! Project '{PROJECT_NAME}' is ready.\n")


if __name__ == "__main__":
    main()
