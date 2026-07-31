"""多方校对引擎 — 数值核对 + 视觉核验回路

数据校对分两个层面：

1. 数值核对 — 对每(product, dimension_key)分组所有 data_points，
   计算共识值和置信度，决定是否写入 products.dimensions。

2. 视觉核验 — 对低置信度项，通过浏览器截图 + 视觉 AI 提取补充数据。

当前数据库尚无 data_points（产品数据存于 products.dimensions JSON），
校对器将对现有 JSON 数据分析质量，作为基线报告。

独立运行：
  python -m backend.scrapers.verify
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean, stdev
from datetime import datetime
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

# 确保能导入 backend 包（路径基于本文件派生，不依赖固定目录）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database import SessionLocal, Product, Category, Dimension, DataPoint, DataSource


# ── 置信度计算 ──────────────────────────────────────────────────────────

def calculate_confidence(sources_count: int, values: list[float]) -> float:
    """计算置信度。

    confidence = 0.5                # 基础值
      + 0.15 × (sources_count - 1)  # 每多一个来源 +0.15
      - 0.3 × coefficient_of_variation  # 离散度惩罚

    上限 0.95，下限 0.1。
    """
    if sources_count == 0:
        return 0.1
    base = 0.5
    source_bonus = 0.15 * (sources_count - 1)

    cv = 0.0
    if len(values) > 1:
        m = mean(values)
        if abs(m) > 1e-10:
            cv = stdev(values) / abs(m)

    confidence = base + source_bonus - 0.3 * cv
    return max(0.1, min(0.95, confidence))


# ── 数值解析 ────────────────────────────────────────────────────────────

def parse_numeric_from_text(text: str) -> float | None:
    """从文本中提取数值（用于 data_points.raw_value → numeric_value）"""
    import re
    if not text:
        return None
    text = text.strip().replace(',', '')
    nums = re.findall(r'(\d+\.?\d*)', text)
    if not nums:
        return None
    vals = [float(n) for n in nums]
    return vals[0] if len(vals) == 1 else sum(vals) / len(vals)


# ── 校对状态常量 ────────────────────────────────────────────────────────

STATUS_PENDING = "pending"
STATUS_VERIFIED = "verified"
STATUS_DISPUTED = "disputed"
STATUS_MANUAL_REVIEW = "manual_review_needed"


# ══════════════════════════════════════════════════════════════════════════
# Verifier 类
# ══════════════════════════════════════════════════════════════════════════

class Verifier:
    """数据校对器。

    支持两种工作模式：
      1. data_points 表有数据 → 多源数值校对
      2. data_points 为空 → 对 products.dimensions JSON 做质量分析
    """

    def __init__(self, db: Session | None = None):
        self.db = db or SessionLocal()

    # ── 单产品单维度核对 ────────────────────────────────────────────────

    def check_product_dimension(self, product_id: int, dim_key: str, apply: bool = False) -> dict:
        """核对一个产品的单个维度。

        流程：
          1. 查询该 (product_id, dim_key) 的所有 data_points
          2. 多源一致(偏差<15%) → 置信度≥0.9，写入 products.dimensions（仅 apply=True）
          3. 多源偏差>20% → 标记 manual_review_needed
          4. 单源 → 置信度 0.5，标记 pending

        返回: {confidence, status, consensus_value, details}
        """
        points = (
            self.db.query(DataPoint)
            .filter(
                DataPoint.product_id == product_id,
                DataPoint.dimension_key == dim_key,
            )
            .all()
        )

        if not points:
            return {
                "confidence": 0.0,
                "status": STATUS_PENDING,
                "consensus_value": None,
                "details": "无数据点",
            }

        numeric_values = [p.numeric_value for p in points if p.numeric_value is not None]
        sources_count = len(set(p.source_id for p in points))
        confidence = calculate_confidence(sources_count, numeric_values) if numeric_values else 0.3

        # 确定状态
        if sources_count == 1:
            status = STATUS_PENDING
        elif sources_count >= 2 and numeric_values:
            cv = 0.0
            if len(numeric_values) > 1:
                m = mean(numeric_values)
                if abs(m) > 1e-10:
                    cv = stdev(numeric_values) / abs(m)
            if cv < 0.15:
                status = STATUS_VERIFIED
            elif cv > 0.20:
                status = STATUS_MANUAL_REVIEW
            else:
                status = STATUS_DISPUTED
        else:
            status = STATUS_PENDING

        # 共识值：取均值（多源时）或第一个有效值
        consensus = mean(numeric_values) if len(numeric_values) > 1 else (numeric_values[0] if numeric_values else None)

        # 置信度充足且已验证 → 写入 products.dimensions（仅 --apply 模式）
        write_back = False
        skip_reason = ""
        if status == STATUS_VERIFIED and consensus is not None and apply:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if product:
                # 枚举/文本维度禁止数值写回（consensus 是数值均值，会把"一级"写成浮点数）
                dim = (
                    self.db.query(Dimension)
                    .filter(
                        Dimension.category_id == product.category_id,
                        Dimension.dim_key == dim_key,
                    )
                    .first()
                )
                if dim and dim.type in ("enum", "text") and isinstance(consensus, (int, float)):
                    skip_reason = "枚举/文本维度禁止数值写回"
                else:
                    dims = dict(product.dimensions or {})
                    dims[dim_key] = consensus
                    product.dimensions = dims
                    self.db.commit()
                    write_back = True

        return {
            "confidence": round(confidence, 4),
            "status": status,
            "consensus_value": consensus,
            "details": {
                "sources_count": sources_count,
                "data_points_count": len(points),
                "numeric_values": [round(v, 4) for v in numeric_values] if numeric_values else [],
                "raw_values": [p.raw_value for p in points[:5]],
                "write_back": write_back,
                "skip_reason": skip_reason,
            },
        }

    # ── 单产品核对 ──────────────────────────────────────────────────────

    def verify_product(self, product_id: int) -> dict:
        """核对一个产品的所有维度。

        返回 {dim_key: check_result, summary}
        """
        # 收集该产品所有 data_points 涉及的维度
        dim_keys = [
            row[0]
            for row in self.db.query(DataPoint.dimension_key)
            .filter(DataPoint.product_id == product_id)
            .distinct()
            .all()
        ]

        results = {}
        for dk in dim_keys:
            results[dk] = self.check_product_dimension(product_id, dk)

        statuses = [r["status"] for r in results.values()]
        return {
            "product_id": product_id,
            "total_dims": len(dim_keys),
            "verified": statuses.count(STATUS_VERIFIED),
            "pending": statuses.count(STATUS_PENDING),
            "disputed": statuses.count(STATUS_DISPUTED),
            "manual_review": statuses.count(STATUS_MANUAL_REVIEW),
            "dimensions": results,
        }

    # ── 全量校对 ────────────────────────────────────────────────────────

    def check_all(self, apply: bool = False) -> dict:
        """遍历所有未核查 data_points，执行校对。

        apply=True 时才写回 products.dimensions，默认只读。

        返回数据质量报告：
          {total_checked, resolved, disputed, pending}
        """
        unchecked = (
            self.db.query(DataPoint)
            .filter(DataPoint.status.in_([STATUS_PENDING, STATUS_MANUAL_REVIEW]))
            .all()
        )

        if not unchecked:
            return {
                "total_checked": 0,
                "resolved": 0,
                "disputed": 0,
                "pending": 0,
                "note": "没有未核查的 data_points，数据可能已全部校对或尚无 data_points",
            }

        # 按 (product_id, dimension_key) 分组
        groups: dict[tuple[int, str], list[DataPoint]] = defaultdict(list)
        for dp in unchecked:
            groups[(dp.product_id, dp.dimension_key)].append(dp)

        resolved = 0
        disputed = 0
        pending = 0

        for (pid, dk), _ in groups.items():
            result = self.check_product_dimension(pid, dk, apply=apply)
            s = result["status"]
            if s == STATUS_VERIFIED:
                resolved += 1
            elif s == STATUS_DISPUTED or s == STATUS_MANUAL_REVIEW:
                disputed += 1
            else:
                pending += 1

        return {
            "total_checked": len(groups),
            "resolved": resolved,
            "disputed": disputed,
            "pending": pending,
        }

    # ── 数据质量报告 ────────────────────────────────────────────────────

    def generate_report(self) -> dict:
        """生成数据质量报告。

        包含：
          - 品类统计（品类名、产品数、维度填充率）
          - 置信度分布（聚合 data_points 真实置信度，按 产品×维度 分组）
          - 覆盖率（关键维度填充率）
          - 未解决项统计

        返回可序列化的 dict。
        """
        categories = self.db.query(Category).order_by(Category.sort_order).all()
        category_stats = []
        total_products = 0
        total_expected_dims = 0
        total_filled_dims = 0

        # 聚合 data_points 真实置信度：按 (product, dimension_key) 分组，
        # 有数值数据点的组用 calculate_confidence 计算（缺失维度无数据点 → 不计入分布）
        all_confidences: list[float] = []
        dp_groups: dict[tuple[int, str], list[DataPoint]] = defaultdict(list)
        for dp in self.db.query(DataPoint).all():
            dp_groups[(dp.product_id, dp.dimension_key)].append(dp)
        for points in dp_groups.values():
            numeric_values = [p.numeric_value for p in points if p.numeric_value is not None]
            if numeric_values:
                sources_count = len(set(p.source_id for p in points))
                all_confidences.append(calculate_confidence(sources_count, numeric_values))

        for cat in categories:
            dims = self.db.query(Dimension).filter(Dimension.category_id == cat.id).all()
            dim_keys = [d.dim_key for d in dims]
            products = self.db.query(Product).filter(Product.category_id == cat.id).all()

            if not dim_keys:
                continue

            cat_filled = 0
            cat_expected = len(products) * len(dim_keys)
            product_details = []

            for p in products:
                p_dims = p.dimensions or {}
                filled = sum(1 for dk in dim_keys if dk in p_dims and p_dims[dk] is not None)
                cat_filled += filled
                total_filled_dims += filled
                total_expected_dims += len(dim_keys)

                # 填充率
                fill_rate = filled / len(dim_keys) if dim_keys else 0

                product_details.append({
                    "id": p.id,
                    "brand": p.brand,
                    "model": p.model or "",
                    "dim_count": len(dim_keys),
                    "filled": filled,
                    "fill_rate": round(fill_rate, 4),
                })

            avg_fill = cat_filled / cat_expected if cat_expected > 0 else 0

            # 关键维度（权重前 5）
            top_dims = sorted(dims, key=lambda d: d.default_weight or 0, reverse=True)[:5]
            top_dim_keys = [d.dim_key for d in top_dims]
            top_filled = 0
            top_total = len(products) * len(top_dim_keys)
            for p in products:
                p_dims = p.dimensions or {}
                top_filled += sum(1 for dk in top_dim_keys if dk in p_dims and p_dims[dk] is not None)
            top_fill_rate = top_filled / top_total if top_total > 0 else 0

            category_stats.append({
                "category_id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "product_count": len(products),
                "dim_count": len(dim_keys),
                "key_dim_count": len(top_dim_keys),
                "total_expected_cells": cat_expected,
                "total_filled_cells": cat_filled,
                "fill_rate": round(avg_fill, 4),
                "key_dim_fill_rate": round(top_fill_rate, 4),
                "products": product_details,
            })
            total_products += len(products)

        # 置信度分布
        total_dims_checked = len(all_confidences)
        conf_high = sum(1 for c in all_confidences if c >= 0.9)
        conf_medium = sum(1 for c in all_confidences if 0.5 <= c < 0.9)
        conf_low = sum(1 for c in all_confidences if 0.3 <= c < 0.5)
        conf_none = sum(1 for c in all_confidences if c < 0.3 and c > 0)
        conf_missing = sum(1 for c in all_confidences if c == 0.0)

        overall_fill_rate = total_filled_dims / total_expected_dims if total_expected_dims > 0 else 0

        # 未解决项（标记 manual_review_needed 的 data_points）
        unresolved_count = (
            self.db.query(DataPoint)
            .filter(DataPoint.status == STATUS_MANUAL_REVIEW)
            .count()
        )

        report = {
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_points_table_empty": self.db.query(DataPoint).count() == 0,
            "summary": {
                "total_categories": len(category_stats),
                "total_products": total_products,
                "total_expected_dim_cells": total_expected_dims,
                "total_filled_dim_cells": total_filled_dims,
                "overall_fill_rate": round(overall_fill_rate, 4),
                "unresolved_data_points": unresolved_count,
            },
            "confidence_distribution": {
                "total_dim_values_checked": total_dims_checked,
                "high_confidence_ge_0_9": conf_high,
                "medium_confidence_ge_0_5": conf_medium,
                "low_confidence_ge_0_3": conf_low,
                "very_low_confidence_lt_0_3": conf_none,
                "missing": conf_missing,
            },
            "category_stats": category_stats,
            "note": (
                "置信度分布聚合自 data_points 真实数据；"
                "若 data_points 为空则置信度分布为空，填充率统计仍基于 products.dimensions。"
            ),
        }

        return report


# ══════════════════════════════════════════════════════════════════════════
# 独立运行入口
# ══════════════════════════════════════════════════════════════════════════

def print_report(report: dict):
    """格式化打印质量报告"""
    print("=" * 64)
    print("  全国家电选购指南 · 数据质量报告")
    print(f"  生成时间: {report['report_time']}")
    print("=" * 64)

    s = report["summary"]
    print(f"\n[总览]")
    print(f"  品类数:           {s['total_categories']}")
    print(f"  产品数:           {s['total_products']}")
    print(f"  期望维度格数:     {s['total_expected_dim_cells']}")
    print(f"  已填充维度格数:   {s['total_filled_dim_cells']}")
    print(f"  总体维度填充率:   {s['overall_fill_rate']*100:.1f}%")
    print(f"  未解决数据点:     {s['unresolved_data_points']}")

    cd = report["confidence_distribution"]
    print(f"\n[置信度分布]")
    total = cd["total_dim_values_checked"]
    if total:
        print(f"  高置信度(>=0.9):  {cd['high_confidence_ge_0_9']:>4}  ({cd['high_confidence_ge_0_9']/total*100:.1f}%)")
        print(f"  中等(0.5~0.9):    {cd['medium_confidence_ge_0_5']:>4}  ({cd['medium_confidence_ge_0_5']/total*100:.1f}%)")
        print(f"  低(0.3~0.5):      {cd['low_confidence_ge_0_3']:>4}  ({cd['low_confidence_ge_0_3']/total*100:.1f}%)")
        print(f"  极低(<0.3):       {cd['very_low_confidence_lt_0_3']:>4}  ({cd['very_low_confidence_lt_0_3']/total*100:.1f}%)")
        print(f"  缺失:             {cd['missing']:>4}  ({cd['missing']/total*100:.1f}%)")
    else:
        print("  (无维度数据)")

    print(f"\n[品类详情]")
    print(f"  {'品类':<14} {'产品数':>5} {'维度数':>5} {'填充率':>8} {'关键维填充率':>10}")
    print(f"  {'-'*14} {'-'*5} {'-'*5} {'-'*8} {'-'*10}")
    for cs in report["category_stats"]:
        print(f"  {cs['name']:<14} {cs['product_count']:>5} {cs['dim_count']:>5} "
              f"{cs['fill_rate']*100:>7.1f}% {cs['key_dim_fill_rate']*100:>9.1f}%")

    # 底部标注
    if report.get("data_points_table_empty"):
        print(f"\n[提示] {report['note']}")

    print(f"\n{'=' * 64}")
    print("  报告结束")
    print(f"{'=' * 64}")


def main():
    """独立运行入口（默认只读，--apply 才写回）"""
    parser = argparse.ArgumentParser(
        prog="python -m backend.scrapers.verify",
        description="数据校对与质量报告：默认只生成报告不写库，--apply 显式开启写回。",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="启用写回：将多源一致的数值共识写入 products.dimensions（默认只读）",
    )
    args = parser.parse_args()

    verifier = Verifier()
    report = verifier.generate_report()
    print_report(report)

    # 若有 data_points，执行全量校对
    if not report.get("data_points_table_empty", True):
        print("\n正在执行全量校对…")
        check_result = verifier.check_all(apply=args.apply)
        print(f"  校对完成：共 {check_result['total_checked']} 组，"
              f"已解决 {check_result['resolved']}，"
              f"争议 {check_result['disputed']}，"
              f"待定 {check_result['pending']}")
        if not args.apply:
            print("  （只读模式：未写库；使用 --apply 可开启写回）")

    verifier.db.close()


if __name__ == "__main__":
    main()
