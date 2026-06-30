# freeai build plan

## Project overview

freeai is a local AI coding assistant that runs entirely on your machine
using Ollama and open source models. The user types `freeai` in the
terminal, sees a welcome screen with the active model name, describes a
task, receives a plan to approve, then freeai executes it step by step.
It has access to file operations, terminal commands, git, web search via
DuckDuckGo, and browser scraping. It supports @ mentions for referencing
files and folders using relative paths. Each project can have a .freeai
skills file that defines custom behaviour for that codebase. All commands
are standalone: freeai, aimodel, aiconfig, aihistory, aiclear.

## Project structure

The package is called freecode and lives in a freecode/ subfolder.
Inside it: main.py handles the freeai entry point and welcome screen.
agent.py contains the core agentic loop. ollama_client.py handles all
communication with the local Ollama REST API at localhost:11434.
config.py reads and writes ~/.freecode/config.json which stores the
active model name and settings. planner.py generates plan.md from a
task. parser.py handles @ mention resolution and skill file loading.
history.py powers the aihistory command. clear.py powers aiclear.
model_manager.py powers aimodel. The tools/ subfolder contains
file_tools.py, shell_tool.py, git_tool.py, web_tool.py, and
browser_tool.py. pyproject.toml registers all five terminal commands
as entry points.

## Day 1 — skeleton and config

Create the full folder structure including freecode/, freecode/tools/,
and all empty __init__.py files. Write pyproject.toml with project
metadata, dependencies (typer, rich, httpx, duckduckgo-search,
beautifulsoup4, gitpython), and all five entry points mapping freeai to
freecode.main:app, aimodel to freecode.model_manager:app, aiconfig to
freecode.config:app, aihistory to freecode.history:app, and aiclear to
freecode.clear:app. Write config.py with two functions: load_config()
which reads ~/.freecode/config.json and returns a dict with defaults if
the file does not exist, and save_config(data) which writes back to that
file creating the directory if needed. Install the package in editable
mode with pip install -e . and confirm that typing freeai in the terminal
does not error.

## Day 2 — Ollama client and welcome screen

Write ollama_client.py with three functions. check_running() sends a GET
to localhost:11434 and returns True if Ollama is up. list_models() calls
GET /api/tags and returns the list of pulled model names. chat(model,
messages, stream=True) sends a POST to /api/chat with the model name and
message history and streams back the response token by token using httpx.
Write main.py with the freeai Typer app. On startup it calls
check_running() and exits with a clear error if Ollama is not running.
It loads config, gets the active model, and prints the ASCII art welcome
screen using Rich showing the FREEAI logo in plain white and the active
model name below it. If no model is set it tells the user to run aimodel
first. After the welcome screen it drops into the main task input loop.

## Day 3 — plan generation and approval flow

Write planner.py with a function generate_plan(task, model) that sends
the user's task to Ollama with a system prompt instructing it to respond
with a numbered step-by-step plan only, no code, no explanations. The
function returns the plan as a list of strings and also writes it to
plan.md in the current working directory. In main.py, after the user
types a task, call generate_plan and display the plan as a Rich numbered
list. Then prompt the user with a yes/no confirmation. If they say no,
ask them to refine the task. If they say yes, pass the approved plan to
the agent loop in agent.py. The agent loop in agent.py iterates over
each step, sends it to the model as a tool-use prompt, parses the
model's response for tool calls, executes them, feeds results back, and
prints progress to the terminal using Rich.

## Day 4 — file tools

Write tools/file_tools.py with five functions. read_file(path) reads a
file and returns its content as a string, resolving the path relative to
cwd. write_file(path, content) writes content to a file, creating
directories if needed, and always asks for confirmation if the file
already exists since overwriting is destructive. create_file(path,
content) creates a new file and errors if it already exists. delete_file
(path) always asks for confirmation before deleting. search_in_files
(query, directory) walks the cwd recursively and returns a list of
matches as file path plus line number plus line content, displayed as a
Rich table. Register these as tools in agent.py so the model can call
them by name with arguments parsed from its JSON response.

## Day 5 — shell tool with safety

Write tools/shell_tool.py with a function run_command(command) that uses
subprocess to run a shell command in the current working directory and
captures stdout and stderr. Before running, check if the command contains
any destructive keywords: rm, rmdir, del, format, mkfs, dd, truncate,
chmod 777, sudo rm. If any match, print the command in red using Rich and
ask the user to confirm before proceeding. For all other commands run
immediately and stream the output to the terminal line by line. Return
the exit code, stdout, and stderr as a dict so the agent can feed the
result back to the model. Register this as a tool in agent.py.

## Day 6 — git tool

Write tools/git_tool.py using the gitpython library. git_status() returns
the current repo status as a formatted string. git_diff(filepath) returns
the diff for a specific file or the whole repo. git_add(paths) stages the
given files, defaulting to all changed files if paths is empty.
git_commit(message) stages all changes and commits with the given message
automatically without asking. git_push() always asks the user to confirm
before pushing, prints the remote and branch clearly, then pushes only
if the user types yes. git_log(n) returns the last n commits as a Rich
table showing hash, author, date, and message. Register all of these as
tools in agent.py.

## Day 7 — web search and browser tool

Write tools/web_tool.py using the duckduckgo-search library. web_search
(query, max_results=5) runs a DuckDuckGo text search and returns a list
of dicts with title, url, and snippet, displayed as a Rich table. This
requires no API key and sends no data to any third party beyond the
search query itself. Write tools/browser_tool.py with fetch_page(url)
that uses httpx to GET the page and beautifulsoup4 to extract the main
text content, stripping scripts, styles, and navigation. Return the
cleaned text truncated to 4000 characters so it fits in the model
context. Register both as tools in agent.py.

## Day 8 — @ mention parser

Write parser.py with a function parse_mentions(text) that scans the
user's input for patterns starting with @. Each mention is treated as a
relative file or folder path resolved from the current working directory,
supporting paths like @../otherproject/file.py or @./src/models/. For
files it reads the content and sends it to the model with a system prompt
asking it to summarise the file and identify the most relevant parts for
the current task. For folders it lists all files recursively up to two
levels deep and sends the file tree as context. The resolved content
replaces or augments the original mention in the prompt before it is sent
to Ollama. Call parse_mentions inside the main task loop in main.py
before the prompt is passed to the planner or agent.

## Day 9 — skills system

Define the skills file as .freeai in the project root directory. It is a
plain text file where each line is either a rule like always use type
hints, a constraint like never modify files in the migrations folder, or
a preference like prefer async functions. Write the load_skills()
function in parser.py that walks up from cwd looking for a .freeai file
and returns its contents as a string. If found, prepend the skills
content to every system prompt sent to Ollama so the model follows the
project-specific rules automatically. In main.py on startup, check if a
.freeai file exists in cwd and show a small Rich notice telling the user
which skills are active. Document the .freeai format clearly in the
README so users know how to write their own.

## Day 10 — remaining commands

Write model_manager.py as a Typer app with four subcommands: list shows
all locally pulled models as a Rich table with name and size, pull
prompts for a model name then streams the download progress from the
Ollama pull API endpoint, use sets the active model in config.json and
confirms the change, remove calls the Ollama delete endpoint and confirms
before doing so. Write aiconfig.py that prints the current config as a
Rich table and accepts optional flags to set values like model,
temperature, and context window size. Write aihistory.py that reads
~/.freecode/history.json and displays past tasks as a Rich table with
timestamp, task summary, and status. Write aiclear.py that wipes the
current session memory and optionally clears history with a confirmation
prompt.

## Day 11 — polish

Go through every command and tool and make sure Rich is used consistently
throughout. The welcome screen should be clean with no clutter. Errors
should print in red with a clear message and a suggested fix. Tool
execution should show a spinner while running and a tick or cross when
done. The plan should be displayed as a numbered list in a panel. Git
operations should show a summary table. Search results should use a clean
table with truncated snippets. All confirmation prompts should be yes/no
with the default clearly shown. Streaming model output should print
tokens as they arrive without buffering. Test every command manually end
to end.

## Day 12 — README and final test

Write README.md covering installation (brew install ollama, git clone,
pip install -e .), pulling a first model with aimodel, running freeai,
the .freeai skills file format, the @ mention syntax with examples,
all five commands with usage, the full tool list, and privacy notes
confirming nothing leaves the machine after the initial model download.
Run a full end-to-end test: pull qwen2.5-coder:7b, open a real Python
project, write a .freeai file, type a real multi-step coding task using
an @ mention to a file outside the folder, approve the plan, watch it
execute, commit the result with aimodel, verify plan.md was written.

## Day 13 — SKILL.md discovery system

Skills live only globally at ~/.freecode/skills/, never per-project.
Each skill is its own folder containing a SKILL.md file, exactly like
Claude's skill format. The file starts with a short description line
explaining what the skill is for, followed by the actual instructions,
rules, or workflow steps in plain markdown. Example folders would be
~/.freecode/skills/django-rest/SKILL.md or
~/.freecode/skills/python-testing/SKILL.md.

Write skills.py with a function list_skills() that walks
~/.freecode/skills/ one level deep, reads the first paragraph of each
SKILL.md as its description, and returns a list of dicts with name,
path, and description. Write a function match_skills(task, available_skills,
model) that sends the task plus all skill descriptions to the model with
a system prompt asking it to return only the names of skills that are
relevant to this task, or none if no skill applies. This is a cheap fast
call using short text only, not the full skill content. Write
load_skill_content(skill_name) that reads the full SKILL.md for a
matched skill. In main.py, before generating a plan, call list_skills,
then match_skills, then for every matched skill load its full content
and prepend it to the system prompt sent to the planner and agent. Print
a small Rich notice showing which skills were activated for this task so
the user always knows what is influencing the model's behaviour.

## Day 14 — skills folder bootstrap and management

On first run of freeai, check if ~/.freecode/skills/ exists. If not,
create it and write one example skill folder called
~/.freecode/skills/general-coding/SKILL.md containing a basic example
showing the expected format, so the user has a working reference to copy
from. Document in the README exactly how to write a new SKILL.md: a
clear one-paragraph description at the top since that description is
what the model uses to decide relevance, followed by specific rules,
conventions, or step-by-step processes the model should follow when this
skill is active. Explain that skills are global by design so a Django
skill or a testing skill works the same way across every project without
needing to copy files around.

## Day 15 — model pulling and management flow

Update model_manager.py so the aimodel command has the following
behaviour. aimodel pull <name> checks if the model is already pulled by
calling list_models from ollama_client. If not pulled, it calls the
Ollama pull API endpoint and streams download progress as a Rich
progress bar showing percentage and size downloaded. Once the pull
finishes, it asks the user a yes/no question: set this as your default
model. If yes, it updates active_model in config.json. If no, it adds
the model name to a pulled_models list in config.json without changing
the active model, so the model stays available for later use without
switching away from the current default.

aimodel list shows a Rich table of every locally pulled model with a
marker next to whichever one is currently active. aimodel use <name>
checks if the name exists in pulled_models, and if so simply updates
active_model in config.json without re-pulling anything. If the name is
not found locally, it tells the user the model is not pulled yet and
offers to pull it now. aimodel remove <name> calls the Ollama delete
endpoint after a confirmation prompt, then removes the name from
pulled_models in config.json, and if that was the active model it clears
active_model and tells the user to pick a new default with aimodel use.

## Day 16 — switching models mid-session

In main.py, allow the user to type a special command inside the task
prompt loop like switch model to <name> or just model <name> instead of
a coding task. Detect this pattern at the start of the loop before
sending anything to Ollama. If detected, treat it as a call to the same
logic as aimodel use, update config, print a confirmation showing the
new active model, and return to the welcome prompt without ending the
session. This lets a user compare two models on the same task without
restarting freeai each time.