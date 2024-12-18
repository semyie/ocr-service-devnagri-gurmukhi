FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-all \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY dependencies.txt .
RUN pip install --no-cache-dir -r dependencies.txt
RUN pip install fastapi uvicorn

COPY . .

RUN python --version && pip --version

RUN ls -l /usr/local/bin

RUN pip show uvicorn && which uvicorn

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--reload"]