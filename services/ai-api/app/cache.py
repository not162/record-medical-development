import os
import json
import time
import hashlib
from typing import Any, Optional, Dict

# Mencoba mengimpor redis
try:
    import redis
    REDIS_INSTALLED = True
except ImportError:
    REDIS_INSTALLED = False

class MemoryCacheFallback:
    """In-memory cache fallback saat Redis belum aktif atau pada environment serverless."""
    def __init__(self):
        self._store: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            val, expire_at = self._store[key]
            if time.time() < expire_at:
                return val
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str):
        self._store.pop(key, None)

    def delete_pattern(self, pattern: str) -> int:
        prefix = pattern.replace("*", "")
        keys_to_del = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_del:
            del self._store[k]
        return len(keys_to_del)

    def count(self) -> int:
        # Bersihkan yang expired
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if now >= exp]
        for k in expired:
            del self._store[k]
        return len(self._store)

class RedisCacheManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._is_redis_active = False
        self._fallback = MemoryCacheFallback()
        self._init_connection()

    def _init_connection(self):
        if not REDIS_INSTALLED:
            print("[*] Cache: Menggunakan in-memory fallback (paket redis belum terpasang).")
            return

        try:
            client = redis.Redis.from_url(
                self.redis_url,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
                decode_responses=True
            )
            # Test ping
            client.ping()
            self._client = client
            self._is_redis_active = True
            print(f"[*] Cache: Berhasil terhubung ke Redis cluster ({self.redis_url})")
        except Exception as e:
            self._is_redis_active = False
            self._client = None
            # Log santai bahwa in-memory fallback aktif
            print(f"[*] Cache: Redis belum aktif pada {self.redis_url} -> Menggunakan in-memory fallback cache.")

    @property
    def is_connected(self) -> bool:
        return self._is_redis_active and self._client is not None

    def get(self, key: str) -> Optional[Any]:
        if self.is_connected and self._client:
            try:
                raw = self._client.get(key)
                if raw is not None:
                    return json.loads(raw)
            except Exception:
                pass
        return self._fallback.get(key)

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        serialized = json.dumps(value, default=str)
        if self.is_connected and self._client:
            try:
                self._client.setex(key, ttl, serialized)
                return True
            except Exception:
                pass
        self._fallback.set(key, value, ttl)
        return True

    def delete(self, key: str) -> bool:
        if self.is_connected and self._client:
            try:
                self._client.delete(key)
            except Exception:
                pass
        self._fallback.delete(key)
        return True

    def delete_pattern(self, pattern: str) -> int:
        count = 0
        if self.is_connected and self._client:
            try:
                keys = self._client.keys(pattern)
                if keys:
                    count += self._client.delete(*keys)
            except Exception:
                pass
        count += self._fallback.delete_pattern(pattern)
        return count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "engine": "Redis" if self.is_connected else "In-Memory RAM Fallback",
            "is_connected": self.is_connected,
            "redis_url": self.redis_url if self.is_connected else None,
            "cached_items_approx": self._fallback.count()
        }

# Instance singleton
cache_manager = RedisCacheManager()

def make_cache_key(prefix: str, *args) -> str:
    """Membuat hash SHA-256 unik untuk parameter query kompleks."""
    raw = ":".join(str(a) for a in args)
    hashed = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{hashed}"
