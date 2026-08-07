"""数据修复：隐藏 cat-17 非集成灶产品 + 移除编造维度 + 占位型号标记人工核查

一次性修复脚本（幂等，可重复执行）：
1. cat-17「集成灶等」混入垃圾处理器/管线机/净水器/蒸烤箱，被集成灶维度错配评分。
   → 按品牌/型号规则将非集成灶产品标记 hidden=True（数据库保留，展示/评分排除）。
2. 满意度评分 / 线上份额_pct 为 enrich 规则编造（无真实来源），从 dimensions 表删除。
3. 占位型号（西门子 旗舰款/各系列、老板/方太 旗舰款）插入 manual_review_needed 数据点，
   经 needs_review 机制自动排最后。
"""
import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "app.db"

# ── 1. cat-17 非集成灶规则（品牌级，cat-17 内这些品牌全部非集成灶） ──
NON_INTEGRATED_BRANDS = ["贝克巴斯", "爱适易", "沁园", "安吉尔", "A.O.史密斯", "凯度"]
NON_INTEGRATED_MODEL_KEYWORDS = ["管线机", "垃圾处理器", "MG908", "HGR2105B"]  # HGR2105B 为海尔壁挂管线机

# ── 3. 占位型号（无真实具体型号，需人工核查） ──
PLACEHOLDER_MODELS = [
    ("抽油烟机", "西门子", "旗舰款"),
    ("抽油烟机", "西门子", "各系列"),
    ("燃气灶", "老板", "旗舰款"),
    ("燃气灶", "方太", "旗舰款"),
]

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 确保 hidden 列存在（数据库迁移）
    cols = [r[1] for r in cur.execute("PRAGMA table_info(products)").fetchall()]
    if "hidden" not in cols:
        cur.execute("ALTER TABLE products ADD COLUMN hidden BOOLEAN DEFAULT 0")

    # ── 1. 隐藏 cat-17 非集成灶产品 ──
    rows = cur.execute(
        "SELECT id, brand, model FROM products WHERE category_id=17 AND hidden=0"
    ).fetchall()
    hidden_ids = []
    for r in rows:
        brand, model = r["brand"], r["model"] or ""
        if brand in NON_INTEGRATED_BRANDS:
            hidden_ids.append(r["id"])
        elif any(k in model for k in NON_INTEGRATED_MODEL_KEYWORDS):
            hidden_ids.append(r["id"])
    for pid in hidden_ids:
        cur.execute("UPDATE products SET hidden=1 WHERE id=?", (pid,))
    print(f"[1] cat-17 隐藏非集成灶产品: {len(hidden_ids)} 款 (id={sorted(hidden_ids)})")

    # ── 2. 删除编造维度定义 ──
    deleted = cur.execute(
        "DELETE FROM dimensions WHERE dim_key IN ('满意度评分', '线上份额_pct')"
    ).rowcount
    print(f"[2] 删除编造维度定义（满意度评分/线上份额_pct）: {deleted} 条")

    # 同步清理产品 dimensions JSON 中的残留键（保持数据整洁）
    cleaned = 0
    for r in cur.execute("SELECT id, dimensions FROM products").fetchall():
        dims = json.loads(r["dimensions"]) if r["dimensions"] else {}
        if "满意度评分" in dims or "线上份额_pct" in dims:
            dims.pop("满意度评分", None)
            dims.pop("线上份额_pct", None)
            cur.execute("UPDATE products SET dimensions=? WHERE id=?", (json.dumps(dims, ensure_ascii=False), r["id"]))
            cleaned += 1
    print(f"[2b] 清理产品 JSON 残留键: {cleaned} 款")

    # ── 3. 占位型号标记人工核查 ──
    src = cur.execute("SELECT id FROM data_sources WHERE platform='internal_review' LIMIT 1").fetchone()
    if not src:
        cur.execute(
            "INSERT INTO data_sources (platform, url, method) VALUES ('internal_review', '', 'manual')"
        )
        src_id = cur.lastrowid
    else:
        src_id = src["id"]

    marked = 0
    for cat_name, brand, model in PLACEHOLDER_MODELS:
        row = cur.execute(
            """SELECT p.id FROM products p JOIN categories c ON p.category_id=c.id
               WHERE c.name=? AND p.brand=? AND p.model=?""",
            (cat_name, brand, model),
        ).fetchone()
        if not row:
            print(f"  [3] 未找到占位型号: {cat_name} {brand} {model}")
            continue
        pid = row["id"]
        exists = cur.execute(
            "SELECT id FROM data_points WHERE product_id=? AND status='manual_review_needed' LIMIT 1",
            (pid,),
        ).fetchone()
        if not exists:
            cur.execute(
                """INSERT INTO data_points (product_id, dimension_key, source_id, raw_value, confidence, status)
                   VALUES (?, 'model', ?, '占位型号待核实', 0.3, 'manual_review_needed')""",
                (pid, src_id),
            )
            marked += 1
    print(f"[3] 占位型号标记 manual_review_needed: {marked} 款")

    conn.commit()
    conn.close()
    print("完成。请重新运行 export_static_data.py 导出 data.json。")

if __name__ == "__main__":
    main()
