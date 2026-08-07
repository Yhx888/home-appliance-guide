"""数据点回填：为 products.dimensions 中无数据点记录的维度值补建 data_points

历史管道（seed/enrich/expand）写入 dimensions 的很多值没有同步生成 data_points
（约 43.5%），导致 verify.py 多源比对缺失"原始来源"侧记录，单源永远无法判定 verified。

本脚本为每个"有值但无数据点"的 (product, dimension_key) 补一条数据点，
来源挂到一条通用 web_research 记录（method='backfill'，URL 留空），
幂等：已有数据点的维度跳过。

用法：python backend/backfill_datapoints.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, DataSource, DataPoint, Product


def to_numeric(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        f = float(str(v).replace(",", ""))
        return f
    except (ValueError, TypeError):
        return None


def main():
    db = SessionLocal()

    # 通用回填来源（复用 web_research 平台，URL 空）
    source = (
        db.query(DataSource)
        .filter(DataSource.platform == "web_research", DataSource.url == "")
        .first()
    )
    if not source:
        source = DataSource(platform="web_research", url="", method="backfill")
        db.add(source)
        db.flush()

    # 仅当 (product, dim) 下没有 web_research 平台的数据点时补原始源记录
    existing = {
        (dp.product_id, dp.dimension_key)
        for dp in db.query(DataPoint)
        .join(DataSource, DataPoint.source_id == DataSource.id)
        .filter(DataSource.platform == "web_research")
        .all()
    }

    added = 0
    skipped = 0
    for product in db.query(Product).all():
        dims = product.dimensions or {}
        for dim_key, value in dims.items():
            if value is None:
                continue
            if (product.id, dim_key) in existing:
                skipped += 1
                continue
            db.add(DataPoint(
                product_id=product.id,
                dimension_key=dim_key,
                source_id=source.id,
                raw_value=str(value),
                numeric_value=to_numeric(value),
                confidence=0.5,
                status="pending",
            ))
            added += 1

    db.commit()
    db.close()
    print(f"完成：回填数据点 {added} 条，已存在跳过 {skipped} 条")
    print("下一步：python -m backend.scrapers.verify --apply（多源判定写回）")


if __name__ == "__main__":
    main()
