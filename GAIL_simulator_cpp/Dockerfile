# Dockerfile
FROM ubuntu:22.04

# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 安装基础依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    unzip \
    pkg-config \
    libyaml-cpp-dev \
    python3-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制源代码
COPY . .

# 创建构建目录
RUN mkdir -p build

# 构建项目
WORKDIR /app/build
RUN cmake .. && make -j$(nproc)

# 创建运行时需要的目录
RUN mkdir -p /app/logs /app/results /app/config

# 设置入口点
WORKDIR /app
CMD ["./build/gail_simulator"]