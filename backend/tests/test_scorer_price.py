"""评分引擎测试：价格维度、权重调整、新枚举映射"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scorer import Scorer


def make_dim(dim_key, type_="float", higher_better=True, weight=50, enum_values=""):
    return SimpleNamespace(
        dim_key=dim_key, label=dim_key, type=type_, unit="",
        higher_better=higher_better, default_weight=weight, enum_values=enum_values,
    )


def make_product(price_low=0.0, price_high=0.0, dimensions=None):
    return SimpleNamespace(price_low=price_low, price_high=price_high, dimensions=dimensions or {})


class TestPriceScoring(unittest.TestCase):
    """价格入综合分的核心行为。"""

    def test_price_lower_better_normalization(self):
        """价格越低归一化分越高（higher_better=False）。"""
        dim = make_dim("价格_low", higher_better=False, weight=50)
        scorer = Scorer(db=None)
        self.assertEqual(scorer.normalize_float(100, [100, 900], dim), 100.0)
        self.assertEqual(scorer.normalize_float(900, [100, 900], dim), 0.0)
        self.assertEqual(scorer.normalize_float(500, [100, 900], dim), 50.0)

    def test_missing_price_scores_zero(self):
        """价格缺失（产品列 0/None）时该维度得 0 分。"""
        dim = make_dim("价格_low", higher_better=False, weight=50)
        dims_map = {"价格_low": dim}
        scorer = Scorer(db=None)
        product = make_product(price_low=0)
        scores = scorer.calc_product_scores(product, dims_map, {}, {"价格_low": [100, 900]})
        self.assertEqual(scores["价格_low"].normalized, 0.0)

    def test_price_weight_in_total(self):
        """价格权重 50 参与综合分：低价产品应显著高于同参数高价产品。"""
        dim_price = make_dim("价格_low", higher_better=False, weight=50)
        dim_capacity = make_dim("容量_L", higher_better=True, weight=80)
        dims_map = {"价格_low": dim_price, "容量_L": dim_capacity}
        scorer = Scorer(db=None)

        cheap = scorer.calc_product_scores(
            make_product(price_low=100, dimensions={"容量_L": 500}),
            dims_map, {}, {"价格_low": [100, 500], "容量_L": [400, 600]},
        )
        expensive = scorer.calc_product_scores(
            make_product(price_low=500, dimensions={"容量_L": 500}),
            dims_map, {}, {"价格_low": [100, 500], "容量_L": [400, 600]},
        )
        self.assertGreater(
            Scorer.calc_total_score(cheap), Scorer.calc_total_score(expensive)
        )

    def test_subjective_dim_weight_reduced(self):
        """满意度评分降权后（10），其高低分对综合分影响显著小于原权重 75。"""
        scorer = Scorer(db=None)
        dim_cap = make_dim("容量_L", higher_better=True, weight=80)

        def score_diff(sat_weight):
            dim_sat = make_dim("满意度评分", type_="float", higher_better=True, weight=sat_weight)
            dims_map = {"满意度评分": dim_sat, "容量_L": dim_cap}
            high = scorer.calc_product_scores(
                make_product(dimensions={"满意度评分": 5.0, "容量_L": 500}),
                dims_map, {}, {"满意度评分": [3.0, 5.0], "容量_L": [400, 600]},
            )
            low = scorer.calc_product_scores(
                make_product(dimensions={"满意度评分": 3.0, "容量_L": 500}),
                dims_map, {}, {"满意度评分": [3.0, 5.0], "容量_L": [400, 600]},
            )
            return Scorer.calc_total_score(high) - Scorer.calc_total_score(low)

        diff_new = score_diff(10)    # 降权后
        diff_old = score_diff(75)    # 原权重
        self.assertAlmostEqual(diff_new, 100.0 * 10 / 90, places=6)   # ≈11.11
        self.assertAlmostEqual(diff_old, 100.0 * 75 / 155, places=6)  # ≈48.39
        self.assertLess(diff_new, diff_old)

    def test_new_enum_mappings(self):
        """新款真实枚举值映射：独嵌两用 85、智能开门 75、翻转冲刷 90。"""
        dim_type = make_dim("类型", type_="enum", enum_values='["嵌入式","独立式"]')
        dim_dry = make_dim("烘干方式", type_="enum", enum_values='["晶蕾","热交换"]')
        dim_rinse = make_dim("冲洗技术", type_="enum", enum_values='["超漩虹吸"]')
        scorer = Scorer(db=None)
        self.assertEqual(scorer.normalize_enum("独嵌两用", dim_type), 85.0)
        self.assertEqual(scorer.normalize_enum("智能开门", dim_dry), 75.0)
        self.assertEqual(scorer.normalize_enum("翻转冲刷", dim_rinse), 90.0)


if __name__ == "__main__":
    unittest.main()
