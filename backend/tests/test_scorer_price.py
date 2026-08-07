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

    def test_price_log_normalization(self):
        """价格用对数归一化（higher_better=False）：
        分数差与倍差成正比——500 vs 900 的差距远小于 100 vs 500。"""
        dim = make_dim("价格_low", higher_better=False, weight=50)
        scorer = Scorer(db=None)
        # 经 get_normalized_score 走价格对数分支
        self.assertEqual(scorer.get_normalized_score(100, dim, [100, 900]), 100.0)
        self.assertEqual(scorer.get_normalized_score(900, dim, [100, 900]), 0.0)
        # 对数域：log500 位于 log100~log900 的 26.8% 处（线性归一化下是 50%），
        # 高价区间内差距被压缩，符合用户价格感知
        self.assertAlmostEqual(scorer.get_normalized_score(500, dim, [100, 900]), 26.8, places=1)

    def test_linear_dimension_unchanged(self):
        """非价格 float 维度保持线性 min/max 归一化。"""
        dim = make_dim("风量_m3", higher_better=True, weight=90)
        scorer = Scorer(db=None)
        self.assertEqual(scorer.normalize_float(100, [100, 900], dim), 0.0)
        self.assertEqual(scorer.normalize_float(500, [100, 900], dim), 50.0)
        self.assertEqual(scorer.normalize_float(900, [100, 900], dim), 100.0)

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

    def test_missing_dims_excluded_from_total(self):
        """缺失维度不参与加权平均：数据未录入不等于参数差，不应按 0 分拖累总分。"""
        dim_price = make_dim("价格_low", higher_better=False, weight=50)
        dim_cap = make_dim("容量_L", higher_better=True, weight=80)
        dims_map = {"价格_low": dim_price, "容量_L": dim_cap}
        scorer = Scorer(db=None)

        # 容量缺失：总分只按价格算（价格最低 → 100 分），而不是被缺失维度拉低
        scores = scorer.calc_product_scores(
            make_product(price_low=100),
            dims_map, {}, {"价格_low": [100, 500], "容量_L": [400, 600]},
        )
        self.assertEqual(Scorer.calc_total_score(scores), 100.0)
        # 缺失权重占比：容量(80) / (价格50+容量80) = 61.5%
        self.assertAlmostEqual(Scorer.missing_weight_ratio(scores), 80 / 130, places=6)

        # 全部缺失（价格 0 视为无价格）：总分 0，不除零
        scores2 = scorer.calc_product_scores(
            make_product(price_low=0),
            dims_map, {}, {"价格_low": [100, 500], "容量_L": [400, 600]},
        )
        self.assertEqual(Scorer.calc_total_score(scores2), 0.0)

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
