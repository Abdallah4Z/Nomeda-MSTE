FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ser_model.py .
COPY service.py .
COPY .env.example .env

EXPOSE 8002

CMD ["python", "service.py"]
