# backend/Dockerfile
# 多阶段可省略（后端无需 build），这里用 python:3.13-slim + uv。
# 用法：在仓库根目录构建  docker build -f backend/Dockerfile -t dps-backend ./backend
FROM python:3.13-slim

# 国内源加速（与 .devcontainer/Dockerfile 保持一致，避免 apt/pip/uv 下载慢）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
ENV UV_DEFAULT_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# 运行时最小依赖：curl 供 HEALTHCHECK 使用
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# 安装 uv（官方镜像）。建议钉版本（如 ghcr.io/astral-sh/uv:0.8.0，与你 devbox 的 `uv --version` 一致），
# 避免不同时间 build 时 uv 解析行为漂移导致"本地能跑、CI 炸"。
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# 1) 先装依赖，利用层缓存（只复制锁文件）
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen

# 2) 再复制源码并安装项目本身
COPY src ./src
# alembic 迁移所需（部署阶段要在容器里跑 alembic upgrade head）
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
RUN uv sync --no-dev --frozen
# 迁移工具 alembic 仅部署期需要：运行时用 --no-dev 不装它，这里单独装入 venv
# （显式指向 .venv，避免 UV_SYSTEM_PYTHON=1 装到系统 Python）
RUN uv pip install --python /app/.venv alembic
ENV PATH=/app/.venv/bin:$PATH

# 3) 暴露端口（与 uvicorn --port 一致）
EXPOSE 8000

# 健康检查：后端已有 GET /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# 生产用多 worker；ENV/密钥通过 docker run -e 或 compose 注入，不要写进镜像
CMD ["uvicorn", "doc_process_studio.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
