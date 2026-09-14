# Placeholder Dockerfile for Junior.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY junior/ junior/

# TODO: switch to the real entrypoint (e.g. uvicorn junior.api:app) once api.py
# serves the /ask endpoint.
CMD ["python", "-m", "junior.agent"]
