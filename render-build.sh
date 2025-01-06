#!/usr/bin/env bash
set -e

# Actualizar pip
pip install --upgrade pip

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