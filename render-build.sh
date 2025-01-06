#!/usr/bin/env bash
set -e

# Update pip
pip install --upgrade pip

# Set environment variables for Playwright
export PLAYWRIGHT_BROWSERS_PATH="/opt/render/project/.playwright"
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
export PLAYWRIGHT_SKIP_VALIDATION=1

# Install Playwright
pip install playwright==1.49.1

# Create browser directory if it doesn't exist
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

# Install browser without attempting to use root
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 playwright install chromium --with-deps 2>&1 || {
    echo "Standard installation failed, trying alternative installation..."
    
    # Try alternative installation without system dependencies
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    PLAYWRIGHT_SKIP_VALIDATION=1 \
    playwright install chromium 2>&1 || {
        echo "Browser installation failed. Continuing anyway as browser might be cached..."
    }
}

# Verify installation
echo "Verifying Playwright installation..."
playwright --version

# List installed browsers
echo "Checking browser installation directory..."
ls -la "$PLAYWRIGHT_BROWSERS_PATH" || true

echo "Build script completed"