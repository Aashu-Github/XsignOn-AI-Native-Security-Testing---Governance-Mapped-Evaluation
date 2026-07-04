FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# OPENAI_API_KEY (or your judge provider's key) is injected at runtime via
# k8s Secret, not baked into the image. Same for any gateway auth token.
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "layer4.runner"]
CMD ["--suite", "suite.yaml"]
