"""采集调度器骨架 — 单线程低频采集 + 失败退避 + 统一落库

所有采集器（厂商官网 / 能效标识 / 京东联盟 / 浏览器补采）共用：
  - 每品类每日访问上限（默认 50 次）
  - 请求间随机 2~5 秒间隔
  - 失败指数退避（1s → 2s → 4s → 8s，最多 3 次重试）
  - 结果统一写入 data_points（记录 source_id / raw_value / confidence=0.5 / pending）

用法：
  from backend.scrapers.base import Collector
  c = Collector()
  with c.throttle(category_slug="cat-6"):
      ok, value = c.fetch(url)   # 受控请求
      c.save_point(product, dim_key, raw, source_id)
"""

import random
import time
from datetime import date
from typing import Optional

import requests
from sqlalchemy.orm import Session

from backend.database import SessionLocal, DataPoint, DataSource


class Collector:
    """低频采集器：限速、退避、落库。"""

    def __init__(self, db: Optional[Session] = None, daily_limit: int = 50):
        self.db = db or SessionLocal()
        self.daily_limit = daily_limit
        self._last_request_at = 0.0
        self._today_counts: dict[str, int] = {}
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    # ── 节流 ──────────────────────────────────────────────────────────

    def _respect_daily_limit(self, category_slug: str) -> bool:
        today = date.today().isoformat()
        key = f"{category_slug}:{today}"
        if self._today_counts.get(key, 0) >= self.daily_limit:
            return False
        self._today_counts[key] = self._today_counts.get(key, 0) + 1
        return True

    def _wait_interval(self):
        """请求间随机 2~5 秒（首请求不等待）。"""
        if self._last_request_at:
            elapsed = time.time() - self._last_request_at
            wait = random.uniform(2.0, 5.0) - elapsed
            if wait > 0:
                time.sleep(wait)
        self._last_request_at = time.time()

    def fetch(self, url: str, category_slug: str = "cat-0", timeout: int = 15) -> Optional[str]:
        """受控 GET 请求：限速 + 退避，返回 HTML 文本或 None。"""
        if not self._respect_daily_limit(category_slug):
            print(f"[限流] {category_slug} 今日访问已达上限 {self.daily_limit}")
            return None
        for attempt in range(4):
            self._wait_interval()
            try:
                resp = requests.get(url, headers=self.headers, timeout=timeout)
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code in (403, 429):
                    time.sleep(2 ** attempt)
                    continue
                print(f"[HTTP {resp.status_code}] {url}")
                return None
            except requests.RequestException as e:
                print(f"[请求失败] {url}: {e}")
                time.sleep(2 ** attempt)
        return None

    # ── 落库 ──────────────────────────────────────────────────────────

    def get_or_create_source(self, platform: str, url: str = "", method: str = "html") -> DataSource:
        """按 platform+url 复用数据源。"""
        q = self.db.query(DataSource).filter(DataSource.platform == platform)
        if url:
            q = q.filter(DataSource.url == url)
        src = q.first()
        if src:
            return src
        src = DataSource(platform=platform, url=url, method=method)
        self.db.add(src)
        self.db.commit()
        return src

    def save_point(self, product, dim_key: str, raw_value, source: DataSource) -> DataPoint:
        """写入一条数据点（pending，置信度 0.5）。"""
        raw_text = str(raw_value)
        # 数值解析：与 verify.parse_numeric_from_text 同规则，取首个数字或范围中值
        import re
        nums = re.findall(r"\d+\.?\d*", raw_text.replace(",", ""))
        numeric = None
        if nums:
            vals = [float(n) for n in nums]
            numeric = vals[0] if len(vals) == 1 else sum(vals) / len(vals)
        dp = DataPoint(
            product_id=product.id,
            dimension_key=dim_key,
            source_id=source.id,
            raw_value=raw_text,
            numeric_value=numeric,
            confidence=0.5,
            status="pending",
        )
        self.db.add(dp)
        self.db.commit()
        return dp

    def close(self):
        self.db.close()
