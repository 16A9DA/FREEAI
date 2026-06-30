# freeai

freeai is a coding assistant that runs entirely on your own computer. You describe a task in plain English, it writes a short plan, and once you approve, it carries out the work step by step: editing files, running commands, using git, and searching the web when needed.

The difference from most AI coding tools is where the work happens. freeai uses [Ollama](https://ollama.com) to run open source language models locally. After you download a model once, nothing you type and no file you open is sent to any company's servers. It keeps working with no internet connection and no API key.

## How it works

You run `freeai` inside a project folder. It greets you, shows which model is active, and waits for a task. You type something like "add input validation to the signup form". freeai turns that into a numbered plan and shows it to you. If the plan looks right, you approve it, and freeai starts working through the steps. For each step it decides which tool to use, runs it, reads the result, and moves on. You watch the whole thing happen in the terminal.

Nothing destructive runs without asking first. More on that under Safety below.

## Requirements

You need two things installed before freeai will run.

Ollama is the program that runs the AI models on your machine. freeai talks to it in the background at `localhost:11434`.

Python 3.10 or newer is needed to install and run freeai itself.

## Install

```bash
brew install ollama
git clone https://github.com/16A9DA/FREEAI.git
cd FREEAI
pip install -e .
```

On Linux or Windows, install Ollama from the instructions at [ollama.com](https://ollama.com) instead of using `brew`.

## First time setup

Start Ollama so the models have somewhere to run.

```bash
ollama serve
```

Download a model. A model is the actual AI that does the thinking. `qwen2.5-coder:7b` is a good starting point for coding work. The download is a few gigabytes and only happens once.

```bash
freeai model pull qwen2.5-coder:7b
```

After the download finishes, freeai asks whether to make it your default model. Say yes and you are ready to go.

## Running a task

From inside any project folder:

```bash
freeai
```

Type your task at the prompt. freeai shows a plan and asks you to approve it. Once you approve, it runs each step and streams its progress. When you are done, type `exit` or `quit`.

## Commands

Everything runs through the one `freeai` command. Running it with no arguments starts the assistant. Everything else is a subcommand. To see the full list at any time, run `freeai -help`.

```
freeai            Start the assistant. Shows the welcome screen and the task prompt.
freeai help       List every command.
freeai model      Download, list, switch, and remove local models.
freeai config     View and change settings.
freeai history    Show your past tasks.
freeai clear      Erase the saved session memory.
freeai index      Build or refresh the search index for the current project.
```

Managing models:

```bash
freeai model pull qwen2.5-coder:7b   # download a model
freeai model list                    # show installed models, with the active one marked
freeai model use qwen2.5-coder:7b    # set the active model
freeai model remove qwen2.5-coder:7b # delete a model from disk
```

If you ask to use a model you have not downloaded yet, freeai offers to download it for you. If you remove the model you were using, it tells you to pick a new one.

You can also switch models without leaving a session. Type `model qwen2.5-coder:7b` or `switch model to llama3` straight into the task prompt, and freeai changes the active model and keeps going. This is handy for comparing how two models handle the same task.

## What the agent can do

While working on a task, freeai has a set of tools it can reach for. You do not call these yourself. The model picks the right one for each step.

```
file        Read, write, create, delete, and search inside files.
shell       Run terminal commands.
git         Check status, view diffs, stage, commit, push, and read the log.
web         Search the web through DuckDuckGo. No account or API key required.
browser     Open a web page and pull out its main text.
```

## Safety

freeai stops and asks before doing anything it cannot easily undo. It will not delete files, overwrite an existing file, or run a dangerous shell command (such as `rm`, `dd`, or `mkfs`) until you confirm. Commits happen on their own, but a `git push` always asks first and shows you the remote and branch it is about to push to. The goal is simple: the assistant can move fast, but it never surprises you with a change you did not agree to.

## Pointing at specific files

When you want freeai to look at a particular file or folder, mention it with an `@` followed by a relative path.

```
fix the bug in @./src/models/user.py
use the schema from @../otherproject/schema.py
```

For a file, freeai reads it and includes a summary. For a folder, it includes the folder's file tree so the model knows what is there.

## Skills

Skills are written instructions that shape how freeai behaves. There are two kinds.

Project skills live in a file named `.freeai` in your project root, with one rule per line.

```
always use type hints
never modify files in the migrations folder
prefer async functions
```

freeai looks for this file starting from your current folder and walking upward. Whatever it finds gets added to every request, so the rules apply to that project automatically.

Global skills apply across every project. Each one is a folder under `~/.freecode/skills/` containing a file called `SKILL.md`. The first paragraph of that file is a short description. freeai reads only these descriptions to decide which skills are relevant to your current task, then loads the full text of the ones that match. The first time you run freeai, it creates the skills folder for you with two starter examples.

A skill file looks like this:

```
~/.freecode/skills/django-rest/SKILL.md

Skill for building Django REST Framework APIs. Covers serializers,
viewsets, and permissions.

Rules:
- Use ModelSerializer unless a field needs custom logic.
- Put business logic in services, not views.
- Always paginate list endpoints.
```

Keep that first paragraph specific, since it is the only part freeai reads when deciding whether the skill applies. When a skill is in use, freeai prints its name so you can see what is shaping its behavior.

## Assistance levels

freeai always runs at one of three assistance levels. The level decides how much code it writes, how much it explains itself, and how much it trims long tool output to save room. This is one setting rather than several knobs you have to learn.

```
low     Writes the least code, replies tersely, and trims output hard. Fastest and cheapest.
full    Balanced. The default, and what you get with no setup.
ultra   The most thorough. Verbose, careful, and keeps the most detail.
```

Set the level so it sticks:

```bash
freeai config --assistance ultra
```

Or change it for the current session by typing it at the prompt:

```
assistance low
```

The active level is shown on the welcome screen so you always know which mode you are in.

One caveat worth knowing. Part of the low level works by telling the model to write minimal code, and how well a model follows that kind of layered instruction varies. Smaller local models follow it less reliably than large ones. The other two parts, output trimming and reply style, are handled by freeai itself and behave the same no matter which model is active.

A rough guide: use `ultra` when you are working in an unfamiliar codebase or on something important, `full` for everyday work, and `low` once you trust the assistant on a given project and want to move faster.

## Automatic file search

On a large project, mentioning every relevant file by hand gets tedious. freeai can build a searchable index of your code so it finds the right files on its own.

The first time you give a task in a project that has not been indexed, freeai asks whether to build the index. If you say yes, it reads your files, splits them into chunks, and stores a mathematical fingerprint of each chunk on disk. From then on, before each task, it searches that index for the parts of your code most related to what you asked, includes them automatically, and prints which files it pulled in. If you say no, it carries on using `@` mentions only, exactly as before.

This feature needs a second, smaller model that turns text into those fingerprints. Download it once:

```bash
freeai model pull nomic-embed-text
```

You can build or refresh the index yourself at any time:

```bash
freeai index
```

The index respects your `.gitignore`, skips files that are not text, and only re-reads files that have changed since the last time. Like everything else, it stays on your machine. The fingerprints are stored under your home folder and never leave it.

## Settings

freeai keeps its settings in `~/.freecode/config.json`. This holds your active model, your assistance level, and other preferences. You can see and change them with `freeai config`.

```bash
freeai config                       # show current settings
freeai config --assistance full     # change the assistance level
freeai config --temperature 0.2     # change how adventurous the model is
```

## Privacy

freeai runs locally from start to finish. The models run inside Ollama on your own computer at `localhost:11434`, the search index is stored in your home folder, and your code, your tasks, and your queries stay on your machine. The only things that ever go out are the initial model downloads and any web searches you explicitly ask for.
