"""厂商官网参数采集 — 低频抓取官方规格表

使用方法：
  from backend.scrapers.manufacturer import collect_official_pages, extract_specs_from_manufacturer_html

两类采集入口：
  1. collect_official_pages()      — 抓取官方页面清单（品牌官网产品页）
  2. collect_from_existing_sources() — 复用 data_sources 中已记录的厂商官网 URL 补采

全部经 Collector 限速 + 失败退避，结果写入 data_points（platform=manufacturer_html）。
"""

import re
from pathlib import Path
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database import SessionLocal, Category, Dimension, Product
from backend.scrapers.base import Collector


# 官方产品页清单：(品类slug, 品牌, 型号, 官方URL) — 已核验可访问的页面
OFFICIAL_PAGES = [
    ("cat-6", "海尔", "山茶花510", "https://www.haier.com/cooling/20250605_265348.shtml"),
    ("cat-6", "小米", "分储鲜Pro十字508L", "https://www.mi.com/mijia-fridge-pro-dsfr508-white"),
    ("cat-6", "松下", "NR-E452SX-PX", "https://consumer.panasonic.cn/product/ref/multi/nr-e452sx-px.html"),
]

# 厂商官网域名白名单（用于复用 data_sources 中已有的官网 URL）
MANUFACTURER_DOMAINS = (
    "haier.com", "midea.cn", "mi.com", "panasonic.cn", "dreame.tech",
    "ecovacs.cn", "dyson.cn", "iqair.cn", "casarte.com", "littleswan.com",
    "consumer.huawei.com", "supor.com", "robam.com", "fotile.com",
)


def collect_official_pages(category_slug: str = None, limit: int = 20) -> dict:
    """抓取 OFFICIAL_PAGES 清单中的官方规格表并写入 data_points。"""
    collector = Collector()
    db = collector.db
    stats = {"fetched": 0, "parsed": 0, "points": 0, "skipped": []}
    for cat_slug, brand, model, url in OFFICIAL_PAGES:
        if category_slug and cat_slug != category_slug:
            continue
        if stats["fetched"] >= limit:
            break
        cat = db.query(Category).filter(Category.slug == cat_slug).first()
        product = (
            db.query(Product)
            .filter(Product.category_id == cat.id, Product.brand == brand)
            .filter(Product.model.like(f"%{model}%"))
            .first()
        )
        if product is None:
            stats["skipped"].append(f"{brand} {model} 未入库")
            continue
        dims = db.query(Dimension).filter(Dimension.category_id == cat.id).all()
        dim_keys = [d.dim_key for d in dims]
        html = collector.fetch(url, category_slug=cat_slug)
        stats["fetched"] += 1
        if not html:
            stats["skipped"].append(f"{brand} {model} 抓取失败")
            continue
        specs = extract_specs_from_manufacturer_html(html, dim_keys)
        if not specs:
            stats["skipped"].append(f"{brand} {model} 未解析到规格")
            continue
        source = collector.get_or_create_source("manufacturer_html", url=url, method="html")
        for dk, raw in specs.items():
            collector.save_point(product, dk, raw, source)
            stats["points"] += 1
        stats["parsed"] += 1
    collector.close()
    return stats


def collect_from_existing_sources(category_slug: str = None, limit: int = 50) -> dict:
    """复用 data_sources 中已记录的厂商官网 URL，低频补采参数。"""
    collector = Collector()
    db = collector.db
    stats = {"sources": 0, "points": 0, "skipped": []}
    from backend.database import DataPoint, DataSource
    rows = (
        db.query(DataSource, DataPoint, Product, Category)
        .join(DataPoint, DataPoint.source_id == DataSource.id)
        .join(Product, Product.id == DataPoint.product_id)
        .join(Category, Category.id == Product.category_id)
        .filter(DataSource.platform == "web_research")
        .all()
    )
    seen = set()
    for src, dp, product, cat in rows:
        url = (src.url or "").strip()
        if not url or not any(d in url for d in MANUFACTURER_DOMAINS):
            continue
        if category_slug and cat.slug != category_slug:
            continue
        key = (product.id, url)
        if key in seen or stats["sources"] >= limit:
            continue
        seen.add(key)
        dims = db.query(Dimension).filter(Dimension.category_id == cat.id).all()
        dim_keys = [d.dim_key for d in dims]
        html = collector.fetch(url, category_slug=cat.slug)
        if not html:
            stats["skipped"].append(f"{cat.slug} {product.brand} {product.model} 抓取失败")
            continue
        specs = extract_specs_from_manufacturer_html(html, dim_keys)
        stats["sources"] += 1
        if not specs:
            stats["skipped"].append(f"{cat.slug} {product.brand} {product.model} 未解析到规格")
            continue
        source = collector.get_or_create_source("manufacturer_html", url=url, method="html")
        for dk, raw in specs.items():
            collector.save_point(product, dk, raw, source)
            stats["points"] += 1
    collector.close()
    return stats


def extract_specs_from_manufacturer_html(html: str, dim_keys: list[str]) -> dict:
    """从厂商官网 HTML 中提取规格参数。

    支持多种官网常见结构：
    - table.product-specs 结构
    - dl/dt/dd 定义列表结构
    - div.spec-item 结构
    返回 {dim_key: raw_value} 字典。
    """
    result: dict[str, str] = {}
    soup = BeautifulSoup(html, 'html.parser')

    # 策略1：table 规格表
    tables = soup.find_all('table', class_=re.compile(r'(spec|parameter|attribute)', re.I))
    if not tables:
        tables = soup.find_all('table')
    for table in tables:
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = _clean_text(cells[0].get_text(strip=True))
                value = _clean_text(cells[1].get_text(strip=True))
                key = _match_dim_key(label, dim_keys)
                if key:
                    result[key] = value
        if result:
            return result

    # 策略2：dl/dt/dd 定义列表
    for dl in soup.find_all('dl', class_=re.compile(r'(spec|parameter|attr)', re.I)):
        dt = dl.find('dt')
        dd = dl.find('dd')
        if dt and dd:
            label = _clean_text(dt.get_text(strip=True))
            value = _clean_text(dd.get_text(strip=True))
            key = _match_dim_key(label, dim_keys)
            if key:
                result[key] = value

    if not result:
        # 策略3：div.spec-item 结构
        for item in soup.find_all('div', class_=re.compile(r'(spec|param|attr)', re.I)):
            label_el = item.find(['span', 'label', 'div'], class_=re.compile(r'(name|label|title)', re.I))
            value_el = item.find(['span', 'div', 'p'], class_=re.compile(r'(value|desc|content)', re.I))
            if label_el and value_el:
                label = _clean_text(label_el.get_text(strip=True))
                value = _clean_text(value_el.get_text(strip=True))
                key = _match_dim_key(label, dim_keys)
                if key:
                    result[key] = value

    return result


def _clean_text(text: str) -> str:
    """清理文本：去空白、去冒号"""
    text = re.sub(r'\s+', '', text)
    text = text.rstrip('：:')
    return text


def _match_dim_key(label: str, dim_keys: list[str]) -> str | None:
    """匹配 label 到 dim_key"""
    label_to_prefix = {
        '风量': '风量',
        '静压': '静压',
        '噪音': '噪音',
        '能效': '能效等级',
        '容量': '容量',
        '火力': '火力',
        '热效率': '热效率',
        '价格': '价格',
        '保修': '保修',
        '功率': '功率',
        '尺寸': '尺寸',
        '重量': '重量',
        '面板': '面板材质',
        '电机': '电机类型',
        '烘干': '烘干方式',
        '消毒': '消毒方式',
        '过滤': '过滤等级',
        '吸力': '吸力',
        '型号': '型号',
    }

    prefix = label_to_prefix.get(label)
    if prefix:
        for dk in dim_keys:
            if dk.startswith(prefix):
                return dk

    for dk in dim_keys:
        if label == dk.split('_')[0]:
            return dk
    return None
