"""注入第二来源核验数据（web 多源调研结果）→ data_points 表

供 verify.py 多源判定使用：数据点只有 ≥2 个不同 source_id 且数值一致
（CV<15%）时才会被判定 verified 并写回 products.dimensions。

用法：
  python backend/verify_web.py <结果JSON>

结果 JSON 格式（product_id 用 export 清单中的 id）：
[
  {
    "product_id": 15,
    "url": "https://item.jd.com/xxx.html",
    "platform": "web_verify",
    "dims": {"风量_m3": 30.0, "静压_Pa": 1450.0, "噪音_dB": 52.0, "保修_年": 5},
    "override": false,     # true=将外部值直接写入 products.dimensions（修正/补全缺失）
    "no_datapoint": false  # true=只写 DB 不插数据点（用于域内修正，避免 verify 均值写回拉偏）
  },
  ...
]

幂等：同一 (product_id, dimension_key, source url) 不重复插入。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, DataSource, DataPoint, Product


def main(path: str):
    db = SessionLocal()
    data = json.load(open(path, encoding="utf-8"))
    added = 0
    skipped = 0
    overridden = 0

    for item in data:
        product = db.query(Product).filter(Product.id == item["product_id"]).first()
        if not product:
            print(f"  [跳过] 产品不存在 id={item['product_id']}")
            skipped += 1
            continue

        url = item.get("url", "")
        platform = item.get("platform", "web_verify")

        # 同一来源 URL 复用一条 data_sources 记录
        source = (
            db.query(DataSource)
            .filter(DataSource.platform == platform, DataSource.url == url)
            .first()
        )
        if not source:
            source = DataSource(platform=platform, url=url, method="web")
            db.add(source)
            db.flush()

        # 修正/补全：外部值直接写入 products.dimensions（来源可追溯）
        if item.get("override"):
            dims = dict(product.dimensions or {})
            for dim_key, value in (item.get("dims") or {}).items():
                if dims.get(dim_key) == value:
                    continue
                dims[dim_key] = value
                overridden += 1
            product.dimensions = dims

        if item.get("no_datapoint"):
            # 只写 DB 不插数据点（域内修正：避免 verify 以均值写回拉偏权威值）
            continue

        for dim_key, value in (item.get("dims") or {}).items():
            exists = (
                db.query(DataPoint)
                .filter(
                    DataPoint.product_id == product.id,
                    DataPoint.dimension_key == dim_key,
                    DataPoint.source_id == source.id,
                )
                .first()
            )
            if exists:
                skipped += 1
                continue

            numeric = None
            raw = str(value)
            if isinstance(value, (int, float)):
                numeric = float(value)
            elif isinstance(value, bool):
                raw = "True" if value else "False"
            elif isinstance(value, str):
                raw = value

            db.add(DataPoint(
                product_id=product.id,
                dimension_key=dim_key,
                source_id=source.id,
                raw_value=raw,
                numeric_value=numeric,
                confidence=0.6,   # 第二来源基础值，verify 会按多源重新计算
                status="pending",
            ))
            added += 1

    db.commit()
    db.close()
    print(f"完成：新增数据点 {added} 条，跳过重复 {skipped} 条，override 写回 {overridden} 处")
    print("下一步：python -m backend.scrapers.verify --apply（多源判定并写回共识值）")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python backend/verify_web.py <结果JSON>")
        sys.exit(1)
    main(sys.argv[1])
