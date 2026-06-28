FROM python:3.11-slim

WORKDIR /app

RUN pip install requests transformers torch

COPY app.py .

CMD ["python", "app.py"]