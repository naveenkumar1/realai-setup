#!/usr/bin/env bash
# =============================================================================
# setup_env.sh  —  RealAI Full Environment Bootstrap
# =============================================================================
#   STEP 1  · Check / Install Python 3.12
#   STEP 2  · Install pyenv + pyenv-virtualenv
#   STEP 3  · Ensure Python 3.12 inside pyenv
#   STEP 4  · Set virtual-environment name (realai)
#   STEP 5  · Create & activate the virtualenv
#   STEP 6  · Install Claude Code -> /usr/local/bin/claude
#   STEP 7  · Install Ollama
#   STEP 8  · Start Ollama as a background service
#   STEP 9  · Pull llama3.2:3b model
#   STEP 10 · Connect Claude Code to Ollama
#   STEP 11 · Smoke-test Claude Code <-> llama3.2:3b
#   STEP 12 · Install Visual Studio Code
# =============================================================================

set -euo pipefail

# -- Log file ------------------------------------------------------------------
LOG_FILE="/tmp/realai_setup_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
SETUP_START=$(date +%s)

# -- Colours -------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# -- Logging helpers -----------------------------------------------------------
TOTAL_STEPS=12
CURRENT_STEP=0

timestamp() { date '+%H:%M:%S'; }

info()    { echo -e "${CYAN}  [$(timestamp)]  INFO    ${RESET} $*"; }
success() { echo -e "${GREEN}  [$(timestamp)]  DONE    ${RESET} $*"; }
warn()    { echo -e "${YELLOW}  [$(timestamp)]  WARN    ${RESET} $*"; }
error()   { echo -e "${RED}  [$(timestamp)]  ERROR   ${RESET} $*" >&2
            echo -e "${RED}  Full log saved to: $LOG_FILE${RESET}" >&2
            exit 1; }
substep() { echo -e "${DIM}       ->  $*${RESET}"; }
done_msg(){ echo -e "${GREEN}${BOLD}  [$(timestamp)]  COMPLETED  ${RESET} $*"; }

section() {
  CURRENT_STEP=$(( CURRENT_STEP + 1 ))
  local pct=$(( CURRENT_STEP * 100 / TOTAL_STEPS ))
  local filled=$(( CURRENT_STEP * 30 / TOTAL_STEPS ))
  local bar=""
  for ((i=0; i<filled; i++));    do bar+="#"; done
  for ((i=filled; i<30; i++));   do bar+="-"; done
  echo ""
  echo -e "${BOLD}${BLUE}+--------------------------------------------------------------+${RESET}"
  printf "${BOLD}${BLUE}|${RESET}  ${BOLD}STEP %d / %d${RESET}  --  %s\n" "$CURRENT_STEP" "$TOTAL_STEPS" "$*"
  printf "${BOLD}${BLUE}|${RESET}  Progress: [${GREEN}%s${RESET}] %d%%\n" "$bar" "$pct"
  echo -e "${BOLD}${BLUE}+--------------------------------------------------------------+${RESET}"
  echo ""
}

step_done() {
  local elapsed=$(( $(date +%s) - SETUP_START ))
  echo ""
  echo -e "${GREEN}${BOLD}  -- Step $CURRENT_STEP complete  (elapsed: ${elapsed}s total)${RESET}"
  echo ""
}

# -- Welcome banner ------------------------------------------------------------
echo ""
echo -e "${BOLD}${MAGENTA}+--------------------------------------------------------------+${RESET}"
echo -e "${BOLD}${MAGENTA}|                                                              |${RESET}"
echo -e "${BOLD}${MAGENTA}|        RealAI Environment Setup  --  v1.0                    |${RESET}"
echo -e "${BOLD}${MAGENTA}|        $(date '+%A, %d %B %Y  %H:%M:%S')                    |${RESET}"
echo -e "${BOLD}${MAGENTA}|                                                              |${RESET}"
echo -e "${BOLD}${MAGENTA}|  This script will install:                                   |${RESET}"
echo -e "${BOLD}${MAGENTA}|    * Python 3.12       * pyenv                               |${RESET}"
echo -e "${BOLD}${MAGENTA}|    * realai virtualenv * Claude Code                         |${RESET}"
echo -e "${BOLD}${MAGENTA}|    * Ollama            * llama3.2:3b model                   |${RESET}"
echo -e "${BOLD}${MAGENTA}|    * VS Code                                                 |${RESET}"
echo -e "${BOLD}${MAGENTA}|                                                              |${RESET}"
echo -e "${BOLD}${MAGENTA}+--------------------------------------------------------------+${RESET}"
echo ""
echo -e "  ${DIM}Full log will be written to: ${BOLD}$LOG_FILE${RESET}"
echo ""
echo -e "  ${YELLOW}Starting in 3 seconds -- press Ctrl+C to abort...${RESET}"
sleep 3
echo ""

# -- Detect OS -----------------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
info "Detected OS: ${BOLD}$OS${RESET}  |  Architecture: ${BOLD}$ARCH${RESET}"

# -- Sudo helper ---------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
  if ! command -v sudo &>/dev/null; then
    error "Root privileges are needed but 'sudo' is not installed."
  fi
  SUDO="sudo"
  info "Will use ${BOLD}sudo${RESET} for privileged operations"
else
  SUDO=""
  info "Running as root -- no sudo required"
fi

# =============================================================================
# STEP 1 -- Check / Install Python 3.12
# =============================================================================
section "Checking / Installing Python 3.12"

info "Scanning system for a compatible Python installation (need 3.12+)..."

REQUIRED_MAJOR=3
REQUIRED_MINOR=12

python_ok() {
  local py_bin="$1"
  if command -v "$py_bin" &>/dev/null; then
    local raw ver major minor
    raw=$("$py_bin" --version 2>&1)
    ver=$(echo "$raw" | sed 's/[^0-9]*\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/')
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    [[ -z "$major" || -z "$minor" ]] && return 1
    if [[ "$major" -gt "$REQUIRED_MAJOR" ]] || \
       { [[ "$major" -eq "$REQUIRED_MAJOR" ]] && [[ "$minor" -ge "$REQUIRED_MINOR" ]]; }; then
      return 0
    fi
  fi
  return 1
}

SYSTEM_PYTHON=""
for candidate in python3.12 python3 python; do
  substep "Checking candidate: $candidate"
  if python_ok "$candidate"; then
    SYSTEM_PYTHON="$candidate"
    break
  fi
done

if [[ -n "$SYSTEM_PYTHON" ]]; then
  FOUND_VER=$("$SYSTEM_PYTHON" --version 2>&1)
  success "Python 3.12+ already on this machine: ${BOLD}$FOUND_VER${RESET}  (via $SYSTEM_PYTHON)"
  substep "No installation needed -- proceeding to next step"
else
  warn "No compatible Python found. Installing Python 3.12 now..."

  case "$OS" in
    Linux)
      if command -v apt-get &>/dev/null; then
        info "Detected Debian/Ubuntu -- installing via apt + deadsnakes PPA"
        substep "Refreshing package lists..."
        $SUDO apt-get update -qq
        substep "Installing software-properties-common..."
        $SUDO apt-get install -y software-properties-common
        substep "Adding deadsnakes PPA for Python 3.12..."
        $SUDO add-apt-repository -y ppa:deadsnakes/ppa
        $SUDO apt-get update -qq
        substep "Installing python3.12, python3.12-venv, python3.12-dev..."
        $SUDO apt-get install -y python3.12 python3.12-venv python3.12-dev
      elif command -v dnf &>/dev/null; then
        info "Detected Fedora/RHEL -- installing via dnf"
        substep "Running: dnf install python3.12 python3.12-devel"
        $SUDO dnf install -y python3.12 python3.12-devel
      elif command -v yum &>/dev/null; then
        info "Detected CentOS/RHEL -- installing via yum"
        substep "Running: yum install python3.12 python3.12-devel"
        $SUDO yum install -y python3.12 python3.12-devel
      elif command -v pacman &>/dev/null; then
        info "Detected Arch Linux -- installing via pacman"
        substep "Running: pacman -Sy python"
        $SUDO pacman -Sy --noconfirm python
      elif command -v brew &>/dev/null; then
        info "Detected Homebrew on Linux"
        substep "Running: brew install python@3.12"
        brew install python@3.12
      else
        error "No supported package manager found. Please install Python 3.12 manually."
      fi
      ;;
    Darwin)
      if command -v brew &>/dev/null; then
        info "Detected macOS with Homebrew"
        substep "Running: brew install python@3.12"
        brew install python@3.12
        substep "Linking python@3.12 (suppressing already-linked warnings)..."
        brew link --force --overwrite python@3.12 2>/dev/null || true
      else
        error "Homebrew not found. Install it first: https://brew.sh"
      fi
      ;;
    *)
      error "Unsupported OS: $OS"
      ;;
  esac

  substep "Verifying Python 3.12 is now reachable..."
  for candidate in python3.12 python3 python; do
    if python_ok "$candidate"; then
      SYSTEM_PYTHON="$candidate"
      break
    fi
  done
  [[ -n "$SYSTEM_PYTHON" ]] || error "Python 3.12 installation failed."
  success "Python 3.12 installed and verified: ${BOLD}$($SYSTEM_PYTHON --version)${RESET}"
fi
step_done

# =============================================================================
# STEP 2 -- Install pyenv + pyenv-virtualenv
# =============================================================================
section "Installing pyenv + pyenv-virtualenv"

PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"

if [[ -d "$PYENV_ROOT" ]]; then
  success "pyenv already installed at ${BOLD}$PYENV_ROOT${RESET} -- skipping download"
  substep "Will re-use existing installation"
else
  info "pyenv not found -- starting installation..."
  substep "Installing build dependencies required by pyenv..."

  case "$OS" in
    Linux)
      if command -v apt-get &>/dev/null; then
        substep "apt: installing make, gcc, libssl-dev, libffi-dev, git and friends..."
        $SUDO apt-get install -y \
          make build-essential libssl-dev zlib1g-dev libbz2-dev \
          libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev \
          xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
          git 2>/dev/null || true
      elif command -v dnf &>/dev/null; then
        substep "dnf: installing gcc, zlib-devel, openssl-devel, readline-devel, git..."
        $SUDO dnf install -y \
          make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel \
          openssl-devel tk-devel libffi-devel xz-devel git 2>/dev/null || true
      fi
      ;;
    Darwin)
      substep "macOS: ensuring Xcode Command Line Tools are present..."
      xcode-select --install 2>/dev/null || true
      ;;
  esac

  info "Downloading pyenv via the official pyenv.run installer..."
  substep "Running: curl -fsSL https://pyenv.run | bash"
  curl -fsSL https://pyenv.run | bash
  success "pyenv downloaded and installed at ${BOLD}$PYENV_ROOT${RESET}"
fi

info "Wiring pyenv into the current shell session..."
substep "Exporting PYENV_ROOT and updating PATH"
export PYENV_ROOT
export PATH="$PYENV_ROOT/bin:$PATH"
substep "Running: eval \"\$(pyenv init -)\""
eval "$(pyenv init -)"
success "pyenv is active -- version: $(pyenv --version)"

PYENV_VENV_PLUGIN="$PYENV_ROOT/plugins/pyenv-virtualenv"
if [[ ! -d "$PYENV_VENV_PLUGIN" ]]; then
  info "pyenv-virtualenv plugin not found -- cloning from GitHub..."
  substep "Running: git clone https://github.com/pyenv/pyenv-virtualenv.git"
  git clone https://github.com/pyenv/pyenv-virtualenv.git "$PYENV_VENV_PLUGIN"
  success "pyenv-virtualenv plugin installed at ${BOLD}$PYENV_VENV_PLUGIN${RESET}"
else
  success "pyenv-virtualenv plugin already present"
fi

substep "Initialising pyenv-virtualenv in current shell..."
eval "$(pyenv virtualenv-init -)" 2>/dev/null || true
success "pyenv-virtualenv initialised"
step_done

# =============================================================================
# STEP 3 -- Ensure Python 3.12 is available inside pyenv
# =============================================================================
section "Ensuring Python 3.12 inside pyenv"

PYENV_PY_VERSION="3.12.9"
info "Target Python version for pyenv: ${BOLD}$PYENV_PY_VERSION${RESET}"
substep "Checking if $PYENV_PY_VERSION is already compiled and cached in pyenv..."

if pyenv versions --bare | sed 's/^[[:space:]*]*//' | grep -qx "$PYENV_PY_VERSION"; then
  success "pyenv already has Python ${BOLD}$PYENV_PY_VERSION${RESET} -- no compilation needed"
  substep "Skipping download and build"
else
  info "Python $PYENV_PY_VERSION not found in pyenv -- downloading and compiling now..."
  substep "This may take 3-10 minutes depending on your machine speed"
  substep "pyenv will download the CPython source and compile it from scratch"
  substep "Running: pyenv install --skip-existing $PYENV_PY_VERSION"
  pyenv install --skip-existing "$PYENV_PY_VERSION"
  success "Python ${BOLD}$PYENV_PY_VERSION${RESET} compiled and installed via pyenv"
fi

done_msg "Python $PYENV_PY_VERSION is ready inside pyenv"
step_done

# =============================================================================
# STEP 4 -- Set virtual-environment name
# =============================================================================
section "Setting virtual-environment name"

VENV_NAME="realai"
info "Virtual environment name is fixed to: ${BOLD}${MAGENTA}$VENV_NAME${RESET}"
substep "This name was pre-configured in the script -- no user input required"
substep "All Python packages for this project will be isolated inside '$VENV_NAME'"
substep "Python version pinned to: $PYENV_PY_VERSION"
done_msg "Virtualenv name confirmed: ${BOLD}$VENV_NAME${RESET}"
step_done

# =============================================================================
# STEP 5 -- Create & activate the virtual environment
# =============================================================================
section "Creating & activating virtualenv '$VENV_NAME'"

info "Checking whether virtualenv '${BOLD}$VENV_NAME${RESET}' already exists..."

if pyenv virtualenvs --bare | sed 's/^[[:space:]*]*//' | grep -qx "$VENV_NAME"; then
  warn "Virtualenv '${BOLD}$VENV_NAME${RESET}' already exists on this machine"
  substep "No need to recreate it -- skipping creation step"
  info "Activating existing virtualenv '${BOLD}$VENV_NAME${RESET}'..."
else
  info "Virtualenv '$VENV_NAME' does not exist yet -- creating it now..."
  substep "Running: pyenv virtualenv $PYENV_PY_VERSION $VENV_NAME"
  pyenv virtualenv "$PYENV_PY_VERSION" "$VENV_NAME"
  success "Virtualenv '${BOLD}$VENV_NAME${RESET}' created (Python $PYENV_PY_VERSION)"
  info "Activating newly created virtualenv '${BOLD}$VENV_NAME${RESET}'..."
fi

substep "Running: pyenv activate $VENV_NAME"
pyenv activate "$VENV_NAME"
success "Virtualenv '${BOLD}${MAGENTA}$VENV_NAME${RESET}' is now ${BOLD}ACTIVE${RESET}"
substep "Python in use: $(python --version)"
substep "pip in use:    $(pip --version)"

info "Upgrading pip to the latest version inside the virtualenv..."
substep "Running: pip install --upgrade pip"
pip install --upgrade pip --quiet
success "pip upgraded: $(pip --version)"

# Persist pyenv init to shell rc
SHELL_RC=""
if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == */zsh ]]; then
  SHELL_RC="$HOME/.zshrc"
elif [[ -n "${BASH_VERSION:-}" ]] || [[ "$SHELL" == */bash ]]; then
  SHELL_RC="$HOME/.bashrc"
fi

PYENV_INIT_SNIPPET='
# >>> pyenv init (added by setup_env.sh) >>>
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
# <<< pyenv init <<<
'

if [[ -n "$SHELL_RC" ]]; then
  if ! grep -q "pyenv init" "$SHELL_RC" 2>/dev/null; then
    substep "Adding pyenv init block to $SHELL_RC..."
    echo "$PYENV_INIT_SNIPPET" >> "$SHELL_RC"
    success "pyenv init saved to ${BOLD}$SHELL_RC${RESET}"
  else
    success "pyenv init already present in $SHELL_RC -- no changes needed"
  fi
fi

done_msg "Virtualenv '${BOLD}$VENV_NAME${RESET}' is active and ready"
step_done

# =============================================================================
# STEP 6 -- Install Claude Code
# =============================================================================
section "Installing Claude Code to /usr/local/bin"

CLAUDE_BIN="/usr/local/bin/claude"

info "Checking whether Claude Code is already installed at ${BOLD}$CLAUDE_BIN${RESET}..."
if [[ -x "$CLAUDE_BIN" ]]; then
  CLAUDE_VER=$("$CLAUDE_BIN" --version 2>/dev/null || echo "unknown")
  success "Claude Code already installed at $CLAUDE_BIN -- version: ${BOLD}$CLAUDE_VER${RESET}"
  substep "Skipping installation"
elif command -v claude &>/dev/null; then
  EXISTING=$(command -v claude)
  info "Claude Code found at $EXISTING -- copying to /usr/local/bin for system-wide access..."
  substep "Running: cp $EXISTING $CLAUDE_BIN"
  $SUDO cp "$EXISTING" "$CLAUDE_BIN"
  $SUDO chmod +x "$CLAUDE_BIN"
  success "Claude Code copied to ${BOLD}$CLAUDE_BIN${RESET}"
else
  info "Claude Code not found -- downloading via official installer, then moving to /usr/local/bin..."
  substep "Step 1: Running official installer to a temp location"
  substep "Source: https://claude.ai/install.sh"

  # Run the installer, then locate the downloaded binary and move it
  TMP_INSTALL_DIR="$(mktemp -d)"
  substep "Temp dir: $TMP_INSTALL_DIR"
  substep "Running: curl -fsSL https://claude.ai/install.sh | bash"
  curl -fsSL https://claude.ai/install.sh | bash

  substep "Step 2: Locating the installed 'claude' binary..."
  INSTALLED_CLAUDE=$(command -v claude 2>/dev/null || true)

  if [[ -z "$INSTALLED_CLAUDE" ]]; then
    # Installer may have placed it in a non-PATH location -- search common spots
    for candidate in \
        "$HOME/.claude/local/claude" \
        "$HOME/.local/bin/claude" \
        "$HOME/bin/claude" \
        "/usr/bin/claude"; do
      substep "Checking: $candidate"
      if [[ -x "$candidate" ]]; then
        INSTALLED_CLAUDE="$candidate"
        break
      fi
    done
  fi

  if [[ -n "$INSTALLED_CLAUDE" && "$INSTALLED_CLAUDE" != "$CLAUDE_BIN" ]]; then
    substep "Step 3: Moving claude binary from $INSTALLED_CLAUDE -> $CLAUDE_BIN"
    $SUDO mkdir -p /usr/local/bin
    $SUDO cp "$INSTALLED_CLAUDE" "$CLAUDE_BIN"
    $SUDO chmod +x "$CLAUDE_BIN"
    success "Claude Code installed at ${BOLD}$CLAUDE_BIN${RESET}"
  elif [[ "$INSTALLED_CLAUDE" == "$CLAUDE_BIN" ]]; then
    success "Installer already placed Claude Code at ${BOLD}$CLAUDE_BIN${RESET}"
  else
    warn "Could not locate the claude binary after installation"
    substep "Searched: ~/.claude/local/claude, ~/.local/bin/claude, ~/bin/claude"
    substep "Please verify the installer completed successfully and re-run the script"
  fi

  rm -rf "$TMP_INSTALL_DIR"
fi

substep "Verifying 'claude' is executable at /usr/local/bin/claude..."
if [[ -x "$CLAUDE_BIN" ]]; then
  success "Claude Code confirmed at ${BOLD}$CLAUDE_BIN${RESET} -- version: $("$CLAUDE_BIN" --version 2>/dev/null || echo 'installed')"
else
  warn "Claude binary not found at $CLAUDE_BIN -- check installer output above"
fi

done_msg "Claude Code is installed at /usr/local/bin/claude"
step_done

# =============================================================================
# STEP 7 -- Install Ollama
# =============================================================================
section "Installing Ollama"

info "Checking whether Ollama is already installed..."
if command -v ollama &>/dev/null; then
  OLLAMA_VER=$(ollama --version 2>/dev/null || echo "unknown")
  success "Ollama already installed -- version: ${BOLD}$OLLAMA_VER${RESET}"
  substep "Skipping installation"
else
  info "Ollama not found -- starting installation..."

  case "$OS" in
    Linux)
      info "Detected Linux -- running the official Ollama install script..."
      substep "Source: https://ollama.com/install.sh"
      substep "This will install the 'ollama' binary and set up a systemd service"
      substep "Running: curl -fsSL https://ollama.com/install.sh | sh"
      curl -fsSL https://ollama.com/install.sh | sh
      success "Ollama installed on Linux"

      if command -v systemctl &>/dev/null; then
        substep "Enabling ollama.service to auto-start on boot..."
        $SUDO systemctl enable ollama 2>/dev/null || true
        substep "Starting ollama.service now..."
        $SUDO systemctl start ollama 2>/dev/null || true
        success "Ollama systemd service enabled and started"
      fi
      ;;

    Darwin)
      if command -v brew &>/dev/null; then
        info "Detected macOS with Homebrew -- installing Ollama via brew..."
        substep "Running: brew install ollama"
        brew install ollama
        success "Ollama installed via Homebrew"
      else
        info "Homebrew not available -- downloading Ollama macOS zip directly..."
        OLLAMA_ZIP="/tmp/Ollama-darwin.zip"
        substep "Downloading from: https://ollama.com/download/Ollama-darwin.zip"
        curl -fSL "https://ollama.com/download/Ollama-darwin.zip" -o "$OLLAMA_ZIP"
        substep "Extracting to /Applications..."
        unzip -q "$OLLAMA_ZIP" -d /Applications/
        rm -f "$OLLAMA_ZIP"
        success "Ollama.app installed to /Applications/"
      fi
      ;;

    *)
      error "Unsupported OS '$OS' for automatic Ollama install."
      ;;
  esac

  substep "Verifying 'ollama' command is available..."
  command -v ollama &>/dev/null && \
    success "Ollama verified: ${BOLD}$(ollama --version 2>/dev/null || echo 'installed')${RESET}" || \
    warn "Ollama binary not yet in PATH -- a new terminal session may be required"
fi

done_msg "Ollama is ready"
step_done

# =============================================================================
# STEP 8 -- Start Ollama as a background service
# =============================================================================
section "Starting Ollama as a background service"

info "Checking if Ollama is already serving on http://localhost:11434..."
OLLAMA_RUNNING=false

if curl -s http://localhost:11434 &>/dev/null; then
  success "Ollama is already running and responding on ${BOLD}http://localhost:11434${RESET}"
  substep "No need to start a new process"
  OLLAMA_RUNNING=true
fi

if [[ "$OLLAMA_RUNNING" == false ]]; then
  info "Ollama is not yet running -- starting it now as a background service..."

  case "$OS" in
    Linux)
      if command -v systemctl &>/dev/null && systemctl list-unit-files ollama.service &>/dev/null 2>&1; then
        info "Using systemd to start the Ollama service..."
        substep "Running: systemctl enable ollama && systemctl start ollama"
        $SUDO systemctl enable ollama 2>/dev/null || true
        $SUDO systemctl start ollama
        substep "Waiting 3 seconds for Ollama to bind to port 11434..."
        sleep 3
        success "Ollama systemd service is running"
      else
        info "systemd not available -- launching Ollama as a nohup background process..."
        substep "Running: nohup ollama serve > /tmp/ollama.log 2>&1 &"
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        OLLAMA_PID=$!
        echo "$OLLAMA_PID" > /tmp/ollama.pid
        success "Ollama background process started with PID ${BOLD}$OLLAMA_PID${RESET}"
        substep "Log output: /tmp/ollama.log"
        substep "PID file:   /tmp/ollama.pid"
      fi
      ;;

    Darwin)
      if command -v brew &>/dev/null && brew list --formula 2>/dev/null | grep -q "^ollama$"; then
        info "Using Homebrew services to start Ollama..."
        substep "Running: brew services start ollama"
        brew services start ollama
        substep "Waiting 3 seconds for Homebrew service to start..."
        sleep 3
        success "Ollama Homebrew service started"
      else
        info "Launching Ollama as a nohup background process (macOS)..."
        substep "Running: nohup ollama serve > /tmp/ollama.log 2>&1 &"
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        OLLAMA_PID=$!
        echo "$OLLAMA_PID" > /tmp/ollama.pid
        success "Ollama background process started with PID ${BOLD}$OLLAMA_PID${RESET}"
        substep "Log output: /tmp/ollama.log"
        substep "PID file:   /tmp/ollama.pid"
      fi
      ;;
  esac

  info "Waiting for Ollama API to become ready on http://localhost:11434..."
  ATTEMPTS=0
  MAX_ATTEMPTS=30
  until curl -s http://localhost:11434 &>/dev/null; do
    ATTEMPTS=$((ATTEMPTS + 1))
    substep "Attempt $ATTEMPTS/$MAX_ATTEMPTS -- not ready yet, retrying in 1s..."
    if [[ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]]; then
      error "Ollama did not respond after ${MAX_ATTEMPTS}s. Check the log: /tmp/ollama.log"
    fi
    sleep 1
  done
  success "Ollama API is ${BOLD}UP${RESET} and responding on ${BOLD}http://localhost:11434${RESET}"
fi

done_msg "Ollama background service is live"
step_done

# =============================================================================
# STEP 9 -- Pull llama3.2:3b model
# =============================================================================
section "Pulling llama3.2:3b model from Ollama registry"

info "Checking local Ollama model library for llama3.2:3b..."
if ollama list 2>/dev/null | grep -q "llama3.2:3b"; then
  success "Model ${BOLD}llama3.2:3b${RESET} is already downloaded -- skipping pull"
  substep "No network download required"
else
  info "llama3.2:3b not yet downloaded -- pulling from Ollama registry..."
  substep "Model size: ~2GB  |  Quantization: Q4_K_M  |  RAM required: ~3-4 GB"
  substep "This may take a few minutes depending on your internet speed"
  substep "Running: ollama pull llama3.2:3b"
  ollama pull llama3.2:3b
  success "Model ${BOLD}llama3.2:3b${RESET} downloaded and stored in local Ollama library"
fi

substep "Confirming model appears in 'ollama list'..."
ollama list 2>/dev/null | grep llama3.2 || true
done_msg "llama3.2:3b is ready for inference"
step_done



# =============================================================================
# STEP 10 -- Connect Claude Code to Ollama
# =============================================================================
section "Connecting Claude Code to local Ollama backend"

info "Configuring Claude Code to route all requests to the local Ollama server..."
substep "This replaces Anthropic's cloud API with your local llama3.2:3b model"
substep "No API key or internet connection will be needed to use Claude Code"
echo ""
substep "Setting three environment variables:"
substep "  ANTHROPIC_AUTH_TOKEN=ollama               (local auth token)"
substep "  ANTHROPIC_API_KEY=''                      (no cloud key needed)"
substep "  ANTHROPIC_BASE_URL=http://localhost:11434  (point to local Ollama)"
echo ""

export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL="http://localhost:11434"

success "ANTHROPIC_AUTH_TOKEN  -> ollama"
success "ANTHROPIC_API_KEY     -> (empty)"
success "ANTHROPIC_BASE_URL    -> http://localhost:11434"

OLLAMA_ENV_SNIPPET='
# >>> Claude Code -> Ollama local backend (added by setup_env.sh) >>>
export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL="http://localhost:11434"
# <<< Claude Code -> Ollama <<<
'

if [[ -n "$SHELL_RC" ]]; then
  if ! grep -q "Claude Code -> Ollama" "$SHELL_RC" 2>/dev/null; then
    info "Persisting Ollama env vars to ${BOLD}$SHELL_RC${RESET} for all future sessions..."
    substep "Appending env var block to $SHELL_RC"
    echo "$OLLAMA_ENV_SNIPPET" >> "$SHELL_RC"
    success "Env vars saved to ${BOLD}$SHELL_RC${RESET} -- will apply in every new terminal"
  else
    success "Ollama env vars already present in ${BOLD}$SHELL_RC${RESET} -- no changes needed"
  fi
else
  warn "Could not detect shell RC file -- env vars set for this session only"
  substep "Manually add to your shell profile to persist:"
  substep "  export ANTHROPIC_AUTH_TOKEN=ollama"
  substep "  export ANTHROPIC_API_KEY=''"
  substep "  export ANTHROPIC_BASE_URL=http://localhost:11434"
fi

done_msg "Claude Code is now wired to Ollama locally"
step_done

# =============================================================================
# STEP 11 -- Smoke-test: Claude Code <-> llama3.2:3b
# =============================================================================
section "Smoke-testing Claude Code <-> llama3.2:3b"

TEST_PROMPT="Reply in one sentence: confirm you are llama3.2:3b running locally via Ollama."

info "Sending a live test prompt through Claude Code -> Ollama -> llama3.2:3b..."
substep "Mode:     non-interactive (claude -p / print mode)"
substep "Model:    llama3.2:3b"
substep "Endpoint: http://localhost:11434"
substep "Prompt:   \"$TEST_PROMPT\""
echo ""

RESPONSE=$(ANTHROPIC_AUTH_TOKEN="ollama" \
           ANTHROPIC_API_KEY="" \
           ANTHROPIC_BASE_URL="http://localhost:11434" \
           claude --model llama3.2:3b -p "$TEST_PROMPT" 2>/dev/null || true)

if [[ -z "$RESPONSE" ]]; then
  warn "No response received from llama3.2:3b -- running diagnostics..."
  substep "Ollama API HTTP status : $(curl -s -o /dev/null -w '%{http_code}' http://localhost:11434)"
  substep "Model in ollama list   : $(ollama list 2>/dev/null | grep llama3.2 || echo 'NOT FOUND')"
  substep "ANTHROPIC_BASE_URL     : $ANTHROPIC_BASE_URL"
  warn "Try running manually:"
  substep "  ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY='' claude --model llama3.2:3b"
else
  echo -e "${BOLD}${GREEN}  +-- Claude Code -> llama3.2:3b  --  Live Response ----------+${RESET}"
  echo -e "${BOLD}${GREEN}  |${RESET}"
  echo -e "${BOLD}${GREEN}  |${RESET}  ${BOLD}$RESPONSE${RESET}"
  echo -e "${BOLD}${GREEN}  |${RESET}"
  echo -e "${BOLD}${GREEN}  +------------------------------------------------------------+${RESET}"
  echo ""
  success "Claude Code is LIVE and successfully talking to llama3.2:3b via Ollama!"
fi

done_msg "Claude Code <-> Ollama smoke-test complete"
step_done

# =============================================================================
# STEP 12 -- Install Visual Studio Code
# =============================================================================
section "Checking / Installing Visual Studio Code"

info "Scanning for an existing VS Code installation..."
VSCODE_INSTALLED=false

for vscode_bin in code code-insiders codium; do
  substep "Checking for binary: $vscode_bin"
  if command -v "$vscode_bin" &>/dev/null; then
    VSCODE_VERSION=$("$vscode_bin" --version 2>/dev/null | head -1)
    success "VS Code already installed -- version: ${BOLD}$VSCODE_VERSION${RESET}  (binary: $vscode_bin)"
    VSCODE_INSTALLED=true
    break
  fi
done

if [[ "$VSCODE_INSTALLED" == false && "$OS" == "Darwin" ]]; then
  substep "Checking for VS Code app bundle at /Applications/Visual Studio Code.app..."
  if [[ -d "/Applications/Visual Studio Code.app" ]]; then
    success "VS Code app bundle found at ${BOLD}/Applications/Visual Studio Code.app${RESET}"
    VSCODE_INSTALLED=true
  fi
fi

if [[ "$VSCODE_INSTALLED" == false ]]; then
  info "VS Code not found -- installing now..."

  case "$OS" in
    Darwin)
      if command -v brew &>/dev/null; then
        info "Installing VS Code via Homebrew Cask (recommended for macOS)..."
        substep "Running: brew install --cask visual-studio-code"
        brew install --cask visual-studio-code
        success "VS Code installed via Homebrew Cask"
      else
        info "Downloading VS Code .zip directly from Microsoft..."
        VSCODE_ZIP="/tmp/VSCode-darwin-universal.zip"
        substep "Downloading universal macOS build from code.visualstudio.com..."
        curl -fSL \
          "https://code.visualstudio.com/sha/download?build=stable&os=darwin-universal" \
          -o "$VSCODE_ZIP"
        substep "Extracting to /Applications..."
        unzip -q "$VSCODE_ZIP" -d /Applications/
        rm -f "$VSCODE_ZIP"
        success "VS Code extracted to ${BOLD}/Applications/Visual Studio Code.app${RESET}"
      fi

      VSCODE_CLI="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
      if [[ -f "$VSCODE_CLI" ]]; then
        substep "Found bundled 'code' CLI at: $VSCODE_CLI"
        if [[ ! -L "/usr/local/bin/code" ]]; then
          substep "Symlinking 'code' CLI to /usr/local/bin/code for terminal access..."
          ln -sf "$VSCODE_CLI" /usr/local/bin/code 2>/dev/null || \
            $SUDO ln -sf "$VSCODE_CLI" /usr/local/bin/code
          success "'code' CLI symlinked to /usr/local/bin/code"
        else
          success "'code' CLI symlink already exists at /usr/local/bin/code"
        fi
      fi
      ;;

    Linux)
      if command -v apt-get &>/dev/null; then
        info "Installing VS Code via Microsoft apt repository (Debian/Ubuntu)..."
        substep "Importing Microsoft GPG key..."
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
          | gpg --dearmor \
          | $SUDO tee /usr/share/keyrings/microsoft-archive-keyring.gpg > /dev/null
        substep "Adding Microsoft VS Code apt source..."
        echo "deb [arch=$(dpkg --print-architecture) \
signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] \
https://packages.microsoft.com/repos/vscode stable main" \
          | $SUDO tee /etc/apt/sources.list.d/vscode.list > /dev/null
        substep "Running: apt-get update && apt-get install code..."
        $SUDO apt-get update -qq
        $SUDO apt-get install -y code
        success "VS Code installed via apt"

      elif command -v dnf &>/dev/null; then
        info "Installing VS Code via Microsoft dnf repository (Fedora/RHEL)..."
        substep "Importing Microsoft RPM signing key..."
        $SUDO rpm --import https://packages.microsoft.com/keys/microsoft.asc
        substep "Adding VS Code yum repo..."
        $SUDO tee /etc/yum.repos.d/vscode.repo > /dev/null <<'EOF'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
EOF
        substep "Running: dnf install code..."
        $SUDO dnf install -y code
        success "VS Code installed via dnf"

      elif command -v yum &>/dev/null; then
        info "Installing VS Code via Microsoft yum repository (CentOS/RHEL)..."
        substep "Importing Microsoft RPM signing key..."
        $SUDO rpm --import https://packages.microsoft.com/keys/microsoft.asc
        substep "Adding VS Code yum repo..."
        $SUDO tee /etc/yum.repos.d/vscode.repo > /dev/null <<'EOF'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
EOF
        substep "Running: yum install code..."
        $SUDO yum install -y code
        success "VS Code installed via yum"

      elif command -v snap &>/dev/null; then
        info "Installing VS Code via snap (fallback for Linux)..."
        substep "Running: snap install --classic code"
        $SUDO snap install --classic code
        success "VS Code installed via snap"

      else
        warn "No supported package manager found -- cannot auto-install VS Code"
        warn "Download manually from: https://code.visualstudio.com/download"
      fi
      ;;

    *)
      warn "Unsupported OS '$OS' -- cannot auto-install VS Code"
      warn "Download manually from: https://code.visualstudio.com/download"
      ;;
  esac
else
  info "VS Code already present -- skipping installation"
fi

substep "Final check -- verifying 'code' CLI is accessible..."
if command -v code &>/dev/null; then
  success "VS Code CLI confirmed: ${BOLD}$(code --version 2>/dev/null | head -1)${RESET}"
else
  warn "'code' command not found in PATH"
  substep "On macOS: open VS Code -> CMD+Shift+P -> 'Shell Command: Install code command in PATH'"
fi

done_msg "VS Code installation complete"
step_done

# =============================================================================
# FINAL SUMMARY
# =============================================================================
TOTAL_ELAPSED=$(( $(date +%s) - SETUP_START ))
MINS=$(( TOTAL_ELAPSED / 60 ))
SECS=$(( TOTAL_ELAPSED % 60 ))

echo ""
echo -e "${BOLD}${GREEN}+--------------------------------------------------------------+${RESET}"
echo -e "${BOLD}${GREEN}|                                                              |${RESET}"
echo -e "${BOLD}${GREEN}|    RealAI Setup Complete!                                    |${RESET}"
printf  "${BOLD}${GREEN}|    Total time: %dm %ds%-38s|${RESET}\n" "$MINS" "$SECS" ""
echo -e "${BOLD}${GREEN}|                                                              |${RESET}"
echo -e "${BOLD}${GREEN}+--------------------------------------------------------------+${RESET}"
echo ""
echo -e "  ${BOLD}Installed components:${RESET}"
echo -e "  ${GREEN}[OK]${RESET}  Python        $($SYSTEM_PYTHON --version 2>&1)"
echo -e "  ${GREEN}[OK]${RESET}  pyenv         $(pyenv --version 2>&1)"
echo -e "  ${GREEN}[OK]${RESET}  Virtualenv    ${BOLD}$VENV_NAME${RESET}  (Python $PYENV_PY_VERSION -- ACTIVE)"
echo -e "  ${GREEN}[OK]${RESET}  Claude Code   $(claude --version 2>/dev/null | head -1 || echo 'installed')"
echo -e "  ${GREEN}[OK]${RESET}  Ollama        $(ollama --version 2>/dev/null || echo 'installed')"
echo -e "  ${GREEN}[OK]${RESET}  Model         llama3.2:3b  ->  http://localhost:11434"
echo -e "  ${GREEN}[OK]${RESET}  VS Code       $(code --version 2>/dev/null | head -1 || echo 'installed')"
echo -e "  ${GREEN}[OK]${RESET}  Backend       Claude Code -> Ollama (fully local, no cloud)"
echo ""
echo -e "  ${BOLD}Quick-start commands:${RESET}"
echo -e "  ${CYAN}>${RESET}  Start Claude Code (local AI):  ${BOLD}claude --model llama3.2:3b${RESET}"
echo -e "  ${CYAN}>${RESET}  Chat with model directly:      ${BOLD}ollama run llama3.2:3b${RESET}"
echo -e "  ${CYAN}>${RESET}  Open VS Code:                  ${BOLD}code .${RESET}"
echo -e "  ${CYAN}>${RESET}  Re-activate virtualenv:        ${BOLD}pyenv activate $VENV_NAME${RESET}"
echo ""
echo -e "  ${DIM}Full setup log saved at: $LOG_FILE${RESET}"
echo ""
