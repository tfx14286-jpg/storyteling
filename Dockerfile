FROM python:3.11-slim

# Install FFmpeg (wajib untuk MoviePy)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render set PORT env, Gradio harus pakai itu
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["python", "app.py"]
