"""导出数据库全量数据为静态 JSON（供 GitHub Pages 前端使用）"""
import json
import sys
from pathlib import Path

# 输出路径基于本文件位置派生（任意 CWD 运行都写项目根目录 data.json）
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data.json"

# 确保以 `python backend/export_static_data.py` 方式运行时也能找到 backend 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, Category, Dimension, Product
from backend.scorer import Scorer

db = SessionLocal()
result = {"categories": []}

try:
    for cat in db.query(Category).filter(Category.slug.like("cat-%")).order_by(Category.sort_order).all():
        dims = db.query(Dimension).filter(Dimension.category_id == cat.id).all()
        products = db.query(Product).filter(Product.category_id == cat.id).all()

        dim_map = {d.dim_key: d for d in dims}
        all_dim_values = Scorer.collect_all_dim_values(products, dim_map)
        scorer = Scorer(db)

        cat_data = {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "icon": cat.icon or "",
            "sort_order": cat.sort_order or 0,
            "product_count": len(products),
            "dimensions": [
                {
                    "dim_key": d.dim_key,
                    "label": d.label,
                    "type": d.type,
                    "unit": d.unit or "",
                    "higher_better": d.higher_better,
                    "default_weight": d.default_weight or 50,
                    "enum_values": json.loads(d.enum_values) if d.enum_values else [],
                }
                for d in dims
            ],
            "products": [],
        }

        for p in products:
            scores = scorer.calc_product_scores(p, dim_map, {}, all_dim_values)
            total = Scorer.calc_total_score(scores)
            cat_data["products"].append(
                {
                    "id": p.id,
                    "brand": p.brand,
                    "model": p.model or "",
                    "price_low": p.price_low or 0,
                    "price_high": p.price_high or 0,
                    "dimensions": p.dimensions or {},
                    # 各维度归一化分（与后端 scorer 一致，含价格/枚举维度），供静态模式排序
                    # 保留 4 位小数：舍入过粗会导致相邻产品排序乱序（如 2999 与 3000 同分）
                    "scores": {k: round(v.normalized, 4) for k, v in scores.items()},
                    "total_score": round(total, 1),
                }
            )

        result["categories"].append(cat_data)
finally:
    db.close()

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"导出完成：{len(result['categories'])} 个品类")
for c in result["categories"]:
    print(f"  {c['slug']} {c['name']}: {len(c['products'])} 个产品, {len(c['dimensions'])} 个维度")
