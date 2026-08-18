#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# bootstrap-linux.sh — One-command setup for TCG Market Intelligence on Linux
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
banner "  TCG Market Intelligence — Linux Bootstrap"
banner "============================================"

# -- Helper: check if running as root ---------------------------------------
if [[ "$(id -u)" -eq 0 ]]; then
    err "Do not run this script as root. It will use sudo when needed."
    exit 1
fi

# -- 1. Detect distro -------------------------------------------------------
IS_DEBIAN=false
if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    case "${ID:-}" in
        debian|ubuntu|linuxmint|pop|elementary|kali|raspbian)
            IS_DEBIAN=true
            info "Detected Debian-family distro: ${PRETTY_NAME:-$ID}"
            ;;
        fedora|rhel|centos|rocky|alma)
            warn "Detected RPM-based distro: ${PRETTY_NAME:-$ID}"
            warn "This script targets Debian/Ubuntu. You may need to adapt package names."
            ;;
        arch|manjaro)
            warn "Detected Arch-based distro: ${PRETTY_NAME:-$ID}"
            warn "This script targets Debian/Ubuntu. You may need to adapt package names."
            ;;
        *)
            warn "Unknown distro: ${PRETTY_NAME:-${ID:-unknown}}"
            warn "This script targets Debian/Ubuntu. You may need to install dependencies manually."
            ;;
    esac
else
    warn "Cannot detect distro (/etc/os-release missing)."
    warn "This script targets Debian/Ubuntu."
fi

# -- 2. Install system packages (Debian/Ubuntu) -----------------------------
find_python() {
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
NEED_INSTALL=false

if ! PYTHON_CMD="$(find_python)"; then
    NEED_INSTALL=true
fi

if ! command -v make &>/dev/null; then
    NEED_INSTALL=true
fi

if [[ "$IS_DEBIAN" == true && "$NEED_INSTALL" == true ]]; then
    info "Installing system packages via apt..."
    sudo apt update
    sudo apt install -y python3 python3-venv python3-pip make
    info "System packages installed."
elif [[ "$IS_DEBIAN" == false && "$NEED_INSTALL" == true ]]; then
    warn "Non-Debian system detected. Please install the following manually:"
    warn "  - Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} with venv support"
    warn "  - make"
    warn "Then re-run this script."
    if ! command -v make &>/dev/null; then
        err "make is not installed. Cannot continue."
        exit 1
    fi
fi

# -- 3. Verify Python version -----------------------------------------------
if PYTHON_CMD="$(find_python)"; then
    info "Python found: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
else
    err "Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} is not available after installation attempt."
    err "Your system Python may be too old. Consider using pyenv:"
    err "  curl https://pyenv.run | bash"
    err "  pyenv install 3.12"
    err "  pyenv global 3.12"
    err "Then re-run this script."
    exit 1
fi

# -- 4. Verify make ---------------------------------------------------------
if command -v make &>/dev/null; then
    info "make is available."
else
    err "make is not installed. Cannot continue."
    exit 1
fi

# -- 5. .env ----------------------------------------------------------------
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

# -- 6. make setup ----------------------------------------------------------
info "Running 'make setup'..."
make setup

# -- 7. Success -------------------------------------------------------------
banner "============================================"
banner "  Setup complete!"
banner "============================================"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Review and edit ${BOLD}.env${NC} if needed"
echo "  2. Run ${BOLD}make test${NC} to verify everything works"
echo "  3. Run ${BOLD}make run-backfill${NC} to start collecting data"
echo ""
