FROM hubproxy.zhufudea.ggff.net/python:3.11-slim

WORKDIR /app

ENV TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

# 设置时区
RUN ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要目录
RUN mkdir -p data output/audio

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
