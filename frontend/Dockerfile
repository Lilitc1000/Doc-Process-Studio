# frontend/Dockerfile
# 多阶段：node 构建 dist -> nginx 托管 + 反代 /api
# 用法：在 frontend/ 目录构建  docker build -f Dockerfile -t dps-frontend ./frontend
FROM node:22-slim AS build
# 国内源加速（与 .devcontainer/Dockerfile 保持一致）
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build   # 产出 dist/

FROM nginx:1.27-alpine AS runtime
# SPA + /api 反向代理配置
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
CMD ["nginx", "-g", "daemon off;"]
