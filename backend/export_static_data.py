"""导出数据库全量数据为静态 JSON（供 GitHub Pages 前端使用）"""
import json
import sys
from pathlib import Path

# 输出路径基于本文件位置派生（任意 CWD 运行都写项目根目录 data.json）
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data.json"

# 通用款判定：model 为"通用款"或纯中文无型号字符（如"集成灶蒸烤一体"）→ 品牌代表款
import re
GENERIC_MODEL_RE = re.compile(r"^[\u4e00-\u9fa5]+$")


def is_generic_product(brand: str, model: str) -> bool:
    return "通用款" in (brand + model) or bool(model and GENERIC_MODEL_RE.match(model))

# 确保以 `python backend/export_static_data.py` 方式运行时也能找到 backend 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, Category, Dimension, Product, DataPoint
from backend.scorer import Scorer, compute_verify_status

db = SessionLocal()
VERIFY_MAP = compute_verify_status(db)
result = {"categories": []}

try:
    for cat in db.query(Category).filter(Category.slug.like("cat-%")).order_by(Category.sort_order).all():
        dims = db.query(Dimension).filter(Dimension.category_id == cat.id).all()
        # 排除 hidden 产品（品类错配等），不参与展示与评分
        products = db.query(Product).filter(Product.category_id == cat.id, Product.hidden == False).all()

        dim_map = {d.dim_key: d for d in dims}
        all_dim_values = Scorer.collect_all_dim_values(products, dim_map)
        scorer = Scorer(db)
        review_ids = {
            row[0] for row in db.query(Product.id)
            .join(DataPoint, DataPoint.product_id == Product.id)
            .filter(Product.category_id == cat.id, DataPoint.status == "manual_review_needed")
            .distinct()
            .all()
        }

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

        # 默认顺序与后端一致：需人工核查 → 数据不完整 → 通用款 → 具体型号按综合分降序
        product_rows = []
        for p in products:
            scores = scorer.calc_product_scores(p, dim_map, {}, all_dim_values)
            total = Scorer.calc_total_score(scores)
            # 缺失权重占比 ≥30% → 数据不完整（评分基于少数维度不可信）
            data_incomplete = Scorer.missing_weight_ratio(scores) >= 0.3
            product_rows.append((p, total, scores, data_incomplete))
        product_rows.sort(key=lambda x: (
            1 if x[0].id in review_ids else 0,
            1 if x[3] else 0,
            1 if is_generic_product(x[0].brand, x[0].model or "") else 0,
            -x[1],
        ))

        for p, total, scores, data_incomplete in product_rows:
            # 产品 JSON 只保留本品类维度定义的键（清理历史残留）
            dims_data = {k: v for k, v in (p.dimensions or {}).items() if k in dim_map}
            # 多源核验状态：已核验维度列表 + 产品级标记
            verify_dims = [dk for dk in dim_map if VERIFY_MAP.get((p.id, dk)) == "verified"]
            if verify_dims:
                # 核心维度（权重 top3）全部核验 → verified；否则 partial
                top3 = sorted(dim_map.values(), key=lambda d: d.default_weight or 0, reverse=True)[:3]
                verify_status = "verified" if all(d.dim_key in verify_dims for d in top3) else "partial"
            else:
                verify_status = ""
            cat_data["products"].append(
                {
                    "id": p.id,
                    "brand": p.brand,
                    "model": p.model or "",
                    "price_low": p.price_low or 0,
                    "price_high": p.price_high or 0,
                    "price_collected_at": p.price_collected_at.strftime("%Y-%m-%d") if p.price_collected_at else "",
                    "needs_review": p.id in review_ids,
                    "data_incomplete": data_incomplete,
                    "verify_dims": verify_dims,
                    "verify_status": verify_status,
                    "dimensions": dims_data,
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
