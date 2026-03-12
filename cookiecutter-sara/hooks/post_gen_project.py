#!/usr/bin/env python3
"""
Cookiecutter post-generation hook.
Runs automatically after the project folder is created.
Initialises git, creates the GitHub repo, and pushes everything.
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap

# ── Injected by cookiecutter ───────────────────────────────────────────────────
PROJECT_NAME    = "{{cookiecutter.project_name}}"
DESCRIPTION     = "{{cookiecutter.description}}"
PRIVATE         = "{{cookiecutter.private_repo}}" == "yes"

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

# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd):
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n❌  Command failed: {' '.join(cmd)}")
        sys.exit(1)


def prompt_git_credentials():
    print()
    username = input("    GitHub username: ").strip()
    if not username:
        print("❌  Username required.")
        sys.exit(1)

    email = input("    GitHub email: ").strip()
    if not email:
        print("❌  Email required.")
        sys.exit(1)

    answer = input(f"    GitHub owner (press Enter to use '{username}'): ").strip()
    owner = answer if answer else username

    return username, email, owner


def create_github_repo(token, owner):
    try:
        import requests
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
        import requests

    # Detect whether owner is a personal account or an org via the API
    check = requests.get(
        f"https://api.github.com/users/{owner}",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    is_org = check.status_code == 200 and check.json().get("type") == "Organization"
    url = f"https://api.github.com/orgs/{owner}/repos" if is_org else "https://api.github.com/user/repos"

    print(f"\n🌐  Creating repo '{PROJECT_NAME}' under '{owner}'...")
    resp = requests.post(
        url,
        json={"name": PROJECT_NAME, "description": DESCRIPTION, "private": PRIVATE, "auto_init": False},
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )

    if resp.status_code == 201:
        print(f"✅  Repo created: {resp.json()['html_url']}")
        return f"https://{token}@github.com/{owner}/{PROJECT_NAME}.git"
    elif resp.status_code == 422:
        print("⚠️   Repo already exists on GitHub, continuing.")
        return f"https://{token}@github.com/{owner}/{PROJECT_NAME}.git"
    else:
        print(f"❌  GitHub API error {resp.status_code}: {resp.json().get('message')}")
        sys.exit(1)


def personalise_notebook():
    nb_path = "project_template.ipynb"
    if not os.path.exists(nb_path):
        return
    print("📓  Personalising notebook...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    cwd = os.getcwd()
    for cell in nb["cells"]:
        src = cell.get("source", [])
        new_src = []
        for line in src:
            if "working_loc" in line and "=" in line:
                line = f"working_loc = '{cwd}'\n"
            if line.strip().startswith('title: ""'):
                line = line.replace('title: ""', f'title: "{PROJECT_NAME}"')
            new_src.append(line)
        cell["source"] = new_src
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("✅  Notebook ready as project_template.ipynb")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("\n🔑  GITHUB_TOKEN not set as environment variable.")
        token = input("    Enter your GitHub token: ").strip()
        if not token:
            print("❌  No token provided — skipping GitHub repo creation.")
            return

    git_username, git_email, github_owner = prompt_git_credentials()

    cwd = os.getcwd()
    print(f"\n📁  Project folder : {cwd}")

    personalise_notebook()

    with open(".gitignore", "w") as f:
        f.write(GITIGNORE_CONTENT)
    print("📝  .gitignore written.")

    remote_url = create_github_repo(token, github_owner)

    print("\n🔧  Setting up git...")
    run(["git", "config", "--global", "user.name",  git_username])
    run(["git", "config", "--global", "user.email", git_email])

    print("🧹  Checking for stray .git folders...")
    for root, dirs, files in os.walk("."):
        if ".git" in dirs:
            stray_git = os.path.join(root, ".git")
            shutil.rmtree(stray_git)
            print(f"    Removed: {stray_git}")
        dirs[:] = [d for d in dirs if d != ".git"]

    run(["git", "init"])
    run(["git", "add", "."])
    run(["git", "commit", "-m", "Initiate git"])
    run(["git", "branch", "-M", "main"])

    subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
    run(["git", "remote", "add", "origin", remote_url])

    print("\n🚀  Pushing to GitHub...")
    run(["git", "push", "-u", "origin", "main"])

    print(f"\n🎉  Done! https://github.com/{github_owner}/{PROJECT_NAME}\n")


if __name__ == "__main__":
    main()
