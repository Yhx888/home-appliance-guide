"""京东联盟 API 采集 — 合规价格来源

依赖环境变量：
  JD_UNION_APPKEY  /  JD_UNION_SECRET

未配置密钥时自动降级为 dry-run（返回空列表并提示），不影响其他采集通道。

参考接口：
  jd.union.open.goods.search          按关键词搜索联盟商品
  jd.union.open.goods.query           按 skuId 批量查价格/标题
"""

import hashlib
import json
import os
import time
import urllib.parse
from typing import Optional

import requests


ROUTER_URL = "https://router.jd.com/api"


def _load_config() -> Optional[dict]:
    app_key = os.environ.get("JD_UNION_APPKEY", "").strip()
    secret = os.environ.get("JD_UNION_SECRET", "").strip()
    if not app_key or not secret or app_key == "你的AppKey":
        return None
    return {"app_key": app_key, "secret": secret}


def _sign(params: dict, secret: str) -> str:
    """京东联盟 MD5 签名：参数按 key 升序拼接，再拼 secret。"""
    items = sorted((k, str(v)) for k, v in params.items())
    raw = "".join(f"{k}{v}" for k, v in items) + secret
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def _call(method: str, param_json: dict) -> Optional[dict]:
    cfg = _load_config()
    if cfg is None:
        print("[jd_union] 未配置 JD_UNION_APPKEY/JD_UNION_SECRET，跳过联盟采集（dry-run）")
        return None
    params = {
        "method": method,
        "app_key": cfg["app_key"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "1.0",
        "sign_method": "md5",
        "param_json": json.dumps(param_json, ensure_ascii=False),
    }
    params["sign"] = _sign(params, cfg["secret"])
    resp = requests.post(ROUTER_URL, data=params, timeout=20)
    data = resp.json()
    if data.get("code") != 0:
        print(f"[jd_union] 接口错误: {data.get('code')} {data.get('msg')}")
        return None
    return data.get("data")


def search_goods(keyword: str, page_index: int = 1, page_size: int = 20) -> list[dict]:
    """按关键词搜索在售商品，返回商品列表（含 skuId/标题/最低价）。"""
    data = _call("jd.union.open.goods.search", {
        "goodsReqDTO": {
            "keyword": keyword,
            "pageIndex": page_index,
            "pageSize": page_size,
            "fields": ["skuId", "skuName", "priceInfo", "goodsInfo", "categoryInfo"],
        }
    })
    if not data:
        return []
    return data.get("result", []) or []


def query_goods_price(sku_ids: list[str]) -> list[dict]:
    """按 skuId 批量查询实时价格。"""
    if not sku_ids:
        return []
    data = _call("jd.union.open.goods.query", {
        "goodsReqDTO": {
            "skuIds": sku_ids,
            "fields": ["skuId", "skuName", "priceInfo"],
        }
    })
    if not data:
        return []
    return data.get("result", []) or []


def collect_price_for_product(brand: str, model: str, keyword: Optional[str] = None) -> Optional[float]:
    """按品牌+型号搜索联盟商品，返回匹配到的价格（元）。"""
    kw = keyword or f"{brand} {model}".strip()
    goods = search_goods(kw)
    for g in goods:
        name = (g.get("skuName") or "")
        if brand.lower() in name.lower() and (model.lower() in name.lower() or model == ""):
            price_info = g.get("priceInfo") or {}
            return price_info.get("lowestPrice") or price_info.get("price")
    return None


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "美的 BCD-508"
    print(search_goods(kw))
