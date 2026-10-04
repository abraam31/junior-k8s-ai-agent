FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY junior/ junior/

EXPOSE 8000

# --host 0.0.0.0 is required so the port is reachable outside the container.
# uvicorn's default 127.0.0.1 only accepts connections from inside the image.
CMD ["uvicorn", "junior.api:app", "--host", "0.0.0.0", "--reload", "--port", "8000"]
