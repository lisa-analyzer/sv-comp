FROM python:3.13-slim

WORKDIR /app

COPY . .

ENV PYTHONPATH=/app/vendor/lib/python3.11/site-packages

# Default command
CMD ["python", "main.py"]