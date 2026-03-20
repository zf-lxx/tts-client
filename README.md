# TTS OPEN 管理平台

将多个 TTS 后端统一聚合在兼容 OpenAI 格式的 API 之后的管理平台。

## 功能特性

- **多渠道支持**：内置 Edge TTS（免费）、Azure 内置、火山引擎内置、纳米AI 内置，支持接入任意 OpenAI 兼容 TTS API
- **OpenAI 兼容**：`POST /api/v1/audio/speech` 完全兼容 OpenAI TTS API 格式
- **音色自动匹配**：调用时只传音色名，系统自动找到对应渠道（结果缓存 5 分钟）
- **渠道管理**：优先级配置、健康检查、CRUD 管理
- **历史记录**：保存最近 7 条生成记录，支持回放下载
- **认证保护**：所有 `/api/v1/*` 接口需要 API Key，前端登录态存于 `sessionStorage`
- **简约 UI**：左侧侧边栏导航，移动端自适应

## 快速开始

### 本地开发

```bash
# 安装依赖（需要 Python 3.12+ 和 uv）
uv sync

# 启动开发服务器（默认端口 59012）
uv run uvicorn main:app --reload
```

访问 `http://localhost:59012`，默认密码 `admin`。

### Docker 部署

```bash
docker-compose up
```

对外暴露 59012 端口，挂载 `./data` 和 `./output` 目录持久化数据。

## API 使用

所有 `/api/v1/*` 接口需要认证：

```bash
-H "Authorization: Bearer admin"
# 或
-H "X-API-Key: admin"
```

### 语音合成（OpenAI 兼容格式）

```bash
curl -X POST http://localhost:59012/api/v1/audio/speech \
  -H "Authorization: Bearer admin" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "你好世界",
    "voice": "zh-CN-XiaoxiaoNeural",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output speech.mp3
```

### 阅读 App 接口

```bash
curl -X POST http://localhost:59012/api/v1/tts/reading \
  -H "Authorization: Bearer admin" \
  -d 'speakText=你好世界&speakSpeed=25&voice=zh-CN-XiaoxiaoNeural' \
  --output reading.mp3
```

### 获取音色列表

```bash
curl -H "Authorization: Bearer admin" \
  http://localhost:59012/api/v1/voices?channel_id=<渠道ID>
```

## 支持的 TTS 渠道

| 渠道类型 | 说明 | 是否需要 Key |
|---|---|---|
| `openai` | OpenAI 官方及任意兼容接口 | 是 |
| `azure` | 微软翻译内置端点 | 否 |
| `edge` | Microsoft Edge TTS | 否 |
| `nami` | 纳米AI（bot.n.cn） | 否 |
| `custom` (volcengine) | 火山翻译内置端点 | 否 |

首次启动自动初始化 4 个内置渠道（Edge TTS、Azure、火山引擎、纳米AI）。

## 环境变量

```env
# 认证
ADMIN_PASSWORD=admin

# 服务
HOST=0.0.0.0
PORT=59012
DEBUG=false          # 生产环境设为 false，关闭 /docs 接口文档

# 数据目录（默认 ./data，只读文件系统时需修改）
DATA_DIR=/app/data
AUDIO_OUTPUT_DIR=/app/output/audio

# 日志
LOG_LEVEL=INFO
```

## 项目结构

```
├── main.py                    # 应用入口，认证中间件
├── config/
│   ├── settings.py            # 环境变量配置
│   └── logger.py              # 日志配置
├── routers/
│   ├── tts.py                 # TTS 相关接口
│   └── channels.py            # 渠道管理接口
├── services/
│   ├── tts_service.py         # TTSChannelManager，合成调度
│   ├── channel_service.py     # 渠道配置管理
│   └── providers/             # 各 TTS 提供商实现
│       ├── base.py
│       ├── openai_provider.py
│       ├── azure_provider.py
│       ├── edge_provider.py
│       ├── nami_provider.py
│       └── volcengine_provider.py
├── models/schemas.py          # Pydantic 数据模型
├── templates/index.html       # 前端页面
├── static/js/app.js           # 前端逻辑
└── data/                      # 运行时数据（不在 Git 中）
    ├── channels.json
    ├── azure_voices.json
    └── volc_voices.json
```
