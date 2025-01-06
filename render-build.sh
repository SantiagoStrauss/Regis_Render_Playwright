# filepath: /C:/Users/david/Documents/LISTAS PYTHON/LISTAS PYTHON/simit - Playwright/render-build.sh
#!/usr/bin/env bash
set -e

# Set Playwright browsers path to a directory within the project
export PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers

# Actualizar pip
pip install --upgrade pip

# Instalar Playwright
pip install --upgrade "playwright>=1.25.0"

# Instalar navegadores y dependencias de Playwright en el directorio especificado
PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers playwright install

# Verificar la instalación de Playwright
if ! PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers playwright --version > /dev/null 2>&1; then
    echo "La instalación de Playwright falló"
    exit 1
fi

echo "Instalación de Playwright completada exitosamente"