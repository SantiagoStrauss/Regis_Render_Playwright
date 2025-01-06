#!/usr/bin/env bash
set -e

# Update package lists and install system dependencies
apt-get update && apt-get install -y \
    libgstgl-1.0-0 \
    libgstcodecparsers-1.0-0 \
    libavif15 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2 \
    # Additional dependencies for Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2

# Update pip
pip install --upgrade pip

# Set Playwright browser path
export PLAYWRIGHT_BROWSERS_PATH="/opt/render/.cache/ms-playwright"

# Install Playwright with specific version
pip install playwright==1.40.0

# Force browser download with specific parameters
PLAYWRIGHT_BROWSERS_PATH="/opt/render/.cache/ms-playwright" playwright install chromium --with-deps

# Verify Playwright installation
if playwright --version; then
    echo "Playwright installation verified successfully"
else
    echo "Playwright installation verification failed"
    exit 1
fi

# Verify browser installation
if [ -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then
    echo "Browser directory exists at $PLAYWRIGHT_BROWSERS_PATH"
    ls -la "$PLAYWRIGHT_BROWSERS_PATH"
else
    echo "Browser directory not found at $PLAYWRIGHT_BROWSERS_PATH"
    exit 1
fi