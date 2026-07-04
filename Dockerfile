# Minimal image — just enough to run the CLI, nothing else bundled.
FROM python:3.11-slim

WORKDIR /app

# Install deps first so this layer is cached across code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# logs/ needs to exist and be writable at runtime
RUN mkdir -p logs

ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
