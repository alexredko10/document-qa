FROM python:3.12-slim
RUN useradd --uid 10001 --create-home operator
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
USER 10001
ENTRYPOINT ["kopf", "run", "--all-namespaces", "--liveness=http://0.0.0.0:8080/healthz", "main.py"]
