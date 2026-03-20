# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run uvicorn main:app --reload
# 或直接运行：
python main.py

# Docker 部署（对外暴露 59012 端口）
docker-compose up
```

## 集成测试

```bash
# 需要先启动服务（默认连接 http://127.0.0.1:8000，默认 API Key: admin）
python test/test_api.py

# 指定服务地址、API Key 和测试文本
python test/test_api.py --base-url http://127.0.0.1:8000 --api-key admin --text "你好世界"
```

## 认证

所有 `/api/v1/*` 接口需要认证，公开路径（`/`、`/api/health`、`/docs`）免校验。

- 请求头：`Authorization: Bearer <password>` 或 `X-API-Key: <password>`
- 密码通过环境变量 `ADMIN_PASSWORD` 配置，默认 `admin`
- 前端登录后将 token 存入 `sessionStorage`，通过 `apiFetch()` 封装自动携带

## 开发规范

### 日志

- 统一使用 `from config.logger import logger` 获取 logger，不要用 `print()`
- 新增模块也可以用 `logging.getLogger(__name__)` 获取带模块名的 logger，格式已由根 logger 统一
- 日志格式：`%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s`，示例：
  ```
  2026-03-19 09:05:56,881 - services.tts_service - INFO - 收到合成请求
  ```

## 架构说明

**TTS OPEN** 是一个 FastAPI 管理平台，将多个 TTS 后端统一聚合在兼容 OpenAI 格式的 API 之后。

### 请求流程

```
HTTP 客户端
  → auth_middleware（main.py，校验 Bearer token）
  → FastAPI 路由（routers/tts.py 或 routers/channels.py）
  → TTSChannelManager（services/tts_service.py）
  → TTSProvider 子类
  → 上游 TTS API 或本地引擎
  → 返回 / 流式传输音频数据
```

### 核心模块

- **`main.py`** — 应用初始化；CORS、认证中间件、静态文件、Jinja2 模板，路由挂载于 `/api/v1`
- **`routers/tts.py`** — TTS 相关接口：`POST /audio/speech`（兼容 OpenAI 格式）、`POST /audio/preview`、`GET /voices`、`GET|DELETE /history`、`GET /audio/stream/{id}`、`POST /tts/reading`（表单接口，供阅读类 APP 使用）
- **`routers/channels.py`** — 渠道管理 CRUD：`GET|POST /channels`、`GET|PUT|DELETE /channels/{id}`、`POST /channels/{id}/test`、`GET /channel-types`
- **`services/tts_service.py`** — `TTSChannelManager` 全局单例（`tts_manager`）；根据渠道类型分发至对应 Provider；音频文件保存至 `./output/audio/`，历史记录最多保留最近 7 条（`./data/history.json`）
- **`services/providers/`** — 各 TTS 提供商实现；`base.py` 定义 `TTSProvider` 基类，其余每个文件对应一个提供商
- **`services/channel_service.py`** — `ChannelService` 全局单例（`channel_service`）；渠道配置持久化至 `./data/channels.json`；首次启动时自动初始化 Edge TTS、Azure、火山引擎、纳米AI 四个默认渠道
- **`models/schemas.py`** — 所有 Pydantic 数据模型
- **`config/settings.py`** — 基于 `pydantic-settings` 的配置；从 `.env` 文件读取；默认端口 59012；关键环境变量：`ADMIN_PASSWORD`（认证密码）、`DATA_DIR`（数据目录，默认 `./data`）、`DEBUG`（生产环境设为 `False` 关闭 API 文档）
- **`static/js/app.js`** — 前端逻辑；`apiFetch()` 封装所有 API 请求并自动带认证头；`voicesLoaded` 标志位防止切换 tab 重复拉取音色列表；`toggleSidebar()` 控制移动端侧边栏
- **`templates/index.html`** — 前端页面；未登录时主体内容隐藏，登录成功后调用 `initApp()` 显示；左侧固定侧边栏导航，移动端折叠为 hamburger 菜单

### TTS 提供商（均在 `services/providers/` 中）

| 渠道类型 | Provider 类 | 说明 |
|---|---|---|
| `openai` | `OpenAIProvider` | 支持官方 OpenAI 及任意兼容接口；自动从第三方 `/models` 接口获取音色列表 |
| `azure` | `AzureTTSProvider` | 使用微软翻译非官方端点（无需 API Key）；Token 带过期缓存；音色列表可通过 `./data/azure_voices.json` 扩展情感风格；支持 `音色名|风格` 语法 |
| `edge` | `EdgeTTSProvider` | 基于 `edge-tts` 库；获取超时时降级为预置列表 |
| `nami` | `NamiTTSProvider` | 使用纳米AI（bot.n.cn）接口（无需 API Key）；音色目录缓存至 `./data/nami_voices.json` |
| `custom` 且 `config.provider=="volcengine"` | `VolcengineTTSProvider` | 使用火山翻译接口（无需 API Key）；音色目录来自 `./data/volc_voices.json`；自动检测语言 |

渠道选择逻辑：`synthesize()` 优先使用 `request.channel_id`；未指定时自动遍历所有渠道的音色列表，找到匹配 `voice` 的渠道（结果缓存 5 分钟）；仍找不到则降级到优先级最高的活跃渠道。

### 持久化数据文件（不在 Git 中）

- `./data/channels.json` — 渠道配置（删除后重启会重新生成 4 个默认渠道）
- `./data/history.json` — 最近 7 条合成记录
- `./data/azure_voices.json` — Azure 音色及情感/风格目录
- `./data/volc_voices.json` — 火山引擎音色目录
- `./data/nami_voices.json` — 纳米AI 音色目录
- `./output/audio/` — 生成的音频文件
