FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy core engine (read-only)
COPY ODI-based-multi-agent-Framework/ /app/ODI-based-multi-agent-Framework/

# Copy backend
COPY backend/ /app/backend/

# Copy frontend
COPY frontend-react/ /app/frontend-react/

# Copy environment
COPY .env /app/.env

# Set env
ENV PYTHONPATH=/app/backend
ENV CORE_ENGINE_PATH=/app/ODI-based-multi-agent-Framework

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
