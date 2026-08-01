"""加权评分排序引擎 — 全局 min/max 归一化"""
import json
from sqlalchemy.orm import Session

from backend.database import Dimension, Product
from backend.schemas import ProductDim

# 所有 enum 维度值 → 分数的硬编码映射（来自 SCHEMA.md 第 2、3 节）
ENUM_SCORE_MAP: dict[str, dict[str, int]] = {
    "能效等级": {
        "一级": 100, "1级": 100, "1": 100,
        "二级": 70, "2级": 70, "2": 70,
        "三级": 40, "3级": 40, "3": 40,
        "四级": 10, "4级": 10, "4": 10,
        "五级": 0, "5级": 0, "5": 0,
    },
    "水效等级": {
        "一级": 100, "1级": 100, "1": 100,
        "二级": 60, "2级": 60, "2": 60,
        "三级": 20, "3级": 20, "3": 20,
    },
    "面板材质": {
        "钢化玻璃": 90, "不锈钢": 70, "陶瓷": 80, "岩板": 80, "陶瓷/岩板": 80,
    },
    "类型": {
        # 洗碗机类型
        "嵌入式": 90, "独立式": 80, "水槽式": 70, "台式": 60,
        "独嵌两用": 85,
        # 热水器类型
        "燃气": 90, "电储水": 75, "空气能": 80,
    },
    "烘干方式": {
        "晶蕾": 100, "热交换": 85, "热风": 80, "冷凝": 65, "余热": 60, "排气": 40,
        "双擎热泵": 95, "热泵": 85,
        "智能开门": 75,
    },
    "门型": {
        "法式多门": 90, "十字门": 85, "对开门": 75, "三门": 65, "双门": 55,
    },
    "制冷方式": {
        "风冷": 100, "混冷": 85, "直冷": 50,
    },
    "消毒方式": {
        "三重消毒(高温+紫外+臭氧)": 100, "光热混动": 90, "高温+紫外": 80, "高温": 60,
    },
    "压缩机": {
        "自研变频": 90, "自研全直流": 85, "美芝": 80, "三菱": 85, "三洋双缸": 70,
        # 补充真实取值（DB 查询：56 个产品 14 种取值；复合值取成分均值，括号注释值取主品牌分）
        "凌达": 85, "海立": 78, "自研压缩机": 75,
        "美芝/海立": 79, "三菱/海立": 82, "三菱/自研": 80,
        "美芝压缩机": 80, "美芝(自研)": 80, "美芝(美的同款)": 80, "凌达(自研)": 85,
    },
    "过滤等级": {
        "H13 HEPA": 100, "H12": 80, "H11": 60, "静电集尘": 70,
    },
    "安装方式": {
        "管道式": 90, "壁挂式": 70, "立柜式": 75,
    },
    "拖地方式": {
        "恒压活水滚筒": 95, "圆拖布旋转": 80, "履带式洗地": 85, "平板拖": 60,
    },
    "避障技术": {
        "3D结构光+AI": 90, "真双目": 85, "激光+AI": 75, "激光": 65,
    },
    "基站功能": {
        "全能基站": 90, "全能+热水洗": 95, "基础功能": 60,
    },
    "加热方式": {
        "即热式": 100, "储热式": 50,
    },
    "冲洗技术": {
        "超漩虹吸": 90, "脉冲水流": 85, "多模式冲洗": 80, "卫洗丽": 95,
        "翻转冲刷": 90,
    },
    "翻盖方式": {
        "自动感应": 90, "脚感": 85, "手动": 60,
    },
    "恒温技术": {
        "双控伺服": 95, "水量伺服": 85, "燃气比例阀": 65,
    },
    "电机类型": {
        "DD直驱": 95, "FPA直驱": 95, "BLDC变频": 75, "皮带定频": 40,
    },
    "面板类型": {
        "QD-OLED": 100, "OLED": 95, "QD-MiniLED": 90, "MiniLED": 80, "ULED": 75, "LCD": 50,
    },
    "音响": {
        "帝瓦雷": 95, "2.1声道杜比": 85, "屏幕发声": 80, "2.0声道": 65,
    },
}


# 价格维度 → 产品列映射（价格为单一事实源，不入 dimensions）
PRICE_DIM_KEYS = {"价格_low": "price_low", "价格_high": "price_high"}


class Scorer:
    """评分引擎：标准化 + 加权综合分"""

    def __init__(self, db: Session):
        self.db = db

    def normalize_float(self, value, all_values: list, dim_def: Dimension) -> float:
        """float 标准化：全局 min/max 归一到 0-100"""
        try:
            v = float(value)
        except (ValueError, TypeError):
            return 0

        nums = []
        for x in all_values:
            try:
                nums.append(float(x))
            except (ValueError, TypeError):
                continue

        if not nums:
            return 50

        min_v, max_v = min(nums), max(nums)
        if max_v == min_v:
            return 50

        if dim_def.higher_better:
            return (v - min_v) / (max_v - min_v) * 100
        else:
            return (max_v - v) / (max_v - min_v) * 100

    def normalize_enum(self, value, dim_def: Dimension) -> float:
        """enum 标准化：从硬编码映射表获取分数，找不到则按 enum_values 位置降序"""
        if value is None:
            return 0

        s = str(value).strip()
        mapping = ENUM_SCORE_MAP.get(dim_def.dim_key, {})
        if s in mapping:
            return float(mapping[s])

        # fallback：按 enum_values 列表位置降序（第一项 100，每后移一项减 30）
        if dim_def.enum_values:
            try:
                enum_list = json.loads(dim_def.enum_values) if isinstance(dim_def.enum_values, str) else dim_def.enum_values
            except (json.JSONDecodeError, TypeError):
                enum_list = []
            if isinstance(enum_list, list):
                for i, ev in enumerate(enum_list):
                    if s == str(ev).strip():
                        return max(100 - i * 30, 10)
        return 50

    @staticmethod
    def normalize_bool(value) -> float:
        """bool 标准化：true=100, false=0"""
        return 100.0 if value else 0.0

    def get_normalized_score(self, value, dim_def: Dimension, all_values: list) -> float:
        """根据 dim_def.type 调度到对应标准化方法"""
        if value is None:
            return 0
        if dim_def.type == "float":
            return self.normalize_float(value, all_values, dim_def)
        elif dim_def.type == "enum":
            return self.normalize_enum(value, dim_def)
        elif dim_def.type == "bool":
            return self.normalize_bool(value)
        return 0

    def calc_product_scores(
        self, product: Product, dims_map: dict, custom_weights: dict, all_dim_values: dict
    ) -> dict[str, ProductDim]:
        """计算单个产品各维度的标准化得分"""
        scores = {}
        dims_data = product.dimensions or {}

        for dim_key, dim_def in dims_map.items():
            if dim_key in PRICE_DIM_KEYS:
                # 价格从产品列读取（0 视为无价格）
                raw_value = getattr(product, PRICE_DIM_KEYS[dim_key], None)
                if not raw_value:
                    raw_value = None
            else:
                raw_value = dims_data.get(dim_key)
            weight = custom_weights.get(dim_key, dim_def.default_weight or 50)

            if raw_value is None:
                scores[dim_key] = ProductDim(raw=None, normalized=0, weight=weight)
                continue

            all_values = all_dim_values.get(dim_key, [])
            normalized = self.get_normalized_score(raw_value, dim_def, all_values)
            scores[dim_key] = ProductDim(raw=raw_value, normalized=normalized, weight=weight)

        return scores

    @staticmethod
    def calc_total_score(dim_scores: dict[str, ProductDim]) -> float:
        """综合得分 = Σ(normalized × weight) / Σ(weight)"""
        total_weight = sum(s.weight for s in dim_scores.values())
        if total_weight == 0:
            return 0
        return sum(s.normalized * s.weight for s in dim_scores.values()) / total_weight

    @staticmethod
    def collect_all_dim_values(products: list[Product], dims_map: dict) -> dict[str, list]:
        """收集品类所有产品的维度值（供全局 min/max 归一化使用）"""
        all_values: dict[str, list] = {}
        for dim_key in dims_map:
            vals = []
            for p in products:
                if dim_key in PRICE_DIM_KEYS:
                    v = getattr(p, PRICE_DIM_KEYS[dim_key], None)
                else:
                    dim_data = p.dimensions or {}
                    v = dim_data.get(dim_key)
                if v is None:
                    continue
                if dim_key in PRICE_DIM_KEYS and v == 0:
                    # 价格 0 视为无价格，不参与归一化范围
                    continue
                vals.append(v)
            all_values[dim_key] = vals
        return all_values
