FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY apps/api ./apps/api
RUN pip install --no-cache-dir --retries 5 --timeout 120 -e ./apps/api
RUN addgroup --system threadpilot \
    && adduser --system --ingroup threadpilot threadpilot \
    && chown -R threadpilot:threadpilot /app
ENV PYTHONPATH=/app/apps/api:/app
WORKDIR /app/apps/api
USER threadpilot
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
