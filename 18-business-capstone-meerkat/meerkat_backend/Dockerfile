FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY meerkat_backend/pyproject.toml .
COPY meerkat_backend/app ./app
COPY meerkat_agent ./meerkat_agent
RUN pip install --no-cache-dir -e .
EXPOSE 8018
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8018"]
