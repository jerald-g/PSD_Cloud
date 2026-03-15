FROM python:3.12-slim

WORKDIR /app

# WeasyPrint system dependencies for HTML-to-PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev libcairo2 libglib2.0-0 fontconfig fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Build system font cache and create writable user cache
RUN fc-cache -fv && \
    mkdir -p /home/appuser/.cache/fontconfig && \
    chown -R appuser:appgroup /home/appuser

ENV XDG_CACHE_HOME=/home/appuser/.cache

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "generator:app", "--host", "0.0.0.0", "--port", "8000"]
