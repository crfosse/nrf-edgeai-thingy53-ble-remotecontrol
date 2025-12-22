#!/bin/bash
# Script to install dependencies and clone the repository for Neuton Nordic Thingy53 BLE Remote Control project
# Basic testing performed on Ubuntu 24.04 and Fedora
set -euo pipefail
trap 'echo "Error on line $LINENO"; exit 1' ERR

REPO_URL="git@github.com:Neuton-tinyML/neuton-nordic-thingy53-ble-remotecontrol.git"
TARGET_DIR="neuton-nordic-thingy53-ble-remotecontrol"
REPO_BRANCH="feature/custom-ble-gatt"

# Use sudo only if not running as root, to allow testing in Ubuntu
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

if ! command -v git >/dev/null 2>&1; then
    echo "git is not installed. Attempting to install..."

    if command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update
        $SUDO apt-get install -y git
    elif command -v yum >/dev/null 2>&1; then
        $SUDO yum install -y git
    elif command -v dnf >/dev/null 2>&1; then
        $SUDO dnf install -y git
    else
        echo "No supported package manager found. Please install git manually."
        exit 1
    fi
else
    echo "git is already installed."
fi

# Install uv if not already installed
if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Installing uv..."
    if ! command -v curl >/dev/null 2>&1; then
        echo "curl is not installed. Attempting to install..."

        if command -v apt-get >/dev/null 2>&1; then
            $SUDO apt-get update
            $SUDO apt-get install -y curl
        elif command -v yum >/dev/null 2>&1; then
            $SUDO yum install -y curl
        elif command -v dnf >/dev/null 2>&1; then
            $SUDO dnf install -y curl
        else
            echo "No supported package manager found. Please install curl manually."
            exit 1
        fi
    else
        echo "curl is already installed."
    fi
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env
else
    echo "uv is already installed."
fi

if ! command -v git >/dev/null 2>&1; then
    echo "git is not installed. Attempting to install..."

    if command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update
        $SUDO apt-get install -y git
    elif command -v dnf >/dev/null 2>&1; then
        $SUDO dnf install -y git
    elif command -v yum >/dev/null 2>&1; then
        $SUDO yum install -y git
    else
        echo "No supported package manager found. Please install git manually."
        exit 1
    fi
else
    echo "git is already installed."
fi

if command -v apt-get >/dev/null 2>&1; then
    if ! dpkg -s bluez >/dev/null 2>&1; then
        $SUDO apt update
        $SUDO apt install -y bluez
    else
        echo "BlueZ is already installed."
    fi
elif command -v dnf >/dev/null 2>&1; then
    if ! dnf list installed bluez >/dev/null 2>&1; then
        $SUDO dnf install -y bluez
    else
        echo "BlueZ is already installed."
    fi
elif command -v yum >/dev/null 2>&1; then
    if ! yum list installed bluez >/dev/null 2>&1; then
        $SUDO yum install -y bluez
    else
        echo "BlueZ is already installed."
    fi
else
    echo "No supported package manager found. Please install BlueZ BLE stack manually."
    exit 1
fi

if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "The current folder is a Git checkout, we assume it is the code we want to run. If this is not the case, run the script from another location."
  cd "$(git rev-parse --show-toplevel)"
else
    if [ ! -d "$TARGET_DIR" ]; then
        echo "Cloning repository into $TARGET_DIR..."
        git clone "$REPO_URL" "$TARGET_DIR"
    else
        echo "Directory $TARGET_DIR already exists. Skipping clone. Delete the directory to re-clone."
    fi
    cd $TARGET_DIR
fi

git checkout $REPO_BRANCH
echo "Pulling latest changes from branch $REPO_BRANCH..."
git pull origin $REPO_BRANCH

cd demo
uv sync

CMD="uv run --project $(pwd) $(pwd)/uiapp_ble.py"

# Define the desktop entry path (for the current user)
if [ -d "$HOME/.local/share/applications/" ]; then
    DESKTOP_ENTRY="$HOME/.local/share/applications/uv-uiapp-ble.desktop"

    # Create the .desktop file
    cat > "$DESKTOP_ENTRY" <<EOF
[Desktop Entry]
Type=Application
Name=Neuton remote demo
Comment=Neuton remote control BLE demo application
Exec=$CMD
Icon=utilities-terminal
Terminal=true
Categories=Utility;
EOF
    chmod +x "$DESKTOP_ENTRY"
    echo "Desktop entry created at $DESKTOP_ENTRY"
fi

echo "To launch the UI application, run the following command or launch via Desktop entry:"
echo $CMD
echo "Launching the UI application now..."
$CMD
