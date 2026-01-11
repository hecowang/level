# 构建阶段（安装依赖）
FROM python:3.13-slim AS builder
WORKDIR /service

# 设置时区为上海
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行阶段（复制必要文件）
FROM python:3.13-slim AS runtime
WORKDIR /service

# 设置时区为上海
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制依赖
COPY --from=builder /root/.local /root/.local
COPY app/ ./app
COPY assets ./assets
COPY .env ./

# 确保可执行文件路径正确
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8606
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8606"]
