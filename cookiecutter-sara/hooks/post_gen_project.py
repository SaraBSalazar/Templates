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
GIT_USERNAME    = "{{cookiecutter.github_username}}"
GIT_EMAIL       = "{{cookiecutter.github_email}}"
GITHUB_OWNER    = "{{cookiecutter.github_owner}}"
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


def create_github_repo(token):
    try:
        import requests
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
        import requests

    PERSONAL_ACCOUNT = "SaraBSalazar"
    is_org = GITHUB_OWNER != PERSONAL_ACCOUNT
    url = f"https://api.github.com/orgs/{GITHUB_OWNER}/repos" if is_org else "https://api.github.com/user/repos"

    print(f"\n🌐  Creating repo '{PROJECT_NAME}' under '{GITHUB_OWNER}'...")
    resp = requests.post(
        url,
        json={"name": PROJECT_NAME, "description": DESCRIPTION, "private": PRIVATE, "auto_init": False},
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )

    if resp.status_code == 201:
        print(f"✅  Repo created: {resp.json()['html_url']}")
        return resp.json()["ssh_url"]
    elif resp.status_code == 422:
        print("⚠️   Repo already exists on GitHub, continuing.")
        return f"git@github.com:{GITHUB_OWNER}/{PROJECT_NAME}.git"
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
    new_nb_path = f"{PROJECT_NAME}.ipynb"
    with open(new_nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    os.remove(nb_path)
    print(f"✅  Notebook saved as {new_nb_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("\n🔑  GITHUB_TOKEN not set as environment variable.")
        token = input("    Enter your GitHub token: ").strip()
        if not token:
            print("❌  No token provided — skipping GitHub repo creation.")
            return

    cwd = os.getcwd()
    print(f"\n📁  Project folder : {cwd}")

    personalise_notebook()

    with open(".gitignore", "w") as f:
        f.write(GITIGNORE_CONTENT)
    print("📝  .gitignore written.")

    remote_url = create_github_repo(token)

    print("\n🔧  Setting up git...")
    run(["git", "config", "--global", "user.name",  GIT_USERNAME])
    run(["git", "config", "--global", "user.email", GIT_EMAIL])

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

    print(f"\n🎉  Done! https://github.com/{GITHUB_OWNER}/{PROJECT_NAME}\n")


if __name__ == "__main__":
    main()
