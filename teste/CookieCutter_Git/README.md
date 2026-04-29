# 🍪 ADA's Project Template

A Cookiecutter template that, in a single command:
1. Creates a project folder with `Data/`, `Notebooks/`, and `Results/` subfolders
2. Writes a `.gitignore`
3. Creates the GitHub repo via API
4. Does `git init`, commits, and pushes
5. Opens a new eLabFTW experiment from the **Advanced Data Analysis Facility** template

---

## One-time setup

```bash
# 1. Install dependencies
pip install cookiecutter requests

# 2. Save your GitHub token (add to ~/.zshrc or ~/.bashrc)
export GITHUB_TOKEN=your_github_token_here

# 3. Save your eLabFTW API key (add to ~/.zshrc or ~/.bashrc)
export ELAB_TOKEN=your_elabftw_api_key_here
```

**GitHub token:** https://github.com/settings/tokens → Generate new token (classic) → tick `repo`

**eLabFTW API key:** https://labbook.gimm.pt/profile.php → API keys → Generate new key (read + write)

---

## Every new project

```bash
cookiecutter path/to/CookieCutter_Git/
```

You'll be prompted for:
| Prompt | Default |
|---|---|
| `project_name` | my-project |
| `description` | A short description |
| `github_username` | _(your GitHub username)_ |
| `github_email` | _(your GitHub email)_ |
| `private_repo` | no |

Then interactively for the eLabFTW experiment:
| Prompt | Notes |
|---|---|
| Experiment title | Defaults to project name |
| Category | Numbered list from your eLabFTW |
| Status | Numbered list from your eLabFTW |
| Tags | Comma-separated, e.g. `RNA-seq,mouse,2026` |

That's it. Folder created, pushed to GitHub, experiment live in eLabFTW. 🎉

---

## Resulting folder structure

```
my-project/
├── Data/          ← raw/input data
├── Notebooks/     ← Jupyter / Quarto notebooks
│   └── project_template.ipynb
├── Results/       ← outputs and reports
├── .gitignore
└── README.md
```

---

## Also included: `git_init.py`

For existing folders (no cookiecutter needed):

```bash
cd /path/to/existing-folder
python /path/to/CookieCutter_Git/git_init.py --name my-project
```
