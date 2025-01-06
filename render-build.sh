#!/usr/bin/env bash
set -e

# Update pip
pip install --upgrade pip

# Set environment variables for Playwright
export PLAYWRIGHT_BROWSERS_PATH="/opt/render/project/.playwright"
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
export PLAYWRIGHT_SKIP_VALIDATION=1

# Install Playwright with specific version
pip install playwright==1.49.1

# Create browser directory with proper permissions
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
chmod -R 777 "$PLAYWRIGHT_BROWSERS_PATH"

# Attempt browser installation with different strategies
echo "Installing browsers..."
playwright install --with-deps chromium || {
    echo "First installation attempt failed, trying alternative method..."
    
    # Try installing without system dependencies
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    PLAYWRIGHT_SKIP_VALIDATION=1 \
    playwright install chromium || {
        echo "Second installation attempt failed, trying minimal installation..."
        
        # Try installing only the browser binary
        playwright install chromium --with-deps
    }
}

# Verify installation
echo "Verifying Playwright installation..."
playwright --version

# List installed browsers and permissions
echo "Checking browser installation directory..."
ls -la "$PLAYWRIGHT_BROWSERS_PATH"

# Ensure browser binaries are executable
find "$PLAYWRIGHT_BROWSERS_PATH" -type f -exec chmod +x {} \;

echo "Build script completed"