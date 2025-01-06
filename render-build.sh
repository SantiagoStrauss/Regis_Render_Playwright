#!/usr/bin/env bash
set -e

# Update pip
pip install --upgrade pip

# Install Flask and Playwright
pip install flask playwright==1.49.1

# Set environment variables
export PLAYWRIGHT_BROWSERS_PATH="/opt/render/project/.playwright"
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
export PLAYWRIGHT_SKIP_VALIDATION=1

# Create browser directory with proper permissions
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
chmod -R 777 "$PLAYWRIGHT_BROWSERS_PATH"

# Install browsers
python -m playwright install chromium --with-deps || {
    echo "Standard installation failed, trying alternative..."
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    PLAYWRIGHT_SKIP_VALIDATION=1 \
    python -m playwright install chromium
}

# Verify installation
python -m playwright --version

# List installed browsers
ls -la "$PLAYWRIGHT_BROWSERS_PATH"

echo "Build script completed"