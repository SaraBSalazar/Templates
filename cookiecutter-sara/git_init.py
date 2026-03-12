#!/usr/bin/env python3
"""
git_init.py — Create a GitHub repo and initialise the current folder.

Usage (from inside the folder you want to push):
    python git_init.py --name my-project

Requires:
    pip install requests
    export GITHUB_TOKEN=your_token_here   ← set once in ~/.zshrc or ~/.bashrc
"""

import argparse
import os
import subprocess
import sys
import textwrap
import requests

DEFAULT_USERNAME = "SaraBSalazar"
DEFAULT_EMAIL    = "sara.barbosa.salazar@gmail.com"

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


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n❌  Command failed: {' '.join(cmd)}")
        sys.exit(1)


def create_github_repo(name, token, username, description, private):
    print(f"\n🌐  Creating GitHub repo '{name}'...")
    resp = requests.post(
        "https://api.github.com/user/repos",
        json={"name": name, "description": description, "private": private, "auto_init": False},
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    if resp.status_code == 201:
        print(f"✅  Repo created: {resp.json()['html_url']}")
        return resp.json()["ssh_url"]
    elif resp.status_code == 422:
        print("⚠️   Repo already exists on GitHub, continuing.")
        return f"git@github.com:{username}/{name}.git"
    else:
        print(f"❌  GitHub API error {resp.status_code}: {resp.json().get('message')}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create a GitHub repo and initialise the current folder.")
    parser.add_argument("--name",        required=True)
    parser.add_argument("--token",       default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--username",    default=DEFAULT_USERNAME)
    parser.add_argument("--email",       default=DEFAULT_EMAIL)
    parser.add_argument("--description", default="")
    parser.add_argument("--private",     action="store_true")
    args = parser.parse_args()

    if not args.token:
        print("❌  No GitHub token.\n"
              "    Set it: export GITHUB_TOKEN=your_token_here\n"
              "    Create one: https://github.com/settings/tokens")
        sys.exit(1)

    cwd = os.getcwd()
    print(f"\n📁  Working directory : {cwd}")
    print(f"📦  Project name      : {args.name}")

    remote_url = create_github_repo(args.name, args.token, args.username, args.description, args.private)

    print("\n🔧  Configuring git identity...")
    run(["git", "config", "--global", "user.name",  args.username])
    run(["git", "config", "--global", "user.email", args.email])

    print("🔧  Initialising local repo...")
    run(["git", "init"], cwd=cwd)

    if not os.path.exists(os.path.join(cwd, ".gitignore")):
        print("📝  Writing .gitignore...")
        with open(os.path.join(cwd, ".gitignore"), "w") as f:
            f.write(GITIGNORE_CONTENT)

    run(["git", "add", "."], cwd=cwd)
    run(["git", "commit", "-m", "Initiate git"], cwd=cwd)
    run(["git", "branch", "-M", "main"], cwd=cwd)

    subprocess.run(["git", "remote", "remove", "origin"], cwd=cwd, capture_output=True)
    run(["git", "remote", "add", "origin", remote_url], cwd=cwd)

    print("\n🚀  Pushing to GitHub...")
    run(["git", "push", "-u", "origin", "main"], cwd=cwd)

    print(f"\n🎉  Done! https://github.com/{args.username}/{args.name}\n")


if __name__ == "__main__":
    main()
