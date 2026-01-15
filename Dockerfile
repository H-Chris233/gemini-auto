# ============================================
# 构建阶段：编译前端资源
# ============================================
FROM node:20-alpine AS builder

WORKDIR /build

# 复制前端依赖
COPY frontend/package*.json ./
RUN npm install

# 复制前端源码
COPY frontend/ ./

# 构建前端
RUN npm run build

# 将构建产物移动到 /build/static 供后续 COPY 使用
RUN mv /app/static /build/static

# ============================================
# 运行阶段：生产环境容器
# ============================================
FROM python:3.11-slim AS runtime

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 安装 Chrome/Chromium 和必要依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libasound2t64 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libxshmfence1 \
    fonts-liberation \
    xdg-utils \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f -y \
    && rm -f google-chrome-stable_current_amd64.deb

# 安装 ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+' | head -1) && \
    CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip && \
    unzip -q /tmp/chromedriver.zip -d /opt/ && \
    mv /opt/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /opt/chromedriver-linux64

# 设置 Chrome 为默认浏览器
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV CHROME_BIN=/usr/bin/google-chrome

# 创建非 root 用户
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

# 复制 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 复制构建好的前端资源
COPY --from=builder /build/static ./static/

# 复制 Nginx 配置
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# 创建 Nginx 所需的目录 (root 用户创建)
RUN mkdir -p /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi /var/lib/nginx/uwsgi /var/lib/nginx/scgi && \
    chown -R appuser:appuser /var/lib/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /etc/nginx && \
    mkdir -p /var/run/nginx && \
    chown appuser:appuser /var/run/nginx

# 切换到非 root 用户
USER appuser

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8080

# 启动脚本
ENTRYPOINT ["/entrypoint.sh"]
