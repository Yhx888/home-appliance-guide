"""能效/水效标识备案查询 — 官方法定参数源

中国能效标识网与水效标识网均为 JS 渲染页面，自动化直接请求拿不到数据，
因此本模块提供：
  1. 备案查询入口 URL 生成（供人工/浏览器核验时直达）
  2. 人工核验后的数据点录入（复用 Collector 落库）

独立使用：
  python -m backend.scrapers.energy_label "KFR-35GW/N8HE1"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scrapers.base import Collector


ENERGY_LABEL_SEARCH_URL = "https://www.energylabel.com.cn/search/pubintro.html"
WATER_LABEL_URL = "https://www.waterlabel.org.cn/"


def build_query_url(brand: str, model: str) -> str:
    """生成能效备案查询直达 URL（进入后按型号搜索）。"""
    return f"{ENERGY_LABEL_SEARCH_URL}?keyword={model}"


def save_verified_value(brand: str, model: str, dim_key: str, raw_value, url: str, platform: str = "energy_label"):
    """人工/浏览器核验后录入一条官方备案数据点（pending，待多源核验）。"""
    from backend.database import SessionLocal, Product
    c = Collector()
    db = c.db
    product = None
    for p in db.query(Product).all():
        if p.brand == brand and model in p.model:
            product = p
            break
    if product is None:
        print(f"未找到产品: {brand} {model}")
        return None
    source = c.get_or_create_source(platform, url=url, method="html")
    dp = c.save_point(product, dim_key, raw_value, source)
    print(f"已录入: {brand} {model} {dim_key}={raw_value} (source_id={source.id})")
    c.close()
    return dp


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else ""
    if not model:
        print("用法: python -m backend.scrapers.energy_label <型号>")
        return
    print(f"能效备案查询入口: {ENERGY_LABEL_SEARCH_URL} (搜索型号: {model})")
    print(f"水效备案查询入口: {WATER_LABEL_URL}")
    print("提示: 两站为 JS 渲染，请用浏览器打开查询，核验后调用 save_verified_value() 录入。")


if __name__ == "__main__":
    main()
