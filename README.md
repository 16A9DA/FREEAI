# FREEAI

## Overview

freeai is local AI coding assistant. Runs on your machine via Ollama and open source models. Type `freeai`, see welcome screen with active model, describe task, approve generated plan, watch it execute step by step. Has file ops, terminal commands, git, DuckDuckGo web search, browser scraping. Supports `@` mentions for files and folders by relative path. Per project `.freeai` skills file defines custom behaviour. Nothing leaves your machine after initial model download.

## Install

Requires Ollama and Python.

```bash
brew install ollama
git clone https://github.com/16A9DA/FREEAI.git
cd FREEAI
pip install -e .
```

Pull first model:

```bash
aimodel pull qwen2.5-coder:7b
```

## Usage

Start Ollama, then run freeai in any project:

```bash
freeai
```

Describe task. freeai generates plan, asks yes/no. Approve. Agent executes each step, calls tools, streams progress.

## Commands

All commands standalone.

```
freeai      main assistant. Welcome screen plus task loop.
aimodel     pull, list, use, remove local models.
aiconfig    show and set config values.
aihistory   show past tasks.
aiclear     wipe session memory.
```

## Tools

Agent calls these by name.

```
file        read, write, create, delete, search in files.
shell       run commands. Confirms on destructive keywords.
git         status, diff, add, commit, push, log. Push always confirms.
web         DuckDuckGo search. No API key.
browser     fetch page, extract main text.
```

## @ mentions

Reference files and folders by relative path inside any task.

```
fix the bug in @./src/models/user.py
use the schema from @../otherproject/schema.py
```

File mention sends summarised content. Folder mention sends file tree.

## Skills

Two kinds.

Project skills. A `.freeai` file in project root. One rule per line. Example.

```
always use type hints
never modify files in the migrations folder
prefer async functions
```

freeai walks up from cwd, finds `.freeai`, prepends rules to every model prompt.

Global skills. Folders under `~/.freecode/skills/`, each with a `SKILL.md`. First paragraph is the description the model uses to decide relevance. Rest is rules or workflow. Example path `~/.freecode/skills/django-rest/SKILL.md`. Global by design. Same skill applies across every project.

On first run freeai creates `~/.freecode/skills/` with a `general-coding` example skill. Add your own by creating one folder per skill, each holding a `SKILL.md`.

Format. The first paragraph is the description. Keep it specific, since the model reads only descriptions to pick relevant skills for a task. Put the rules or workflow after a blank line in plain markdown.

```
~/.freecode/skills/django-rest/SKILL.md

Skill for building Django REST Framework APIs. Covers serializers,
viewsets, and permissions.

Rules:
- Use ModelSerializer unless a field needs custom logic.
- Put business logic in services, not views.
- Always paginate list endpoints.
```

Before each task freeai matches its description against your skills, loads the full text of any that apply, prepends it to the planner and agent prompts, and prints which skills are active.

## Assistance levels

An always-on setting that controls how much help freeai gives, from terse and minimal to thorough. Three levels.

```
low     Least code, terse replies, aggressive tool-output compression. Fastest, cheapest.
full    Balanced. Moderate compression, normal replies. Default.
ultra   Highest fidelity. Verbose, careful work, minimal compression.
```

Each level sets three things. code_minimalism force includes a minimal-code skill so the model writes less. compression_aggressiveness controls how hard tool output is shortened before it goes back to the model. response_style sets how the model talks.

Set it persistently.

```bash
aiconfig --assistance ultra
```

Or change it for the session from the freeai prompt.

```
assistance low
```

The active level shows on the welcome screen.

## Config

Stored at `~/.freecode/config.json`. Holds active model, assistance level, and settings.

## Privacy

Local only. Ollama serves models at `localhost:11434`. No data leaves the machine except the initial model download and explicit DuckDuckGo search queries.
