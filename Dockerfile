# Dockerfile
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖（如编译依赖）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并预安装（利用缓存加速后续构建）
COPY requirements.txt .

# 升级 pip 并安装生产依赖到用户目录
RUN pip install --upgrade pip && \
    pip install --user -r requirements.txt


# 第二阶段：运行时镜像
FROM python:3.11-slim

# 防止 Python 输出使用缓冲
ENV PYTHONUNBUFFERED=1

# 设置时区为上海（确保业务逻辑按北京时间执行）
ENV TZ=Asia/Shanghai

# 创建非 root 用户（安全最佳实践）
RUN groupadd -r trader && useradd -r -g trader trader && \
    mkdir /app && chown trader:trader /app

# 切换到非 root 用户
USER trader

# 设置工作目录
WORKDIR /app

# 从上一阶段复制已安装的包
COPY --from=builder --chown=trader:trader /root/.local /root/.local

# 复制应用代码
COPY --chown=trader:trader . .

# 确保可执行权限
RUN chmod +x app.py

# 将用户级 pip 路径加入 PATH
ENV PATH=/root/.local/bin:$PATH

# 暴露端口
EXPOSE 8080

# 启动命令（使用 gunicorn）
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--worker-class", "sync", "wsgi:application"]