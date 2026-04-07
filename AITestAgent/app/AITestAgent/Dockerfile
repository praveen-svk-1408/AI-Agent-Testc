FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# AgentCore runtime entrypoint
CMD ["python", "main.py"]
