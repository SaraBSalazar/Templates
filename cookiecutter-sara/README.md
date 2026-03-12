# 🍪 Sara's Project Template

A Cookiecutter template that:
1. Creates a project folder with `Data/` and `Results/` subfolders
2. Writes a `.gitignore`
3. Creates the GitHub repo via API
4. Does `git init`, commits, and pushes — all in one command

---

## One-time setup

```bash
# 1. Install dependencies
pip install cookiecutter requests

# 2. Save your GitHub token permanently (add to ~/.zshrc or ~/.bashrc)
export GITHUB_TOKEN=your_token_here
```

To create a GitHub token:  
👉 https://github.com/settings/tokens → **Generate new token (classic)** → tick `repo`

---

## Every new project

```bash
cookiecutter path/to/cookiecutter-sara/
```

You'll be prompted for:
| Prompt | Default |
|---|---|
| `project_name` | my-project |
| `description` | A short description |
| `github_username` | SaraBSalazar |
| `github_email` | sara.barbosa.salazar@gmail.com |
| `private_repo` | no |

That's it. Your folder is created, pushed to GitHub, and ready to go. 🎉

---

## Resulting folder structure

```
my-project/
├── Data/          ← put raw/input data here
├── Results/       ← put outputs and reports here
├── .gitignore
└── README.md
```

---

## Also included: `git_init.py`

For existing folders (not using cookiecutter):

```bash
cd /path/to/existing-folder
python /path/to/cookiecutter-sara/git_init.py --name my-project
```
