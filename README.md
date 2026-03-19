# TTS OPEN 管理平台

一个功能全面的 TTS（文本转语音）管理平台，支持多种 TTS 渠道接入，兼容 OpenAI TTS API 格式。

## 功能特性

- **多渠道支持**: OpenAI、Azure、Google、ElevenLabs、Microsoft Edge TTS、自定义 API
- **OpenAI 兼容**: 完全兼容 `/v1/audio/speech` API 格式
- **在线预览**: 支持实时试听和参数调整
- **渠道管理**: 灵活的渠道优先级配置、健康检查
- **历史记录**: 保存生成历史，支持回放下载
- **现代化 UI**: 使用 Tailwind CSS 的精美界面

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动

### 访问管理界面

打开浏览器访问: `http://localhost:8000`

## API 使用

### 语音合成

```bash
curl -X POST http://localhost:8000/api/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "你好，世界！",
    "voice": "alloy",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output speech.mp3
```

### 获取语音列表

```bash
curl http://localhost:8000/api/v1/voices
```

### 渠道管理

```bash
# 获取渠道列表
curl http://localhost:8000/api/v1/channels

# 创建渠道
curl -X POST http://localhost:8000/api/v1/channels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My OpenAI",
    "type": "openai",
    "api_key": "sk-xxx",
    "priority": 1
  }'
```

## 项目结构

```
.
├── main.py                 # 主程序入口
├── config/                 # 配置模块
│   ├── __init__.py
│   └── settings.py
├── models/                 # 数据模型
│   ├── __init__.py
│   └── schemas.py
├── routers/                # API 路由
│   ├── __init__.py
│   ├── tts.py             # TTS 相关路由
│   └── channels.py        # 渠道管理路由
├── services/               # 业务逻辑层
│   ├── __init__.py
│   ├── tts_service.py     # TTS 服务
│   └── channel_service.py # 渠道服务
├── static/                 # 静态文件
│   └── js/
│       └── app.js         # 前端 JavaScript
├── templates/              # HTML 模板
│   └── index.html         # 主页面
├── requirements.txt        # 依赖列表
└── README.md              # 项目说明
```

## 支持的 TTS 渠道

| 渠道 | 类型 | 说明 |
|------|------|------|
| OpenAI | openai | OpenAI TTS API |
| Azure | azure | Azure Speech Services |
| Google | google | Google Cloud Text-to-Speech |
| ElevenLabs | elevenlabs | ElevenLabs API |
| Edge TTS | edge | Microsoft Edge TTS（免费） |
| Custom | custom | 自定义 API 接口 |

## 配置说明

可以通过环境变量或 `.env` 文件配置：

```env
HOST=0.0.0.0
PORT=8000
DEBUG=true
AUDIO_OUTPUT_DIR=./output/audio
```

## 许可证

MIT License
