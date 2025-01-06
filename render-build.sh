#!/usr/bin/env bash
set -e

# Update pip
pip install --upgrade pip

# Set Playwright browser path
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/ms-playwright"

# Install Playwright with specific version
pip install --upgrade playwright==1.49.1

# Install only Chromium browser with dependencies
playwright install --with-deps chromium

# Verify installation
echo "Verifying Playwright installation..."
if playwright --version; then
    echo "Playwright installation successful"
else
    echo "Playwright installation failed"
    exit 1
fi

# List browser path contents
echo "Checking browser installation..."
if [ -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then
    echo "Browser directory exists at $PLAYWRIGHT_BROWSERS_PATH"
    ls -la "$PLAYWRIGHT_BROWSERS_PATH"
else
    echo "Browser directory not found"
    exit 1
fi