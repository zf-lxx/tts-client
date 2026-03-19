"""
渠道管理服务
"""
import uuid
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.schemas import (
    ChannelCreateRequest,
    ChannelUpdateRequest,
    ChannelResponse,
    ChannelListResponse,
    ChannelType,
    ChannelStatus
)
from config.logger import logger

DATA_DIR = "./data"
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")


class ChannelService:
    """渠道管理服务"""
    
    def __init__(self):
        self.channels: Dict[str, Dict[str, Any]] = {}
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load_channels()
    
    def _load_channels(self):
        """从文件加载渠道"""
        if not os.path.exists(CHANNELS_FILE):
            self._init_default_channel()
            self._save_channels()
            return
            
        try:
            with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 恢复 datetime 对象
                for channel_id, channel in data.items():
                    channel['created_at'] = datetime.fromisoformat(channel['created_at'])
                    channel['updated_at'] = datetime.fromisoformat(channel['updated_at'])
                self.channels = data
                logger.info(f"已加载 {len(self.channels)} 个渠道配置")
        except Exception as e:
            logger.error(f"加载渠道配置失败: {e}，使用默认配置")
            self._init_default_channel()
            self._save_channels()

    def _save_channels(self):
        """保存渠道到文件"""
        try:
            # 转换 datetime 为字符串
            data_to_save = {}
            for channel_id, channel in self.channels.items():
                channel_copy = channel.copy()
                channel_copy['created_at'] = channel_copy['created_at'].isoformat()
                channel_copy['updated_at'] = channel_copy['updated_at'].isoformat()
                data_to_save[channel_id] = channel_copy
                
            with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存渠道配置失败: {e}")
    
    def _init_default_channel(self):
        """初始化默认渠道"""
        default_id = str(uuid.uuid4())
        self.channels[default_id] = {
            "id": default_id,
            "name": "Edge TTS (免费)",
            "type": ChannelType.EDGE,
            "base_url": None,
            "api_key": None,
            "config": {},
            "priority": 0,
            "status": ChannelStatus.ACTIVE,
            "is_default": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        azure_id = str(uuid.uuid4())
        self.channels[azure_id] = {
            "id": azure_id,
            "name": "Azure 内置",
            "type": ChannelType.AZURE,
            "base_url": None,
            "api_key": None,
            "config": {},
            "priority": 0,
            "status": ChannelStatus.ACTIVE,
            "is_default": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        volc_id = str(uuid.uuid4())
        self.channels[volc_id] = {
            "id": volc_id,
            "name": "火山内置",
            "type": ChannelType.CUSTOM,
            "base_url": None,
            "api_key": None,
            "config": {"provider": "volcengine"},
            "priority": 0,
            "status": ChannelStatus.ACTIVE,
            "is_default": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        nami_id = str(uuid.uuid4())
        self.channels[nami_id] = {
            "id": nami_id,
            "name": "纳米AI内置",
            "type": ChannelType.NAMI,
            "base_url": None,
            "api_key": None,
            "config": {"default_voice": "DeepSeek"},
            "priority": 0,
            "status": ChannelStatus.ACTIVE,
            "is_default": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    def create_channel(self, request: ChannelCreateRequest) -> ChannelResponse:
        """创建渠道"""
        logger.info(f"创建新渠道: {request.name} ({request.type})")
        channel_id = str(uuid.uuid4())
        
        # 如果设置为默认，取消其他默认
        if request.is_default:
            logger.info("新渠道设为默认，取消其他默认渠道")
            for channel in self.channels.values():
                channel["is_default"] = False
        
        channel_data = {
            "id": channel_id,
            "name": request.name,
            "type": request.type,
            "base_url": request.base_url,
            "api_key": request.api_key,
            "config": request.config,
            "priority": request.priority,
            "status": ChannelStatus.ACTIVE,
            "is_default": request.is_default,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        self.channels[channel_id] = channel_data
        self._save_channels()
        
        return ChannelResponse(
            id=channel_id,
            name=request.name,
            type=request.type,
            base_url=request.base_url,
            config=request.config,
            priority=request.priority,
            status=ChannelStatus.ACTIVE,
            is_default=request.is_default,
            created_at=channel_data["created_at"],
            updated_at=channel_data["updated_at"]
        )
    
    def update_channel(self, channel_id: str, request: ChannelUpdateRequest) -> ChannelResponse:
        """更新渠道"""
        logger.info(f"更新渠道: {channel_id}")
        channel = self.channels.get(channel_id)
        if not channel:
            logger.warning(f"更新失败，渠道不存在: {channel_id}")
            raise ValueError(f"渠道 {channel_id} 不存在")
        
        # 如果设置为默认，取消其他默认
        if request.is_default:
            logger.info("渠道设为默认，取消其他默认渠道")
            for ch in self.channels.values():
                ch["is_default"] = False
        
        if request.name is not None:
            channel["name"] = request.name
        if request.base_url is not None:
            channel["base_url"] = request.base_url
        if request.api_key is not None:
            channel["api_key"] = request.api_key
        if request.config is not None:
            channel["config"] = request.config
        if request.priority is not None:
            channel["priority"] = request.priority
        if request.status is not None:
            channel["status"] = request.status
        if request.is_default is not None:
            channel["is_default"] = request.is_default
        
        channel["updated_at"] = datetime.now()
        self._save_channels()
        
        return ChannelResponse(**channel)
    
    def delete_channel(self, channel_id: str) -> bool:
        """删除渠道"""
        logger.info(f"删除渠道: {channel_id}")
        if channel_id not in self.channels:
            logger.warning(f"删除失败，渠道不存在: {channel_id}")
            return False
        
        # 不能删除默认渠道
        if self.channels[channel_id].get("is_default"):
            logger.warning(f"删除失败，不能删除默认渠道: {channel_id}")
            raise ValueError("不能删除默认渠道")
        
        del self.channels[channel_id]
        self._save_channels()
        return True
    
    def get_channel(self, channel_id: str) -> Optional[ChannelResponse]:
        """获取单个渠道"""
        channel = self.channels.get(channel_id)
        if channel:
            return ChannelResponse(**channel)
        return None
    
    def list_channels(
        self, 
        status: Optional[ChannelStatus] = None,
        channel_type: Optional[ChannelType] = None
    ) -> ChannelListResponse:
        """获取渠道列表"""
        items = list(self.channels.values())
        
        if status:
            items = [ch for ch in items if ch["status"] == status]
        
        if channel_type:
            items = [ch for ch in items if ch["type"] == channel_type]
        
        # 按优先级排序
        items.sort(key=lambda x: (-x["priority"], x["created_at"]), reverse=False)
        
        return ChannelListResponse(
            total=len(items),
            items=[ChannelResponse(**ch) for ch in items]
        )
    
    async def test_channel(self, channel_id: str) -> Dict[str, Any]:
        """测试渠道连接"""
        logger.info(f"测试渠道连接: {channel_id}")
        channel = self.channels.get(channel_id)
        if not channel:
            return {"success": False, "message": "渠道不存在"}
        
        # 简单的连接测试
        try:
            if channel["type"] == ChannelType.OPENAI:
                import httpx
                api_key = channel.get("api_key", "")
                base_url = channel.get("base_url", "https://api.openai.com/v1")
                
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{base_url}/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=10.0
                        )
                        if response.status_code == 200:
                            success = True
                            error_msg = ""
                        else:
                            success = False
                            error_msg = f"HTTP {response.status_code}"
                            # 尝试获取更多错误信息
                            try:
                                error_detail = response.json()
                                if "error" in error_detail:
                                    if isinstance(error_detail["error"], dict):
                                        error_msg += f": {error_detail['error'].get('message', '')}"
                                    else:
                                        error_msg += f": {error_detail['error']}"
                            except:
                                pass
                                
                except Exception as ex:
                    logger.warning(f"渠道 {channel_id} HTTP 请求失败: {str(ex)}")
                    success = False
                    error_msg = str(ex)
                
                if success:
                    channel["status"] = ChannelStatus.ACTIVE
                    logger.info(f"渠道 {channel_id} 测试成功")
                    self._save_channels()
                    return {"success": True, "message": "连接成功"}
                else:
                    channel["status"] = ChannelStatus.ERROR
                    logger.error(f"渠道 {channel_id} 测试失败: {error_msg}")
                    self._save_channels()
                    return {"success": False, "message": f"连接失败: {error_msg}"}
            else:
                return {"success": True, "message": "本地渠道无需测试"}
                
        except Exception as e:
            channel["status"] = ChannelStatus.ERROR
            self._save_channels()
            logger.error(f"渠道 {channel_id} 测试异常: {str(e)}", exc_info=True)
            return {"success": False, "message": f"测试失败: {str(e)}"}


# 全局服务实例
channel_service = ChannelService()
