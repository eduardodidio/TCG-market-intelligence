#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# bootstrap-mac.sh — One-command setup for TCG Market Intelligence on macOS
# ---------------------------------------------------------------------------

REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=11
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# -- Colors -----------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()     { echo -e "${RED}[ERR]${NC}  $*"; }
banner()  { echo -e "\n${BOLD}$*${NC}\n"; }

# -- Banner -----------------------------------------------------------------
banner "============================================"
banner "  TCG Market Intelligence — macOS Bootstrap"
banner "============================================"

# -- 1. Homebrew ------------------------------------------------------------
if command -v brew &>/dev/null; then
    info "Homebrew is already installed."
else
    warn "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Ensure brew is on PATH for the rest of this script
    if [[ -x /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    info "Homebrew installed."
fi

# -- 2. Python >= 3.11 -----------------------------------------------------
find_python() {
    # Check common python commands for a suitable version
    for cmd in python3.14 python3.13 python3.12 python3.11 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver="$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)" || continue
            local major minor
            major="${ver%%.*}"
            minor="${ver##*.}"
            if [[ "$major" -eq "$REQUIRED_PYTHON_MAJOR" && "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD=""
if PYTHON_CMD="$(find_python)"; then
    info "Python found: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
else
    warn "Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} not found. Installing via Homebrew..."
    # Try from highest to lowest
    INSTALLED=false
    for formula in python@3.14 python@3.13 python@3.12 python@3.11; do
        if brew install "$formula" 2>/dev/null; then
            INSTALLED=true
            info "Installed $formula via Homebrew."
            break
        fi
    done
    if [[ "$INSTALLED" == false ]]; then
        err "Could not install Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} via Homebrew."
        err "Please install Python manually or use pyenv:"
        err "  curl https://pyenv.run | bash"
        err "  pyenv install 3.12"
        exit 1
    fi
    # Re-check
    if PYTHON_CMD="$(find_python)"; then
        info "Python ready: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
    else
        err "Python was installed but cannot be found on PATH."
        err "Try restarting your terminal or adding Homebrew to your PATH."
        exit 1
    fi
fi

# -- 3. make (Xcode CLI tools) ---------------------------------------------
if command -v make &>/dev/null; then
    info "make is already installed."
else
    warn "make not found. Installing Xcode Command Line Tools..."
    xcode-select --install 2>/dev/null || true
    echo "    Please complete the Xcode CLT installation dialog, then re-run this script."
    exit 1
fi

# -- 4. .env ----------------------------------------------------------------
cd "$PROJECT_ROOT"

if [[ -f .env ]]; then
    info ".env already exists — skipping copy."
else
    if [[ -f .env.example ]]; then
        cp .env.example .env
        info "Created .env from .env.example."
    else
        warn ".env.example not found — skipping .env creation."
    fi
fi

# -- 5. make setup ----------------------------------------------------------
info "Running 'make setup'..."
make setup

# -- 6. Success -------------------------------------------------------------
banner "============================================"
banner "  Setup complete!"
banner "============================================"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Review and edit ${BOLD}.env${NC} if needed"
echo "  2. Run ${BOLD}make test${NC} to verify everything works"
echo "  3. Run ${BOLD}make run-backfill${NC} to start collecting data"
echo ""
