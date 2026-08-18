# Setup Guide

Step-by-step instructions to get TCG Market Intelligence running on your machine.

## Prerequisites

| Tool       | Minimum version | Notes                         |
|------------|-----------------|-------------------------------|
| Python     | 3.11            | 3.12, 3.13, 3.14 also work   |
| make       | any             | GNU Make recommended          |
| git        | any             | For cloning the repository    |

## Quick Start (macOS)

```bash
git clone https://github.com/eduardodidio/TCG-market-intelligence.git
cd TCG-market-intelligence
./bin/bootstrap-mac.sh
```

The bootstrap script will:
- Install Homebrew if missing
- Install Python >= 3.11 via Homebrew if missing
- Verify `make` is available (installs Xcode CLI Tools if needed)
- Copy `.env.example` to `.env` if `.env` does not exist
- Run `make setup` (creates venv, installs all dependencies)

## Quick Start (Linux)

```bash
git clone https://github.com/eduardodidio/TCG-market-intelligence.git
cd TCG-market-intelligence
./bin/bootstrap-linux.sh
```

The bootstrap script will:
- Detect your distro (optimized for Debian/Ubuntu)
- Install `python3`, `python3-venv`, `python3-pip`, and `make` via apt if needed
- Copy `.env.example` to `.env` if `.env` does not exist
- Run `make setup` (creates venv, installs all dependencies)

**Note:** On non-Debian distros (Fedora, Arch, etc.) you may need to install
Python >= 3.11, venv support, and make manually before running the script.

## Manual Setup

If you prefer not to use the bootstrap scripts, follow these steps:

```bash
# 1. Clone the repository
git clone https://github.com/eduardodidio/TCG-market-intelligence.git
cd TCG-market-intelligence

# 2. Create a virtual environment and install dependencies
make setup
# This runs: python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# 3. (Optional) Copy the env file
cp .env.example .env   # edit as needed
```

If `make` is not available, you can run the commands directly:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Verify Installation

Run the test suite and linter to confirm everything is wired up correctly:

```bash
make test
make lint
```

Expected output:
- `make test` -- all 27+ tests pass (pytest, verbose mode)
- `make lint` -- no ruff errors

## First Run

Backfill price history for a small set of cards to verify end-to-end:

```bash
make run-backfill SET=dominaria-remastered LIMIT=5
```

This will scrape 5 cards from the Dominaria Remastered set on MYP Cards and
store price observations in a local SQLite database (`tcg_market.db`).

## Troubleshooting

### Cloudflare 403 errors

MYP Cards is behind Cloudflare. The project uses `curl_cffi` with browser
impersonation to bypass this. If you get 403 errors:

- Make sure `curl_cffi` is installed (`pip show curl_cffi`)
- Update to the latest version: `.venv/bin/pip install --upgrade curl_cffi`
- The provider uses `impersonate="chrome"` -- this is configured automatically

### Python version too old

The project requires Python >= 3.11. Check your version:

```bash
python3 --version
```

If it is below 3.11, install a newer version:

- **macOS:** `brew install python@3.12`
- **Ubuntu/Debian:** `sudo apt install python3.12 python3.12-venv`
- **Any OS:** Use [pyenv](https://github.com/pyenv/pyenv):
  ```bash
  curl https://pyenv.run | bash
  pyenv install 3.12
  pyenv global 3.12
  ```

### `make setup` fails with "python: command not found"

The Makefile uses `python` (not `python3`). If your system only has `python3`,
either:
- Create a symlink: `sudo ln -s $(which python3) /usr/local/bin/python`
- Or use the bootstrap scripts which handle this automatically

### venv creation fails on Ubuntu

Ubuntu may not ship `python3-venv` by default:

```bash
sudo apt install python3-venv
```
