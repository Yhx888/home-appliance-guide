"""评分变更：价格维度入综合分 + 主观规则维度降权

1. 为 cat-1~cat-7、cat-9~cat-17 各插入价格维度 dim_key="价格_low"
   （weight=50，higher_better=false，经 scorer.PRICE_DIM_KEYS 从产品列读取）
2. 满意度评分 75→10、线上份额_pct 30→10（无真实数据点来源的规则维度降权）
3. cat-8 中央空调保留原业务价格维度，不重复插入

幂等：已存在的维度/权重不会重复插入。
运行：python backend/apply_scoring_changes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, Category, Dimension


PRICE_DIM_KEY = "价格_low"
PRICE_DIM = {
    "dim_key": PRICE_DIM_KEY,
    "label": "价格",
    "type": "float",
    "unit": "元",
    "higher_better": False,
    "default_weight": 50,
    "enum_values": "",
}
WEIGHT_CHANGES = {
    "满意度评分": 10,
    "线上份额_pct": 10,
}


def main():
    db = SessionLocal()
    inserted = 0
    weight_updated = 0
    try:
        for cat in db.query(Category).filter(Category.slug.like("cat-%")).order_by(Category.sort_order).all():
            # cat-8 中央空调保留 价格_全屋_万/风管机3匹_元，不插入通用价格维度
            if cat.slug == "cat-8":
                continue
            exists = (
                db.query(Dimension)
                .filter(Dimension.category_id == cat.id, Dimension.dim_key == PRICE_DIM_KEY)
                .first()
            )
            if exists:
                if exists.default_weight != PRICE_DIM["default_weight"]:
                    exists.default_weight = PRICE_DIM["default_weight"]
                    weight_updated += 1
                continue
            db.add(Dimension(category_id=cat.id, **PRICE_DIM))
            inserted += 1

        # 主观规则维度降权
        for dim in db.query(Dimension).filter(Dimension.dim_key.in_(list(WEIGHT_CHANGES))).all():
            new_w = WEIGHT_CHANGES[dim.dim_key]
            if dim.default_weight != new_w:
                print(f"权重调整: {dim.category.name if dim.category else '?'}/{dim.dim_key} {dim.default_weight} -> {new_w}")
                dim.default_weight = new_w
                weight_updated += 1

        db.commit()
    finally:
        db.close()
    print(f"完成：插入价格维度 {inserted} 个品类，权重更新 {weight_updated} 处")


if __name__ == "__main__":
    main()
