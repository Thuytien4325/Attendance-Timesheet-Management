FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# --- THÊM DÒNG NÀY ---
# Để code Python bên trong biết phải kết nối ra ngoài máy thật
ENV DB_HOST_ENV=host.docker.internal

# Cài đặt thư viện hệ thống (Fix lỗi thư viện ảnh và C++)
RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    make \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt thư viện Python
RUN pip install --no-cache-dir \
    flask \
    sqlalchemy \
    flask-sqlalchemy \
    mysql-connector-python \
    pymysql \
    cryptography \
    qrcode \
    pillow \
    numpy \
    face_recognition \
    opencv-python-headless

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]