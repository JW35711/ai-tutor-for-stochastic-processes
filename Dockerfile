FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/artifacts \
    && chown -R appuser:appuser /app/artifacts

USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2).read()"

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8000"]
