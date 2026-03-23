FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir psycopg2-binary

COPY redundancy_daemon.py .

CMD ["python", "-u", "redundancy_daemon.py"]
