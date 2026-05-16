FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Logs unbuffered → visible avec `docker logs` en temps réel.
CMD ["python", "-u", "main.py"]
