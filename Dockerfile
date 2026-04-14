FROM python:3.11-slim

WORKDIR /app

# 依赖层（先复制，利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 源码
COPY . .

# 确保 workspace 目录存在
RUN mkdir -p workspace/tasks workspace/outputs workspace/shared

EXPOSE 8000

CMD ["uvicorn", "web.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-keep-alive", "300", \
     "--workers", "1"]
