#!/usr/bin/env bash
set -e

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias del sistema necesarias para Playwright
apt-get update && apt-get install -y \
    libgstgl-1.0-0 \
    libgstcodecparsers-1.0-0 \
    libavif15 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2

# Configurar la ruta de los navegadores de Playwright
export PLAYWRIGHT_BROWSERS_PATH=0

# Instalar Playwright
pip install --upgrade "playwright>=1.25.0"

# Instalar navegadores y dependencias de Playwright
playwright install

# Verificar la instalación de Playwright
if ! playwright --version > /dev/null 2>&1; then
    echo "La instalación de Playwright falló"
    exit 1
fi

echo "Instalación de Playwright completada exitosamente"