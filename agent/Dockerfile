FROM python:3.12.3-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY metrics.py .
COPY agent.py .

RUN mkdir logs buffer

CMD ["python", "agent.py"]