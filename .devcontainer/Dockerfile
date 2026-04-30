FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y curl ca-certificates git build-essential make python3-pip sed ed patch grep coreutils openssh-server libreoffice-writer default-jre-headless fonts-noto-cjk \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/run/sshd \
    && echo 'root:password' | chpasswd \
    && echo 'vscode:vscode' | chpasswd \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode

RUN su - vscode -c "libreoffice --headless --terminate_after_init" 2>/dev/null || true \
    && rm -rf /home/vscode/.config/libreoffice

RUN pip3 install --no-cache-dir uv
RUN npm install -g @openai/codex --no-progress
