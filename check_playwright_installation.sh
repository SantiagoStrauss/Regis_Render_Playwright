#!/usr/bin/env bash
set -e

# Verificar la instalación de Playwright
if ! playwright --version > /dev/null 2>&1; then
    echo "La instalación de Playwright falló"
    exit 1
fi

echo "Instalación de Playwright completada exitosamente"