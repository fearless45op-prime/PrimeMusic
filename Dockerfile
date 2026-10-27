FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV DENO_INSTALL=/usr/local/deno
ENV PATH="/usr/local/deno/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg unzip gcc git curl procps ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN mkdir -p "${DENO_INSTALL}" \
    && curl -fsSL https://deno.land/install.sh | sh

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

EXPOSE 10000
CMD ["python3", "-u", "render_start.py"]
