"""种子数据脚本 — 从 index.html 解析所有品类数据并写入 SQLite"""
import re
import json
import sys
import io
from pathlib import Path

# 确保控制台输出兼容 GBK
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from bs4 import BeautifulSoup

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db, SessionLocal, Category, Dimension, Product

# ============================================================
# 1. 品类元信息
# ============================================================
CATEGORIES = [
    # (slug, name, icon, sort_order)
    ("cat-1", "抽油烟机", "🍳", 1),
    ("cat-2", "燃气灶", "🔥", 2),
    ("cat-3", "蒸烤箱", "🍞", 3),
    ("cat-4", "洗碗机", "🍽️", 4),
    ("cat-5", "净水器", "💧", 5),
    ("cat-6", "冰箱", "❄️", 6),
    ("cat-7", "消毒柜", "🧹", 7),
    ("cat-8", "中央空调", "🌬️", 8),
    ("cat-9", "新风系统", "🌿", 9),
    ("cat-10", "挂机/柜机空调", "🏠", 10),
    ("cat-11", "扫地机器人", "🤖", 11),
    ("cat-12", "空气净化器", "🌸", 12),
    ("cat-13", "智能马桶", "🚽", 13),
    ("cat-14", "热水器", "🚿", 14),
    ("cat-15", "洗衣机", "👕", 15),
    ("cat-16", "电视机", "📺", 16),
    ("cat-17", "集成灶等", "🔌", 17),
    # 专题（不做产品解析，仅写入 categories）
    ("topic-1", "全屋智能方案对比", "🏡", 18),
    ("topic-2", "售后维修红黑榜", "🏆", 19),
    ("topic-3", "用户口碑风云榜", "💬", 20),
    ("topic-4", "全生命周期成本", "💰", 21),
    ("topic-5", "按预算分级方案", "📊", 22),
    ("topic-6", "行业趋势", "📈", 23),
    ("topic-7", "特殊人群指南", "👶", 24),
    ("topic-8", "品牌软实力", "🏅", 25),
]

# ============================================================
# 2. 各品类维度定义（来自 SCHEMA.md）
# ============================================================
# 格式: (slug, dim_key, label, type, unit, higher_better, default_weight, enum_values)
DIMENSIONS = {
    "cat-1": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("风量_m3", "风量", "float", "m³/min", True, 90, None),
        ("静压_Pa", "最大静压", "float", "Pa", True, 85, None),
        ("噪音_dB", "噪音", "float", "dB", False, 60, None),
        ("能效等级", "能效等级", "enum", "", True, 50, json.dumps(["一级", "二级", "三级"], ensure_ascii=False)),
        ("保修_年", "保修", "float", "年", True, 40, None),
        ("线上份额_pct", "线上份额", "float", "%", True, 30, None),
        ("满意度评分", "满意度", "float", "分", True, 75, None),
    ],
    "cat-2": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("火力_kW", "火力", "float", "kW", True, 85, None),
        ("热效率_pct", "热效率", "float", "%", True, 80, None),
        ("面板材质", "面板材质", "enum", "", True, 40, json.dumps(["钢化玻璃", "不锈钢", "陶瓷"], ensure_ascii=False)),
        ("熄火保护", "熄火保护", "bool", "", True, 50, None),
        ("保修_年", "保修", "float", "年", True, 35, None),
    ],
    "cat-3": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("容量_L", "容量", "float", "L", True, 80, None),
        ("最高温度_C", "最高温度", "float", "°C", True, 60, None),
        ("有微波", "微波功能", "bool", "", True, 40, None),
        ("蒸功能评分", "蒸功能", "float", "分", True, 70, None),
        ("烤功能评分", "烤功能", "float", "分", True, 75, None),
        ("保修_年", "保修", "float", "年", True, 30, None),
    ],
    "cat-4": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("容量_套", "容量", "float", "套", True, 85, None),
        ("类型", "类型", "enum", "", True, 40, json.dumps(["嵌入式", "独立式", "水槽式", "台式"], ensure_ascii=False)),
        ("烘干方式", "烘干方式", "enum", "", True, 70, json.dumps(["晶蕾", "热交换", "热风", "余热"], ensure_ascii=False)),
        ("噪音_dB", "噪音", "float", "dB", False, 55, None),
        ("水效等级", "水效等级", "enum", "", True, 50, json.dumps(["一级", "二级", "三级"], ensure_ascii=False)),
        ("保修_年", "保修", "float", "年", True, 40, None),
    ],
    "cat-5": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("通量_G", "通量", "float", "G", True, 80, None),
        ("RO膜寿命_年", "RO膜寿命", "float", "年", True, 85, None),
        ("废水比", "废水比", "float", "", True, 60, None),
        ("年均耗材_元", "年均耗材", "float", "元", False, 75, None),
        ("过滤级数", "过滤级数", "float", "级", True, 40, None),
        ("保修_年", "保修", "float", "年", True, 35, None),
    ],
    "cat-6": [
        ("价格_low", "最低价", "float", "元", False, 65, None),
        ("价格_high", "最高价", "float", "元", False, 55, None),
        ("容量_L", "容量", "float", "L", True, 80, None),
        ("门型", "门型", "enum", "", True, 50, json.dumps(["法式多门", "十字门", "对开门", "三门", "双门"], ensure_ascii=False)),
        ("制冷方式", "制冷方式", "enum", "", True, 60, json.dumps(["风冷", "混冷", "直冷"], ensure_ascii=False)),
        ("双系统", "双系统", "bool", "", True, 70, None),
        ("嵌入深度_mm", "嵌入深度", "float", "mm", False, 45, None),
        ("保修_年", "保修", "float", "年", True, 35, None),
    ],
    "cat-7": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("容量_L", "容量", "float", "L", True, 75, None),
        ("消毒方式", "消毒方式", "enum", "", True, 80, json.dumps(["三重消毒(高温+紫外+臭氧)", "光热混动", "高温+紫外", "高温"], ensure_ascii=False)),
        ("杀菌率_pct", "杀菌率", "float", "%", True, 70, None),
        ("保修_年", "保修", "float", "年", True, 35, None),
    ],
    "cat-8": [
        ("价格_全屋_万", "全屋价格", "float", "万元", False, 60, None),
        ("风管机3匹_元", "3匹风管机", "float", "元", False, 65, None),
        ("压缩机", "压缩机", "enum", "", True, 80, json.dumps(["自研变频", "自研全直流", "美芝", "三菱", "三洋双缸"], ensure_ascii=False)),
        ("能效_APF", "能效 APF", "float", "", True, 75, None),
        ("噪音_dB", "噪音", "float", "dB", False, 60, None),
        ("保修_年", "保修", "float", "年", True, 50, None),
    ],
    "cat-9": [
        ("价格_low", "最低价", "float", "元", False, 60, None),
        ("价格_high", "最高价", "float", "元", False, 50, None),
        ("风量_m3h", "风量", "float", "m³/h", True, 85, None),
        ("过滤等级", "过滤等级", "enum", "", True, 80, json.dumps(["H13 HEPA", "H12", "H11", "静电集尘"], ensure_ascii=False)),
        ("热交换率_pct", "热交换率", "float", "%", True, 70, None),
        ("噪音_dB", "噪音", "float", "dB", False, 55, None),
        ("安装方式", "安装方式", "enum", "", True, 45, json.dumps(["管道式", "壁挂式", "立柜式"], ensure_ascii=False)),
    ],
    "cat-10": [
        ("价格_low", "最低价", "float", "元", False, 75, None),
        ("价格_high", "最高价", "float", "元", False, 65, None),
        ("能效_APF", "能效 APF", "float", "", True, 85, None),
        ("压缩机", "压缩机", "enum", "", True, 70, json.dumps(["自研变频", "自研全直流", "美芝", "三菱", "三洋双缸"], ensure_ascii=False)),
        ("噪音_dB", "噪音", "float", "dB", False, 60, None),
        ("自清洁", "自清洁", "bool", "", True, 50, None),
        ("保修_年", "保修", "float", "年", True, 45, None),
        ("匹数", "匹数", "float", "匹", True, 30, None),
    ],
    "cat-11": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("吸力_Pa", "吸力", "float", "Pa", True, 75, None),
        ("拖地方式", "拖地方式", "enum", "", True, 80, json.dumps(["恒压活水滚筒", "圆拖布旋转", "履带式洗地", "平板拖"], ensure_ascii=False)),
        ("避障技术", "避障技术", "enum", "", True, 70, json.dumps(["3D结构光+AI", "真双目", "激光+AI", "激光"], ensure_ascii=False)),
        ("基站功能", "基站功能", "enum", "", True, 65, json.dumps(["全能基站", "全能+热水洗", "基础功能"], ensure_ascii=False)),
        ("续航_min", "续航", "float", "分钟", True, 55, None),
        ("保修_年", "保修", "float", "年", True, 30, None),
    ],
    "cat-12": [
        ("价格_low", "最低价", "float", "元", False, 65, None),
        ("价格_high", "最高价", "float", "元", False, 55, None),
        ("颗粒物CADR", "颗粒物 CADR", "float", "m³/h", True, 85, None),
        ("甲醛CADR", "甲醛 CADR", "float", "m³/h", True, 80, None),
        ("噪音_dB", "噪音", "float", "dB", False, 50, None),
        ("滤芯寿命_年", "滤芯寿命", "float", "年", True, 60, None),
        ("保修_年", "保修", "float", "年", True, 30, None),
    ],
    "cat-13": [
        ("价格_low", "最低价", "float", "元", False, 75, None),
        ("价格_high", "最高价", "float", "元", False, 65, None),
        ("加热方式", "加热方式", "enum", "", True, 80, json.dumps(["即热式", "储热式"], ensure_ascii=False)),
        ("冲洗技术", "冲洗技术", "enum", "", True, 70, json.dumps(["超漩虹吸", "脉冲水流", "多模式冲洗", "卫洗丽"], ensure_ascii=False)),
        ("翻盖方式", "翻盖方式", "enum", "", True, 55, json.dumps(["自动感应", "脚感", "手动"], ensure_ascii=False)),
        ("座圈抗菌", "座圈抗菌", "bool", "", True, 45, None),
        ("无水压限制", "无水压限制", "bool", "", True, 65, None),
        ("保修_年", "保修", "float", "年", True, 40, None),
    ],
    "cat-14": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("类型", "热水器类型", "enum", "", True, 40, json.dumps(["燃气", "电储水", "空气能"], ensure_ascii=False)),
        ("恒温技术", "恒温技术", "enum", "", True, 85, json.dumps(["双控伺服", "水量伺服", "燃气比例阀"], ensure_ascii=False)),
        ("升数_L", "升数", "float", "L", True, 75, None),
        ("噪音_dB", "噪音", "float", "dB", False, 50, None),
        ("保修_年", "保修", "float", "年", True, 45, None),
    ],
    "cat-15": [
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("容量_kg", "容量", "float", "kg", True, 80, None),
        ("电机类型", "电机类型", "enum", "", True, 65, json.dumps(["DD直驱", "FPA直驱", "BLDC变频", "皮带定频"], ensure_ascii=False)),
        ("烘干方式", "烘干方式", "enum", "", True, 75, json.dumps(["双擎热泵", "热泵", "冷凝", "排气"], ensure_ascii=False)),
        ("洗净比", "洗净比", "float", "", True, 70, None),
        ("保修_年", "保修", "float", "年", True, 40, None),
    ],
    "cat-16": [
        ("价格_low", "最低价", "float", "元", False, 65, None),
        ("价格_high", "最高价", "float", "元", False, 55, None),
        ("尺寸_寸", "尺寸", "float", "英寸", True, 60, None),
        ("面板类型", "面板类型", "enum", "", True, 85, json.dumps(["QD-OLED", "OLED", "QD-MiniLED", "MiniLED", "ULED", "LCD"], ensure_ascii=False)),
        ("分区数", "分区数", "float", "", True, 75, None),
        ("刷新率_Hz", "刷新率", "float", "Hz", True, 50, None),
        ("色域_pct", "色域", "float", "% DCI-P3", True, 70, None),
        ("音响", "音响", "enum", "", True, 40, json.dumps(["帝瓦雷", "2.1声道杜比", "屏幕发声", "2.0声道"], ensure_ascii=False)),
        ("保修_年", "保修", "float", "年", True, 25, None),
    ],
    "cat-17": [
        # 集成灶相关维度
        ("价格_low", "最低价", "float", "元", False, 70, None),
        ("价格_high", "最高价", "float", "元", False, 60, None),
        ("类型", "集成灶类型", "enum", "", True, 40, json.dumps(["蒸烤一体", "消毒柜款", "储物柜款"], ensure_ascii=False)),
        ("风量_m3", "风量", "float", "m³/min", True, 80, None),
        ("静压_Pa", "最大静压", "float", "Pa", True, 75, None),
        ("热效率_pct", "热效率", "float", "%", True, 65, None),
        ("保修_年", "保修", "float", "年", True, 40, None),
    ],
}

# ============================================================
# 3. 数值/文本解析工具函数
# ============================================================

def parse_price(text):
    """解析价格文本，返回 (price_low, price_high)"""
    if not text:
        return (0, 0)
    text = text.strip().replace(",", "").replace("，", "").replace(" ", "")
    # 判断是否有"万"（万元单位）
    is_wan = "万" in text
    text_clean = text.replace("万", "").replace("元", "").replace("+", "")
    # "800-1,200" → (800, 1200)
    m = re.search(r"([\d.]+)\s*[-~]\s*([\d.]+)", text_clean)
    if m:
        low = float(m.group(1))
        high = float(m.group(2))
        if is_wan:
            low *= 10000
            high *= 10000
        return (low, high)
    # "~3,000" → (2800, 3200)
    m = re.search(r"~?\s*([\d.]+)", text_clean)
    if m:
        v = float(m.group(1))
        if is_wan:
            v *= 10000
        return (v * 0.9, v * 1.1)
    # "约5,000" → (4500, 5500)
    m = re.search(r"约\s*([\d.]+)", text_clean)
    if m:
        v = float(m.group(1))
        if is_wan:
            v *= 10000
        return (v * 0.9, v * 1.1)
    return (0, 0)


def extract_number(text):
    """从文本中提取数值（取中值或唯一值）"""
    if not text:
        return None
    text = text.strip()
    # 去掉带单位的常见文本
    text_clean = text.replace("m³/min", "").replace("m³/h", "").replace("Pa", "")
    text_clean = text_clean.replace("dB", "").replace("kW", "").replace("kW+", "")
    text_clean = text_clean.replace("L", "").replace("kg", "").replace("G", "")
    text_clean = text_clean.replace("mm", "").replace("°C", "").replace("℃", "")
    text_clean = text_clean.replace("℃", "").replace("Hz", "").replace("DCI-P3", "")
    text_clean = text_clean.replace("元", "").replace("%", "").replace("+", "")
    text_clean = text_clean.replace(",", "").replace("，", "").replace(" ", "")
    text_clean = text_clean.replace("万", "").replace("以上", "")
    # 去掉中文和其他非数字符号，但保留 . - ~ 和 >（去掉 : 但保留前面的数字）
    # 先尝试匹配 "数字:数字" 的比率格式 → 取第一个数字
    m_ratio = re.search(r"(\d+)\s*:\s*(\d+)", text_clean)
    if m_ratio:
        # 如果是范围 "2:1-3:1"
        m_range = re.search(r"(\d+)\s*:\s*\d+\s*[-~]\s*(\d+)\s*:\s*\d+", text_clean)
        if m_range:
            return (float(m_range.group(1)) + float(m_range.group(2))) / 2
        return float(m_ratio.group(1))
    # 去掉所有 : 符号
    text_clean = re.sub(r'[^\d.\-~≥>]+', '', text_clean)
    # 去除末尾多余的符号
    text_clean = text_clean.rstrip('.~->≥')
    if not text_clean:
        return None
    # 范围值: "22-30" → 中值 26
    m = re.search(r"([\d.]+)\s*[-~]\s*([\d.]+)", text_clean)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    # "≥1000" → 1000
    m = re.search(r"[≥>]\s*([\d.]+)", text_clean)
    if m:
        return float(m.group(1))
    # 纯数字
    m = re.search(r"^([\d.]+)$", text_clean)
    if m:
        return float(m.group(1))
    return None


def parse_stars(text):
    """解析星星评分 ⭐⭐⭐⭐⭐ → 5.0"""
    if not text:
        return 0
    count = text.count("⭐")
    if count > 0:
        return float(count)
    # "4.45分" 这种
    m = re.search(r"([\d.]+)", text)
    if m:
        return float(m.group(1))
    return 0


def parse_bool(text):
    """解析布尔值：✅ → True, ❌ → False, 其他文本判断"""
    if not text:
        return None
    if "✅" in text:
        return True
    if "❌" in text:
        return False
    t = text.strip()
    # 包含"有"且不包含"无/不"
    if re.search(r'(?:^|[\s,，、/])有(?:$|[\s,，、/]|[^无不])', t) or t.endswith("有"):
        return True
    if t in ("有", "是", "支持", "标配", "标配双系统"):
        return True
    if t in ("无", "否", "不支持", "部分有"):
        return False
    # "TR Pro有" → 匹配结尾有
    if t and t[-1] == "有":
        return True
    return None


def extract_enum_value(text):
    """提取枚举值，去掉多余描述"""
    if not text:
        return None
    text = text.strip()
    # "一级能效" → "一级"
    if "一级" in text:
        return "一级"
    if "二级" in text:
        return "二级"
    if "三级" in text:
        return "三级"
    # "H13 HEPA" 之类
    if "H13" in text or "HEPA" in text:
        return text
    return text


def parse_warranty(text):
    """解析保修年限"""
    if not text:
        return None
    text = text.strip()
    # "整机5年" → 5, "整机3年" → 3, "1-3年" → 3
    m = re.search(r"(\d+)\s*[-~]\s*(\d+)", text)
    if m:
        return float(m.group(2))
    m = re.search(r"(\d+)", text)
    if m:
        return float(m.group(1))
    return None


# ============================================================
# 4. 各品类行标签 → dim_key 映射
# ============================================================
# 每个品类独立定义，避免跨品类冲突
SLUG_LABEL_MAP = {
    "cat-1": {
        "风量": "风量_m3",
        "最大静压": "静压_Pa",
        "噪音": "噪音_dB",
        "能效": "能效等级",
        "保修": "保修_年",
        "线上份额": "线上份额_pct",
        "满意度": "满意度评分",
    },
    "cat-2": {
        "火力": "火力_kW",
        "热效率": "热效率_pct",
        "面板材质": "面板材质",
        "熄火保护": "熄火保护",
        "保修": "保修_年",
    },
    "cat-3": {
        "容量": "容量_L",
        "最高温度": "最高温度_C",
        "蒸功能": "蒸功能评分",
        "烤功能": "烤功能评分",
        "微波功能": "有微波",
        "保修": "保修_年",
    },
    "cat-4": {
        "类型": "类型",
        "容量": "容量_套",
        "烘干方式": "烘干方式",
        "噪音": "噪音_dB",
        "水效": "水效等级",
        "保修": "保修_年",
    },
    "cat-5": {
        "通量": "通量_G",
        "RO膜寿命": "RO膜寿命_年",
        "废水比": "废水比",
        "年均耗材": "年均耗材_元",
        "过滤级数": "过滤级数",
        "保修": "保修_年",
    },
    "cat-6": {
        "主流容量": "容量_L",
        "主流门型": "门型",
        "制冷方式": "制冷方式",
        "双系统": "双系统",
        "嵌入深度": "嵌入深度_mm",
        "保修": "保修_年",
    },
    "cat-7": {
        "容量": "容量_L",
        "消毒方式": "消毒方式",
        "杀菌率": "杀菌率_pct",
        "保修": "保修_年",
    },
    "cat-8": {
        "价格(全屋)": "价格_全屋_万",
        "3匹风管机": "风管机3匹_元",
        "压缩机": "压缩机",
        "能效(APF)": "能效_APF",
        "噪音": "噪音_dB",
        "保修": "保修_年",
    },
    "cat-9": {
        "风量(m³/h)": "风量_m3h",
        "过滤等级": "过滤等级",
        "热交换率": "热交换率_pct",
        "噪音": "噪音_dB",
        "安装方式": "安装方式",
        "保修": "保修_年",
    },
    "cat-10": {
        "能效(APF)": "能效_APF",
        "压缩机": "压缩机",
        "噪音(内机)": "噪音_dB",
        "自清洁": "自清洁",
        "保修": "保修_年",
    },
    "cat-11": {
        "吸力": "吸力_Pa",
        "拖地方式": "拖地方式",
        "避障技术": "避障技术",
        "基站功能": "基站功能",
        "保修": "保修_年",
    },
    "cat-12": {
        "颗粒物CADR": "颗粒物CADR",
        "甲醛CADR": "甲醛CADR",
        "噪音": "噪音_dB",
        "滤芯寿命": "滤芯寿命_年",
        "保修": "保修_年",
    },
    "cat-13": {
        "加热方式": "加热方式",
        "冲洗技术": "冲洗技术",
        "翻盖方式": "翻盖方式",
        "座圈抗菌": "座圈抗菌",
        "水压要求": "无水压限制",
        "保修": "保修_年",
    },
    "cat-14": {
        "恒温技术": "恒温技术",
        "升数": "升数_L",
        "噪音": "噪音_dB",
        "保修": "保修_年",
    },
    "cat-15": {
        "容量": "容量_kg",
        "电机类型": "电机类型",
        "烘干方式": "烘干方式",
        "洗净比": "洗净比",
        "保修": "保修_年",
    },
    "cat-16": {
        "面板类型": "面板类型",
        "分区数": "分区数",
        "刷新率": "刷新率_Hz",
        "色域": "色域_pct",
        "音响": "音响",
        "保修": "保修_年",
        "尺寸": "尺寸_寸",
    },
    "cat-17": {
        "排风量": "风量_m3",
        "热负荷": "热效率_pct",
        "保修": "保修_年",
    },
}


def get_dim_key_from_label(label_text, slug):
    """根据行标签文本和品类 slug 返回 dim_key"""
    label = label_text.strip()
    label_map = SLUG_LABEL_MAP.get(slug, {})
    # 精确匹配
    if label in label_map:
        return label_map[label]
    # 前缀匹配
    for pattern, dim_key in label_map.items():
        if label.startswith(pattern) or pattern.startswith(label):
            return dim_key
    return None


# ============================================================
# 5. 根据数据类型解析单元格值
# ============================================================

def get_dim_type(dim_key, slug):
    """查找维度的数据类型"""
    dims = DIMENSIONS.get(slug, [])
    for d in dims:
        if d[0] == dim_key:
            return d[2]  # type
    return "float"


def parse_cell_value(text, dim_type, dim_key):
    """根据维度类型解析单元格文本"""
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    if dim_type == "bool":
        val = parse_bool(text)
        return val
    
    if dim_type == "enum":
        return extract_enum_value(text)
    
    if dim_type == "float":
        # 保修特别处理
        if "保修" in dim_key or dim_key == "保修_年":
            return parse_warranty(text)
        # 满意度
        if "满意度" in dim_key or dim_key == "满意度评分":
            return parse_stars(text)
        # 线上份额
        if "份额" in dim_key or dim_key == "线上份额_pct":
            return extract_number(text.replace("~", ""))
        # 静压
        if "静压" in dim_key or dim_key == "静压_Pa":
            return extract_number(text)
        # 热效率/百分比
        if "热效率" in dim_key or dim_key == "热效率_pct":
            # "新国标一级(70%+)" → 70
            m = re.search(r"(\d+)\s*%", text)
            if m:
                return float(m.group(1))
            return extract_number(text)
        # 面板材质 - enum 但被识别为 float 时的兜底
        if dim_key == "面板材质":
            return extract_enum_value(text)
        # 熄火保护 - bool 但被识别为 float 时的兜底
        if dim_key == "熄火保护":
            val = parse_bool(text)
            return val
        # 一般数值
        n = extract_number(text)
        if n is not None:
            return n
        # 如果解析不出数值，尝试枚举或布尔兜底
        if "等级" in dim_key:
            return extract_enum_value(text)
        return None
    
    # text 类型
    return text


# ============================================================
# 6. 从 HTML 解析 dim-table
# ============================================================

def parse_dim_table(table, slug):
    """解析 dim-table，返回 {品牌: {dim_key: value}}"""
    if not table:
        return {}
    
    rows = table.find_all("tr")
    if len(rows) < 2:
        return {}
    
    # 第一行是表头：th 或 td
    header_cells = rows[0].find_all(["th", "td"])
    brands = []
    for cell in header_cells[1:]:  # 跳过第一列"维度"
        brand = cell.get_text(strip=True)
        if brand:
            brands.append(brand)
    
    if not brands:
        return {}
    
    result = {b: {} for b in brands}
    
    # 数据行
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label_cell = cells[0].get_text(strip=True)
        dim_key = get_dim_key_from_label(label_cell, slug)
        
        # 特殊处理价格行：存储为价格字段
        if label_cell == "价格区间":
            for i, brand in enumerate(brands):
                if i + 1 < len(cells):
                    val_text = cells[i + 1].get_text(strip=True)
                    price_low, price_high = parse_price(val_text)
                    if price_low:
                        result[brand]["价格_low"] = price_low
                    if price_high:
                        result[brand]["价格_high"] = price_high
            continue
        
        if dim_key is None:
            continue
        
        dim_type = get_dim_type(dim_key, slug)
        for i, brand in enumerate(brands):
            if i + 1 < len(cells):
                val_text = cells[i + 1].get_text(strip=True)
                if val_text:
                    result[brand][dim_key] = parse_cell_value(val_text, dim_type, dim_key)
    
    return result


# ============================================================
# 7. 从 HTML 解析"推荐型号与价格"表格
# ============================================================

def is_dim_table(table):
    """判断表格是否为 dim-table（多维度对比表）"""
    if table.get("class") and "dim-table" in table.get("class"):
        return True
    # 检查表头是否包含"维度"列
    first_row = table.find("tr")
    if first_row:
        cells = first_row.find_all(["th", "td"])
        if len(cells) >= 2:
            first_text = cells[0].get_text(strip=True)
            if first_text == "维度":
                return True
    return False


def find_all_recommend_tables(section):
    """查找品类 section 中所有非 dim-table 的品牌/型号表格"""
    cards = section.find_all("div", class_="card")
    tables = []
    for card in cards:
        header = card.find("div", class_="card-header")
        if not header:
            continue
        header_text = header.get_text(strip=True)
        # 跳过明显不是推荐表格的卡片
        if "品牌梯队" in header_text or "口碑" in header_text or "售后" in header_text or "维修" in header_text:
            continue
        table_wrap = card.find("div", class_="table-wrap")
        if not table_wrap:
            continue
        table = table_wrap.find("table")
        if not table:
            continue
        if is_dim_table(table):
            continue  # dim-table 由其他函数处理
        tables.append((header_text, table))
    return tables


def parse_recommend_table(table):
    """解析推荐/品牌表格，返回 [{品牌, 型号, 价格_low, 价格_high}]"""
    if not table:
        return []
    
    rows = table.find_all("tr")
    if len(rows) < 2:
        return []
    
    # 解析表头，找到各列索引
    header_cells = rows[0].find_all(["th", "td"])
    col_map = {}
    for idx, cell in enumerate(header_cells):
        text = cell.get_text(strip=True)
        if "品牌" in text and "品牌/型号" not in text:
            col_map["brand"] = idx
        if "型号" in text or "推荐型号" in text:
            col_map["model"] = idx
        if "价格" in text:
            col_map["price"] = idx
    
    # 没有品牌列的表头，但第一列可能是品牌名
    if "brand" not in col_map:
        # 尝试判断：如果第一列内容都是品牌名，则视为品牌列
        brands_from_rows = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if cells:
                txt = cells[0].get_text(strip=True)
                if txt and len(txt) <= 10 and not any(c.isdigit() for c in txt[:2]):
                    brands_from_rows.append(txt)
        if len(brands_from_rows) >= 3:
            col_map["brand"] = 0
    
    if "brand" not in col_map:
        return []
    
    products = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) <= col_map.get("brand", 0):
            continue
        
        brand = cells[col_map["brand"]].get_text(strip=True) if "brand" in col_map else ""
        if not brand:
            continue
        # 跳过表头或无效行
        if brand in ("品牌", "品牌/型号"):
            continue
        
        model = ""
        if "model" in col_map and col_map["model"] < len(cells):
            model = cells[col_map["model"]].get_text(strip=True)
        
        price_low = 0
        price_high = 0
        if "price" in col_map and col_map["price"] < len(cells):
            price_text = cells[col_map["price"]].get_text(strip=True)
            price_low, price_high = parse_price(price_text)
        
        products.append({
            "brand": brand,
            "model": model,
            "price_low": price_low,
            "price_high": price_high,
        })
    
    return products


# ============================================================
# 8. 主函数
# ============================================================

def main():
    html_path = Path(__file__).resolve().parent.parent / "index.html"
    if not html_path.exists():
        print(f"❌ 找不到 index.html: {html_path}")
        return
    
    print(f"📖 读取 {html_path} ...")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, "lxml")
    
    # 初始化数据库
    init_db()
    db = SessionLocal()
    
    try:
        # ---- 清理旧数据 ----
        print("🧹 清理旧数据...")
        db.query(Product).delete()
        db.query(Dimension).delete()
        db.query(Category).delete()
        db.commit()
        
        # ---- 创建品类 ----
        print("📁 创建品类...")
        cat_map = {}  # slug → DB Category object
        for slug, name, icon, sort_order in CATEGORIES:
            cat = Category(name=name, slug=slug, icon=icon, sort_order=sort_order)
            db.add(cat)
            db.flush()
            cat_map[slug] = cat
        
        db.commit()
        print(f"   ✅ 创建了 {len(cat_map)} 个品类/专题")
        
        # ---- 创建维度 ----
        print("📐 创建维度定义...")
        dim_count = 0
        for slug, dims in DIMENSIONS.items():
            cat = cat_map.get(slug)
            if not cat:
                continue
            for dim_tuple in dims:
                dim_key, label, dtype, unit, higher_better, weight, enum_vals = dim_tuple
                dim = Dimension(
                    category_id=cat.id,
                    dim_key=dim_key,
                    label=label,
                    type=dtype,
                    unit=unit,
                    higher_better=higher_better,
                    default_weight=weight,
                    enum_values=enum_vals or "",
                )
                db.add(dim)
                dim_count += 1
        
        db.commit()
        print(f"   ✅ 创建了 {dim_count} 个维度定义")
        
        # ---- 从 HTML 解析产品数据 ----
        print("🔍 解析 HTML 产品数据...")
        total_products = 0
        product_brands = {}  # slug → set of brands
        
        for slug, _, _, _ in CATEGORIES:
            if slug.startswith("topic-"):
                continue  # 专题不解析产品
            
            section = soup.find("div", id=slug)
            if not section:
                print(f"   ⚠️ 未找到 section: {slug}")
                continue
            
            cat = cat_map[slug]
            brands_seen = set()
            product_brands[slug] = set()
            
            # 8a) 解析 dim-table
            dim_tables = section.find_all("table", class_="dim-table")
            if dim_tables:
                dim_data = parse_dim_table(dim_tables[0], slug)
                for brand, dims in dim_data.items():
                    if brand in brands_seen:
                        continue
                    brands_seen.add(brand)
                    
                    # 提取价格
                    price_low = dims.pop("价格_low", 0) or 0
                    price_high = dims.pop("价格_high", 0) or 0
                    
                    # 清理仅用于展示的非维度字段
                    dims.pop("核心技术", None)
                    dims.pop("核心特点", None)
                    
                    # 对 enum 字段，保留原始文本
                    product_dimensions = {}
                    for k, v in dims.items():
                        if v is not None:
                            product_dimensions[k] = v
                    
                    product = Product(
                        category_id=cat.id,
                        brand=brand,
                        model="",
                        price_low=float(price_low),
                        price_high=float(price_high),
                        dimensions=product_dimensions,
                        rating=product_dimensions.get("满意度评分", 0) or 0,
                    )
                    db.add(product)
                    total_products += 1
                    product_brands[slug].add(brand)
            
            # 8b) 解析所有推荐/商品表格
            rec_tables = find_all_recommend_tables(section)
            for header_text, rec_table in rec_tables:
                rec_products = parse_recommend_table(rec_table)
                for rp in rec_products:
                    brand = rp["brand"]
                    # 如果品牌已经在 dim-table 中出现过但型号不同，仍然写入
                    product = Product(
                        category_id=cat.id,
                        brand=brand,
                        model=rp["model"],
                        price_low=float(rp["price_low"]),
                        price_high=float(rp["price_high"]),
                        dimensions={},
                        rating=0,
                    )
                    db.add(product)
                    total_products += 1
                    product_brands[slug].add(brand)
        
        db.commit()
        
        # ---- 统计 ----
        print(f"\n📊 === 统计信息 ===")
        print(f"   品类数: {len([s for s, _, _, _ in CATEGORIES if not s.startswith('topic-')])}")
        print(f"   专题数: {len([s for s, _, _, _ in CATEGORIES if s.startswith('topic-')])}")
        print(f"   维度定义数: {dim_count}")
        print(f"   总产品数: {total_products}")
        
        for slug, _, name, _ in CATEGORIES:
            if slug.startswith("topic-"):
                continue
            brands = product_brands.get(slug, set())
            print(f"   {name} ({slug}): {len(brands)} 品牌, 产品已写入")
        
        print(f"\n✅ 种子数据导入完成！")
    
    except Exception as e:
        db.rollback()
        print(f"❌ 出错: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
