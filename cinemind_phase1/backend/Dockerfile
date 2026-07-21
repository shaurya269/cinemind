FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY backend/ backend/

# Data + artifacts are mounted at runtime by docker-compose (they're large
# and gitignored -- see .gitignore), not baked into the image.

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
