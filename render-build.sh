#!/usr/bin/env bash
set -e

# System dependencies
apt-get update
apt-get install -y \
    libwoff1 \
    libopus0 \
    libwebp7 \
    libwebpdemux2 \
    libenchant1c2a \
    libgudev-1.0-0 \
    libsecret-1-0 \
    libhyphen0 \
    libgdk-pixbuf2.0-0 \
    libegl1 \
    libnotify4 \
    libxslt1.1 \
    libevent-2.1-7 \
    libgles2 \
    libvpx7

# Python dependencies
pip install --upgrade pip
pip install --upgrade "playwright>=1.25.0"

# Install browsers with dependencies
playwright install-deps
playwright install chromium

# Verify Playwright installation
if ! playwright --version > /dev/null 2>&1; then
    echo "Playwright installation failed"
    exit 1
fi

echo "Playwright installation completed successfully"