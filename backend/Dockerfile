FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
# This is the local development image, including test/lint dependencies.
RUN pip install -r requirements.txt
# Fail the image build if the pinned local OCR runtime/models cannot initialize.
RUN python -c "from rapidocr import RapidOCR; RapidOCR()"
COPY . .
RUN useradd --create-home app && mkdir -p /app/archive/originals /app/archive/derivatives /app/archive/text && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
