# 08 · 部署

> 从一键启动到完整三机部署，覆盖所有部署场景。

## 1. 部署场景

| 场景 | 机器 | 适用 |
|------|------|------|
| **单机局域网** | 任意一台机器 | 局域网内使用 |
| **单机 + 公网** | 同上 + Cloudflare Tunnel | 手机/外网访问 |
| **分层部署** | 主机 + 中转服务器 + GPU | 有独立 GPU 机器时 |

## 2. 单机部署

> 以下为说明性示例；**以仓库根目录的 `docker-compose.yml` 为准**（生产用预构建镜像
> `image: mnemo:latest`，开发态才 `build:` + 挂载源码，见 `docker-compose.dev.yml`）。

### docker-compose.yml

```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  api:
    build: ./api
    ports:
      - "8000:8000"
    volumes:
      - ${DATA_DIR:-./data}:/data
      - db_data:/db
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/data
      - DB_PATH=/db/analyzer.db
      - API_TOKEN=${API_TOKEN}
    depends_on:
      - redis
    restart: unless-stopped

  scheduler:
    build: ./scheduler
    volumes:
      - ${DATA_DIR:-./data}:/data
      - db_data:/db
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/data
      - DB_PATH=/db/analyzer.db
    depends_on:
      - redis
    restart: unless-stopped

  worker-download:
    build: ./worker
    command: python3 worker.py --type download
    volumes:
      - ${DATA_DIR:-./data}:/data
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/data
    security_opt:
      - no-new-privileges:true
    depends_on:
      - redis
    restart: unless-stopped

  worker-cpu:
    build: ./worker
    command: python3 worker.py --type cpu
    volumes:
      - ${DATA_DIR:-./data}:/data
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/data
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 4G
    depends_on:
      - redis
    restart: unless-stopped

  worker-ai:
    build: ./worker
    command: python3 worker.py --type ai
    volumes:
      - ${DATA_DIR:-./data}:/data
      # CLI 订阅用户取消下面的注释：
      # - ~/.claude:/home/user/.claude
      # - ~/.local/share/claude:/home/user/.local/share/claude:ro
      # - ~/.local/bin/claude:/usr/local/bin/claude:ro
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/data
      # API Key（按需配置，至少一个）
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY:-}
      - HTTPS_PROXY=${HTTPS_PROXY:-}
    security_opt:
      - no-new-privileges:true
    deploy:
      replicas: 2
    depends_on:
      - redis
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  redis_data:
  db_data:
```

### .env.example

```bash
# === 必填 ===
API_TOKEN=your-random-64-char-token

# === AI Provider API Keys (至少配一个) ===
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# DEEPSEEK_API_KEY=sk-...
# GOOGLE_API_KEY=AIza...

# === 路径 ===
DATA_DIR=./data

# === 代理 (访问 AI API 需要，无需代理可留空) ===
# HTTPS_PROXY=http://host.docker.internal:7890  # 访问外部 API 时使用，视网络环境配置
```

### 一键启动

```bash
cp .env.example .env
# 编辑 .env，填入 API_TOKEN
docker compose up -d
# 访问 http://localhost:3000
```

## 3. 加公网：Cloudflare Tunnel

在主机 docker-compose.yml 中加一个 cloudflared 容器：

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    restart: unless-stopped
```

Cloudflare Dashboard 配置：
1. 创建 Tunnel，获取 Token
2. 配置路由：`video-notes.yourdomain.com` → `http://api:8000`
3. 开启 Cloudflare Access（邮箱验证）

前端静态文件也通过 API 服务返回（或单独配一条 Tunnel 路由到 frontend:80）。

### .env 追加

```bash
CLOUDFLARE_TUNNEL_TOKEN=your-tunnel-token
```

## 4. 分层部署：主机 + 中转 + GPU

### 中转服务器 docker-compose.yml

```yaml
services:
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --tls-port 6380
      --port 0
      --tls-cert-file /tls/redis.crt
      --tls-key-file /tls/redis.key
      --tls-ca-cert-file /tls/ca.crt
      --rename-command CONFIG ""
      --rename-command EVAL ""
      --rename-command SCRIPT ""
      --appendonly yes
    ports:
      - "6380:6380"
    volumes:
      - redis_data:/data
      - ./tls:/tls:ro
    restart: unless-stopped

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    restart: unless-stopped

volumes:
  redis_data:
  minio_data:
```

### GPU 机器启动命令

> **audio/播客流水线需要 whisper-capable worker**：`00b_whisper` 步在 `gpu` 池，仅由 `--type gpu` 且装了 `[gpu]` 依赖（faster-whisper）的 worker 执行；该 worker 在无 GPU 的机器上用 CPU（int8）转写，较慢但可用。若集群无此 worker，含音频/无字幕视频的 job 会在约 90s 后 fail-fast 报「无可用 worker」而非永久挂起。默认 `docker compose up` 只起 download/cpu/ai worker，不含 whisper worker。

现行接入走 worker-gateway 单出站 HTTPS（见 [ADR-0009](adr/0009-worker-gateway-outbound-https.md)）：
GPU 机只需能出站访问主机 API，不暴露任何入站端口、不直连 Redis/MinIO。

whisper 需 `[gpu]` 依赖(faster-whisper)，base 镜像未含——先构建一个带该 extra 的镜像：

```dockerfile
FROM ghcr.io/${IMAGE_OWNER:-gwzlchn}/mnemo:latest
RUN pip install --no-cache-dir ".[gpu]"
```

```bash
docker run -d --gpus all \
  --name mnemo-gpu-worker \
  -e GATEWAY_URL=https://<主机域名> \
  -e WORKER_REGISTRATION_TOKEN=<管理页铸造的接入 token> \
  -e IDLE_TIMEOUT=600 \
  --tmpfs /tmp:size=2G \
  --memory 8g \
  --security-opt no-new-privileges:true \
  <上面构建的镜像> \
  python -m worker.main --type gpu
```

一条命令接入，纯出站 HTTPS，空闲 10 分钟自动退出；删除 worker 即吊销其 token。

> 旧的「中转 Redis(TLS)+MinIO」直连模型见上方 compose，已被网关模型取代，仅在需要 worker 直连内部组件时保留。

## 5. 首次使用引导

```
1. docker compose up -d          → 全套服务启动
2. 浏览器打开 http://localhost:3000 (或公网域名)
3. 设置 → B站 → 扫码登录        → 解锁 1080P
4. 首页 → 粘贴 B站 URL → 投递    → 第一个任务开始处理
5. 等待 ~20 分钟                  → 查看笔记
```

## 6. 升级

```bash
git pull
docker compose build
docker compose up -d
# Redis 数据持久化，不丢任务状态
```

## 7. 备份

```bash
# 关键数据
tar czf backup-$(date +%Y%m%d).tar.gz \
  data/jobs/ \
  data/db/ \
  data/cookies/ \
  data/prompts/ \
  .env

# 恢复
tar xzf backup-20260516.tar.gz
docker compose up -d
```

视频文件体积大，可以只备份 `data/db/` + `data/jobs/*/output/`（笔记产物），视频丢了可以重新下载。
