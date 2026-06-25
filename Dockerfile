FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY memcell_rl ./memcell_rl

EXPOSE 8000

CMD ["uvicorn", "memcell_rl.app:app", "--host", "0.0.0.0", "--port", "8000"]
