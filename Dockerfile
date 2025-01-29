FROM python:3.11 AS base

RUN apt-get update && apt-get install -y libnss3\
	libnspr4\
	libdbus-1-3\
	libatk1.0-0\
	libatk-bridge2.0-0\
	libatspi2.0-0\
	libxcomposite1\
	libxdamage1\
	libxfixes3\
	libxrandr2\
	libgbm1\
	libdrm2\
	libxkbcommon0\
	libcups2\
	libasound2

FROM base AS api-builder

WORKDIR /app

# Install all requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Setup playwright and install browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright-browsers
RUN playwright install chromium chromium-headless-shell

# Run script to check playwright installation
COPY check_playwright_installation.sh .
RUN chmod +x check_playwright_installation.sh
RUN ./check_playwright_installation.sh

# Copy the code
COPY . .

ENV PORT=8000
EXPOSE 8000

# Run API
CMD exec gunicorn --bind :$PORT app:app
