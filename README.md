# RealAI Environment Setup

A single-script bootstrap that sets up a complete local AI development environment from scratch — no manual steps, no cloud dependency, no API keys required after setup.

---

## What It Does

Running `setup_env.sh` performs **12 automated steps** in sequence:

| Step | What happens |
|------|-------------|
| 1 | Checks for Python 3.12+; installs it via your system package manager if missing |
| 2 | Installs `pyenv` + `pyenv-virtualenv` plugin and wires them into your shell |
| 3 | Compiles and caches Python 3.12.9 inside pyenv |
| 4 | Sets the virtualenv name to `realai` |
| 5 | Creates the `realai` virtualenv, activates it, upgrades pip |
| 6 | Downloads Claude Code and installs it to `/usr/local/bin/claude` |
| 7 | Installs Ollama (the local model server) |
| 8 | Starts Ollama as a background service and waits until it is ready |
| 9 | Pulls the `llama3.2:3b` model (~2 GB) from the Ollama registry |
| 10 | Connects Claude Code to Ollama by setting the required environment variables |
| 11 | Sends a live test prompt through Claude Code → Ollama → llama3.2:3b |
| 12 | Installs Visual Studio Code |

Everything is **idempotent** — re-running the script skips steps that are already complete.

---

## Requirements

### Operating system

| OS | Supported |
|----|-----------|
| macOS (Apple Silicon & Intel) | ✅ |
| Ubuntu / Debian | ✅ |
| Fedora / RHEL | ✅ |
| CentOS | ✅ |
| Arch Linux | ✅ |
| Windows | ❌ (use WSL2) |

### What must already be present

- `bash` 4.0+ (macOS ships with 3.x — install via `brew install bash` if needed)
- `curl`
- `git`
- `sudo` access (or run as root)
- Internet connection (for first-time downloads)
- ~6 GB free disk space (Python build, model weights, VS Code)

### Recommended RAM

| RAM | Experience |
|-----|-----------|
| 8 GB | Minimum — llama3.2:3b runs but leaves little headroom |
| 16 GB | Comfortable — model fits fully in memory |
| 32 GB+ | Ideal — fast inference, plenty of room for VS Code and other tools |

---

## Quick Start

```bash
# 1. Clone or download the script
curl -fsSL https://raw.githubusercontent.com/your-org/realai/main/setup_env.sh \
  -o setup_env.sh

# 2. Make it executable
chmod +x setup_env.sh

# 3. Run it
./setup_env.sh
```

The script prints a 3-second countdown at startup — press **Ctrl+C** at any point to abort safely.

---

## What Gets Installed

### Python 3.12 (system)

Installed via the appropriate package manager for your OS:

- **macOS** — `brew install python@3.12`
- **Ubuntu/Debian** — deadsnakes PPA → `apt install python3.12`
- **Fedora/RHEL** — `dnf install python3.12`
- **CentOS** — `yum install python3.12`
- **Arch** — `pacman -Sy python`

### pyenv

Installed via [pyenv.run](https://pyenv.run). Also installs the `pyenv-virtualenv` plugin.

The following block is appended to your `~/.zshrc` or `~/.bashrc`:

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

### `realai` virtualenv

A Python 3.12.9 virtualenv named `realai` is created and activated via pyenv. All subsequent Python tooling runs inside this isolated environment.

To re-activate it in a new terminal:

```bash
pyenv activate realai
```

### Claude Code

Downloaded via the official standalone installer (`https://claude.ai/install.sh`) and placed at:

```
/usr/local/bin/claude
```

This makes `claude` available system-wide for all users.

### Ollama

Installed via the official installer (`https://ollama.com/install.sh` on Linux, or `brew install ollama` on macOS). Started automatically as a background service:

- **Linux with systemd** — `systemctl enable/start ollama`
- **macOS with Homebrew** — `brew services start ollama`
- **Fallback** — `nohup ollama serve` with PID written to `/tmp/ollama.pid` and logs at `/tmp/ollama.log`

The script polls `http://localhost:11434` and only proceeds once Ollama is confirmed live (up to 30 retries, 1 second apart).

### llama3.2:3b model

| Property | Value |
|----------|-------|
| Model | Meta Llama 3.2 3B Instruct |
| Quantization | Q4_K_M |
| Download size | ~2 GB |
| RAM required at runtime | ~3–4 GB |
| Endpoint | `http://localhost:11434` |

Pull command used: `ollama pull llama3.2:3b`

### Claude Code ↔ Ollama wiring

Three environment variables are exported in the current session and persisted to your `~/.zshrc` / `~/.bashrc`:

```bash
export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL="http://localhost:11434"
```

This routes all Claude Code requests to your local Ollama server instead of Anthropic's cloud API. No internet connection or API key is needed once setup is complete.

### Visual Studio Code

Installed via the method most appropriate for your OS:

- **macOS + Homebrew** — `brew install --cask visual-studio-code`
- **macOS without Homebrew** — downloads the universal `.zip` from `code.visualstudio.com` and extracts to `/Applications`; symlinks `code` CLI to `/usr/local/bin/code`
- **Ubuntu/Debian** — Microsoft signed apt repository → `apt install code`
- **Fedora/RHEL** — Microsoft yum repository → `dnf install code`
- **CentOS** — Microsoft yum repository → `yum install code`
- **Linux fallback** — `snap install --classic code`

---

## Logging

Every run writes a timestamped log file:

```
/tmp/realai_setup_YYYYMMDD_HHMMSS.log
```

All terminal output (stdout + stderr) is tee'd to this file automatically. If the script fails, the log path is printed in the error message for easy debugging.

Log levels used during the run:

| Level | Colour | Meaning |
|-------|--------|---------|
| `INFO` | Cyan | About to perform an action |
| `DONE` | Green | Action completed successfully |
| `WARN` | Yellow | Non-fatal issue; script continues |
| `ERROR` | Red | Fatal — script exits immediately |
| `-> substep` | Dim | Granular detail on the current action |
| `COMPLETED` | Bold green | End-of-step summary |

A progress bar is shown at the start of each step:

```
+--------------------------------------------------------------+
|  STEP 8 / 12  --  Starting Ollama as a background service
|  Progress: [####################----------] 66%
+--------------------------------------------------------------+
```

---

## After Setup — Quick Reference

```bash
# Start Claude Code using the local llama3.2:3b model
claude --model llama3.2:3b

# Chat with llama3.2:3b directly (no Claude Code)
ollama run llama3.2:3b

# Open VS Code in the current directory
code .

# Re-activate the realai virtualenv in a new terminal
pyenv activate realai

# Check Ollama is running
curl http://localhost:11434

# View Ollama logs (if started as background process)
cat /tmp/ollama.log

# List all downloaded Ollama models
ollama list
```

---

## Troubleshooting

**`grep: invalid option -- P`**
Your system is using BSD `grep` (macOS). This has been patched — ensure you are using the latest version of the script.

**`pyenv: /path/to/.pyenv/versions/3.12.9 already exists`**
pyenv is prompting for confirmation because it thinks the version needs reinstalling. This is patched in the latest script via `pyenv install --skip-existing`.

**`Error: could not connect to ollama server`**
The model pull ran before the server started. This ordering bug has been fixed — Step 8 now starts the server, Step 9 pulls the model.

**`brew link` fails with "Already linked"**
This is patched — `brew link --force --overwrite python@3.12 2>/dev/null || true` suppresses the non-zero exit.

**Claude Code returns no response from Ollama**
Run the diagnostics manually:
```bash
# Confirm Ollama is up
curl http://localhost:11434

# Confirm model is present
ollama list

# Test the model directly
ollama run llama3.2:3b "Hello, are you running?"

# Test via Claude Code manually
ANTHROPIC_AUTH_TOKEN=ollama \
ANTHROPIC_BASE_URL=http://localhost:11434 \
ANTHROPIC_API_KEY='' \
claude --model llama3.2:3b
```

**VS Code `code` command not found after install**
On macOS: open VS Code → `Cmd+Shift+P` → type **Shell Command: Install 'code' command in PATH**.

---

## File Locations Summary

| Item | Location |
|------|----------|
| Script | `./setup_env.sh` |
| Setup log | `/tmp/realai_setup_YYYYMMDD_HHMMSS.log` |
| Claude Code binary | `/usr/local/bin/claude` |
| pyenv root | `~/.pyenv` |
| realai virtualenv | `~/.pyenv/versions/realai` |
| Ollama models | `~/.ollama/models/` |
| Ollama background log | `/tmp/ollama.log` |
| Ollama PID file | `/tmp/ollama.pid` |
| Shell env vars | `~/.zshrc` or `~/.bashrc` |

---

## License

MIT
