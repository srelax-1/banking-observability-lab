FROM python:3.12-slim

WORKDIR /load-generator

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY locustfile.py .

EXPOSE 8089

CMD ["locust", "-f", "locustfile.py", "--host", "http://api-gateway:8000"]
