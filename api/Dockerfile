
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

ENV PYTHONPATH=/app


RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api ./api
COPY core ./core
COPY compliance ./compliance

# Copy environment file
COPY .env ./

EXPOSE 8080

# KEY CHANGE: Run core/main.py, not api/main.py
CMD ["uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8080"]

