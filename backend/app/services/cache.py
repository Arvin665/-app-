from typing import Optional

import redis
from redis.exceptions import RedisError

from app.core.config import settings


class AuthCache:
    """Redis 鉴权缓存；Redis 暂时不可用时自动退化为数据库查询，保证服务可启动。"""

    def __init__(self) -> None:
        self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)

    def get_device(self, device_id: str) -> Optional[str]:
        try:
            return self._client.get(f"device-auth:{device_id}")
        except RedisError:
            return None

    def set_device(self, device_id: str, role_level: int) -> None:
        try:
            self._client.setex(f"device-auth:{device_id}", settings.access_cache_seconds, str(role_level))
        except RedisError:
            # 缓存故障不能阻断业务主链路。
            return None

    def delete_device(self, device_id: str) -> None:
        try:
            self._client.delete(f"device-auth:{device_id}")
        except RedisError:
            return None

    def set_sync_cursor(self, device_id: str, module: str, cursor: str) -> None:
        """Redis 只保存同步游标，真实数据仍以数据库为唯一来源。"""
        try:
            self._client.setex(f"sync-cursor:{device_id}:{module}", 86400 * 30, cursor)
        except RedisError:
            return None

    def get_sync_cursor(self, device_id: str, module: str) -> Optional[str]:
        try:
            return self._client.get(f"sync-cursor:{device_id}:{module}")
        except RedisError:
            return None


auth_cache = AuthCache()
