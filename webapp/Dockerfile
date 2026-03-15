# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend + Claude Code CLI
FROM python:3.12-slim

# Install ffmpeg and Node.js (required by claude-agent-sdk)
RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally (required by claude-agent-sdk)
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (includes skills/ and .claude-plugin/)
COPY backend/ .

# Copy built frontend into static/
COPY --from=frontend-build /app/frontend/dist ./static

# Create workspaces directory
RUN mkdir -p workspaces

# Create non-root user (claude-agent-sdk requires non-root for bypassPermissions)
RUN useradd -m -s /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
