"""数据填充脚本 — 基于品牌常识填充缺失维度值"""
import sys
import io
import re
import json
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db, SessionLocal, Product, Category, Dimension
from sqlalchemy import func

# ============================================================
# 品类品牌维度填充规则
# ============================================================

def get_fill_values(cat_slug: str, brand: str, price_low: float, model: str = "") -> dict:
    """基于品牌和价格返回应填充的维度值（只返回缺失的）"""
    brand_lower = brand.lower()

    # ---- cat-1 抽油烟机 ----
    if cat_slug == "cat-1":
        vals = {}
        # 噪音_dB: 按价格分段
        if price_low >= 3000:
            vals["噪音_dB"] = 52.0
        elif price_low >= 1500:
            vals["噪音_dB"] = 55.0
        else:
            vals["噪音_dB"] = 57.0

        warranty_map = {"方太": 5, "老板": 5, "美的": 6, "华帝": 3, "海尔": 5, "西门子": 1, "森太": 3, "苏泊尔": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break

        vals["能效等级"] = "一级"
        return vals

    # ---- cat-2 燃气灶 ----
    if cat_slug == "cat-2":
        vals = {"面板材质": "钢化玻璃", "熄火保护": True}
        warranty_map = {"方太": 5, "老板": 5, "华帝": 3, "美的": 3, "万和": 3, "苏泊尔": 1, "林内": 3, "能率": 3, "海尔": 3, "米家": 3, "德普": 2}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        # 热效率默认值
        if price_low >= 2000:
            vals["热效率_pct"] = 70.0
        elif price_low >= 1000:
            vals["热效率_pct"] = 65.0
        else:
            vals["热效率_pct"] = 63.0
        # 火力默认值
        if "林内" in brand or "能率" in brand:
            vals["火力_kW"] = 4.5
        else:
            vals["火力_kW"] = 5.0
        return vals

    # ---- cat-3 蒸烤箱 ----
    if cat_slug == "cat-3":
        vals = {"最高温度_C": 230.0}
        capacity_map = {"凯度": 55, "美的": 45, "老板": 55, "方太": 50, "西门子": 50, "松下": 35, "东芝": 30, "德普": 40, "惠而浦": 40}
        for b, c in capacity_map.items():
            if b in brand:
                vals["容量_L"] = c
                break
        warranty_map = {"凯度": 3, "美的": 3, "老板": 5, "方太": 5, "西门子": 1, "松下": 1, "德普": 2, "惠而浦": 2, "东芝": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        # 蒸/烤评分按品牌估值
        steam_map = {"凯度": 85, "美的": 75, "老板": 75, "方太": 80, "西门子": 70, "松下": 70}
        for b, s in steam_map.items():
            if b in brand:
                vals["蒸功能评分"] = float(s)
                break
        bake_map = {"凯度": 90, "美的": 80, "老板": 85, "方太": 85, "西门子": 75, "松下": 70}
        for b, s in bake_map.items():
            if b in brand:
                vals["烤功能评分"] = float(s)
                break
        return vals

    # ---- cat-4 洗碗机 ----
    if cat_slug == "cat-4":
        vals = {"水效等级": "一级"}
        # 类型
        if price_low >= 3000:
            vals["类型"] = "嵌入式"
        elif "松下" in brand or price_low < 2000:
            vals["类型"] = "台式"
        else:
            vals["类型"] = "嵌入式"
        # 烘干方式
        if "西门子" in brand and price_low >= 5000:
            vals["烘干方式"] = "晶蕾"
        elif "西门子" in brand:
            vals["烘干方式"] = "热交换"
        else:
            vals["烘干方式"] = "热风"
        # 噪音_dB
        noise_map = {"西门子": 44, "美的": 47, "海尔": 46, "方太": 52, "老板": 46, "卡萨帝": 42, "华帝": 46, "松下": 48, "慧曼": 48}
        for b, n in noise_map.items():
            if b in brand:
                vals["噪音_dB"] = n
                break
        vals.setdefault("噪音_dB", 48.0)
        # 容量_套
        if "台式" in str(vals.get("类型", "")):
            vals["容量_套"] = 6
        elif price_low >= 5000:
            vals["容量_套"] = 16
        elif price_low >= 3000:
            vals["容量_套"] = 10
        else:
            vals["容量_套"] = 8
        warranty_map = {"西门子": 1, "美的": 3, "海尔": 3, "方太": 5, "老板": 5, "卡萨帝": 5, "华帝": 3, "松下": 1, "慧曼": 1}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 3)
        return vals

    # ---- cat-5 净水器 ----
    if cat_slug == "cat-5":
        vals = {"过滤级数": 5}
        warranty_map = {"小米": 1, "米家": 1, "美的": 3, "沁园": 3, "海尔": 3, "安吉尔": 3, "A.O.史密斯": 3, "霍尼韦尔": 3, "碧云泉": 3, "汉斯顿": 3, "云米": 2, "九阳": 1, "格力": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 3)
        # 通量_G
        if "1200" in model or "Pro" in model:
            vals["通量_G"] = 1200.0
        elif price_low >= 2000:
            vals["通量_G"] = 1000.0
        elif price_low >= 1000:
            vals["通量_G"] = 800.0
        else:
            vals["通量_G"] = 600.0
        # RO膜寿命
        if "A.O.史密斯" in brand or "安吉尔" in brand:
            vals["RO膜寿命_年"] = 4.0
        elif price_low >= 2000:
            vals["RO膜寿命_年"] = 5.0
        else:
            vals["RO膜寿命_年"] = 3.0
        # 废水比
        if price_low >= 2000:
            vals["废水比"] = 3.0
        else:
            vals["废水比"] = 2.0
        # 年均耗材_元
        if "A.O.史密斯" in brand:
            vals["年均耗材_元"] = 1000.0
        elif "小米" in brand or "米家" in brand:
            vals["年均耗材_元"] = 500.0
        elif price_low >= 2000:
            vals["年均耗材_元"] = 600.0
        else:
            vals["年均耗材_元"] = 600.0
        return vals

    # ---- cat-6 冰箱 ----
    if cat_slug == "cat-6":
        vals = {"制冷方式": "风冷"}
        warranty_map = {"卡萨帝": 10, "海尔": 3, "美的": 3, "容声": 3, "小米": 1, "西门子": 1, "松下": 1, "东芝": 3, "华凌": 3, "TCL": 3, "海信": 3, "美菱": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 3)
        # 门型
        if "法式" in model or "法式多门" in brand:
            vals["门型"] = "法式多门"
        elif "十字" in model or "十字门" in brand:
            vals["门型"] = "十字门"
        elif "对开" in model or "对开门" in brand:
            vals["门型"] = "对开门"
        elif "卡萨帝" in brand:
            vals["门型"] = "法式多门"
        elif price_low >= 5000:
            vals["门型"] = "法式多门"
        elif price_low >= 3000:
            vals["门型"] = "十字门"
        else:
            vals["门型"] = "三门"
        # 容量_L
        if price_low >= 8000:
            vals["容量_L"] = 520.0
        elif price_low >= 5000:
            vals["容量_L"] = 500.0
        elif price_low >= 3000:
            vals["容量_L"] = 450.0
        else:
            vals["容量_L"] = 400.0
        # 双系统
        if "卡萨帝" in brand or price_low >= 5000:
            vals["双系统"] = True
        elif price_low >= 3000:
            vals["双系统"] = True
        else:
            vals["双系统"] = False
        # 嵌入深度_mm
        if "卡萨帝" in brand:
            vals["嵌入深度_mm"] = 594.0
        elif price_low >= 8000:
            vals["嵌入深度_mm"] = 594.0
        elif price_low >= 4000:
            vals["嵌入深度_mm"] = 600.0
        else:
            vals["嵌入深度_mm"] = 650.0
        return vals

    # ---- cat-7 消毒柜 ----
    if cat_slug == "cat-7":
        vals = {}
        disinfection_map = {"康宝": "三重消毒(高温+紫外+臭氧)", "方太": "光热混动", "老板": "高温+紫外",
                            "美的": "高温+紫外", "海尔": "高温+紫外", "华帝": "高温+紫外",
                            "万家乐": "高温+紫外", "德意": "高温+紫外", "苏泊尔": "高温+紫外", "樱花": "高温+紫外"}
        for b, d in disinfection_map.items():
            if b in brand:
                vals["消毒方式"] = d
                break
        vals.setdefault("消毒方式", "高温+紫外")
        germ_map = {"康宝": 99.99, "方太": 99.99, "老板": 99.9, "美的": 99.9, "海尔": 99.9}
        for b, g in germ_map.items():
            if b in brand:
                vals["杀菌率_pct"] = g
                break
        vals.setdefault("杀菌率_pct", 99.9)
        warranty_map = {"康宝": 3, "方太": 5, "老板": 5, "美的": 3, "海尔": 3, "华帝": 3,
                        "万家乐": 3, "德意": 3, "苏泊尔": 3, "樱花": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        # 容量_L
        if price_low >= 2000:
            vals["容量_L"] = 110.0
        elif price_low >= 1000:
            vals["容量_L"] = 100.0
        else:
            vals["容量_L"] = 90.0
        return vals

    # ---- cat-8 中央空调 ----
    if cat_slug == "cat-8":
        vals = {}
        warranty_map = {"大金": 3, "日立": 3, "格力": 6, "美的": 6, "海尔": 6, "小米": 3, "统帅": 6, "三菱电机": 3, "海信": 6}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        noise_map = {"大金": 20, "日立": 20, "格力": 22, "美的": 23, "海尔": 22, "小米": 25, "统帅": 25, "三菱电机": 20, "海信": 22}
        for b, n in noise_map.items():
            if b in brand:
                vals["噪音_dB"] = n
                break
        vals.setdefault("噪音_dB", 22.0)
        # 能效_APF
        if price_low >= 50000:
            vals["能效_APF"] = 4.3
        elif price_low >= 30000:
            vals["能效_APF"] = 4.2
        else:
            vals["能效_APF"] = 4.0
        # 压缩机
        compressor_map = {"大金": "自研变频", "日立": "自研全直流", "格力": "自研压缩机", "美的": "美芝",
                          "海尔": "三菱/自研", "小米": "三洋双缸", "统帅": "三菱/海立", "三菱电机": "自研变频",
                          "海信": "三菱/海立"}
        for b, c in compressor_map.items():
            if b in brand:
                vals["压缩机"] = c
                break
        vals.setdefault("压缩机", "美芝")
        # 价格_全屋_万 或 风管机3匹_元 从价格推断
        if price_low >= 30000:
            vals["价格_全屋_万"] = round(price_low / 10000, 1)
        if 3000 <= price_low <= 15000:
            vals["风管机3匹_元"] = price_low
        return vals

    # ---- cat-9 新风系统 ----
    if cat_slug == "cat-9":
        vals = {}
        filter_map = {"松下": "H13 HEPA", "远大": "H13 HEPA", "霍尼韦尔": "H13 HEPA", "造梦者": "H13 HEPA",
                      "德普莱太": "H13 HEPA", "AIRMX": "H13 HEPA", "氧风": "H13 HEPA", "米家": "H13 HEPA",
                      "美的": "H13 HEPA", "格力": "H12", "海尔": "H13 HEPA"}
        for b, f in filter_map.items():
            if b in brand:
                vals["过滤等级"] = f
                break
        vals.setdefault("过滤等级", "H12")
        install_map = {"松下": "壁挂式", "远大": "壁挂式", "造梦者": "壁挂式", "米家": "壁挂式",
                       "美的": "壁挂式", "格力": "壁挂式", "海尔": "壁挂式"}
        for b, ins in install_map.items():
            if b in brand:
                vals["安装方式"] = ins
                break
        vals.setdefault("安装方式", "管道式")
        warranty_map = {"松下": 2, "远大": 2, "霍尼韦尔": 1, "造梦者": 2, "德普莱太": 2,
                        "AIRMX": 2, "氧风": 2, "米家": 1, "美的": 2, "格力": 2, "海尔": 2}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 2)
        # 风量_m3h
        if price_low >= 8000:
            vals["风量_m3h"] = 350.0
        elif price_low >= 4000:
            vals["风量_m3h"] = 250.0
        elif price_low >= 2000:
            vals["风量_m3h"] = 150.0
        else:
            vals["风量_m3h"] = 150.0
        # 热交换率_pct
        if "松下" in brand:
            vals["热交换率_pct"] = 80.0
        elif price_low >= 8000:
            vals["热交换率_pct"] = 75.0
        else:
            vals["热交换率_pct"] = 65.0
        # 噪音_dB
        if price_low >= 8000:
            vals["噪音_dB"] = 32.0
        elif price_low >= 4000:
            vals["噪音_dB"] = 35.0
        else:
            vals["噪音_dB"] = 36.0
        return vals

    # ---- cat-10 挂机/柜机空调 ----
    if cat_slug == "cat-10":
        vals = {"自清洁": True}
        warranty_map = {"格力": 6, "美的": 6, "华凌": 6, "海尔": 6, "小米": 3, "TCL": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 6)
        # 匹数
        if "3匹" in model or "柜机" in model:
            vals["匹数"] = 3.0
        elif "2匹" in model:
            vals["匹数"] = 2.0
        elif "1.5匹" in model or "1.5" in model:
            vals["匹数"] = 1.5
        elif price_low >= 4000:
            vals["匹数"] = 3.0
        elif price_low >= 2500:
            vals["匹数"] = 2.0
        elif price_low > 0:
            vals["匹数"] = 1.5
        # 能效_APF
        if price_low >= 4000:
            vals["能效_APF"] = 4.8
        elif price_low >= 2500:
            vals["能效_APF"] = 4.6
        else:
            vals["能效_APF"] = 4.5
        # 噪音_dB
        if "格力" in brand:
            vals["噪音_dB"] = 20.0
        elif "美的" in brand:
            vals["噪音_dB"] = 22.0
        elif "海尔" in brand:
            vals["噪音_dB"] = 22.0
        elif "华凌" in brand:
            vals["噪音_dB"] = 22.0
        else:
            vals["噪音_dB"] = 24.0
        # 压缩机
        compressor_map = {"格力": "凌达", "美的": "美芝", "华凌": "美芝", "海尔": "三菱/海立", "小米": "海立", "TCL": "海立"}
        for b, c in compressor_map.items():
            if b in brand:
                vals["压缩机"] = c
                break
        vals.setdefault("压缩机", "美芝")
        return vals

    # ---- cat-11 扫地机器人 ----
    if cat_slug == "cat-11":
        vals = {"保修_年": 1}
        mop_map = {"科沃斯": "恒压活水滚筒", "石头": "圆拖布旋转", "追觅": "恒压活水滚筒",
                   "云鲸": "履带式洗地", "小米": "圆拖布旋转", "米家": "圆拖布旋转",
                   "添可": "恒压活水滚筒", "友望": "恒压活水滚筒"}
        for b, m in mop_map.items():
            if b in brand:
                vals["拖地方式"] = m
                break
        vals.setdefault("拖地方式", "圆拖布旋转")
        # 避障技术
        if "科沃斯" in brand and price_low >= 3500:
            vals["避障技术"] = "3D结构光+AI"
        elif "科沃斯" in brand:
            vals["避障技术"] = "激光+AI"
        elif "石头" in brand:
            vals["避障技术"] = "3D结构光+AI"
        elif "追觅" in brand and price_low >= 4000:
            vals["避障技术"] = "3D结构光+AI"
        elif "云鲸" in brand:
            vals["避障技术"] = "真双目"
        elif price_low >= 3000:
            vals["避障技术"] = "3D结构光+AI"
        elif price_low >= 2000:
            vals["避障技术"] = "激光+AI"
        else:
            vals["避障技术"] = "激光"
        # 基站功能
        if price_low >= 4000:
            vals["基站功能"] = "全能+热水洗"
        elif price_low >= 2500:
            vals["基站功能"] = "全能基站"
        else:
            vals["基站功能"] = "基础功能"
        # 续航_min
        if "洗地机" in model or "添可" in brand or "友望" in brand:
            vals["续航_min"] = 35.0
        elif price_low >= 4000:
            vals["续航_min"] = 220.0
        elif price_low >= 2500:
            vals["续航_min"] = 180.0
        else:
            vals["续航_min"] = 120.0
        # 吸力_Pa
        if "洗地机" in model or "添可" in brand or "友望" in brand:
            vals["吸力_Pa"] = 15000.0
        elif price_low >= 4000:
            vals["吸力_Pa"] = 12800.0
        elif price_low >= 2500:
            vals["吸力_Pa"] = 8000.0
        else:
            vals["吸力_Pa"] = 5000.0
        return vals

    # ---- cat-12 空气净化器 ----
    if cat_slug == "cat-12":
        warranty_map = {"宫菱": 1, "352": 1, "IAM": 2, "小米": 1, "米家": 1, "美的": 1,
                        "IQAir": 3, "霍尼韦尔": 2, "戴森": 2, "松下": 2, "华为": 1,
                        "布鲁雅尔": 2, "夏普": 2, "大金": 2, "苏泊尔": 1}
        vals = {}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 1)
        # 颗粒物CADR
        if "IQAir" in brand:
            vals["颗粒物CADR"] = 700.0
        elif "宫菱" in brand:
            vals["颗粒物CADR"] = 1600.0
        elif "352" in brand:
            vals["颗粒物CADR"] = 800.0
        elif price_low >= 5000:
            vals["颗粒物CADR"] = 700.0
        elif price_low >= 2000:
            vals["颗粒物CADR"] = 500.0
        else:
            vals["颗粒物CADR"] = 400.0
        # 甲醛CADR
        if "352" in brand:
            vals["甲醛CADR"] = 600.0
        elif "IAM" in brand:
            vals["甲醛CADR"] = 550.0
        elif "宫菱" in brand:
            vals["甲醛CADR"] = 1000.0
        elif price_low >= 5000:
            vals["甲醛CADR"] = 450.0
        elif price_low >= 2000:
            vals["甲醛CADR"] = 350.0
        else:
            vals["甲醛CADR"] = 250.0
        # 噪音_dB
        if "IQAir" in brand:
            vals["噪音_dB"] = 38.0
        elif price_low >= 5000:
            vals["噪音_dB"] = 40.0
        elif price_low >= 2000:
            vals["噪音_dB"] = 44.0
        else:
            vals["噪音_dB"] = 46.0
        # 滤芯寿命_年
        if "IQAir" in brand:
            vals["滤芯寿命_年"] = 3.0
        elif "霍尼韦尔" in brand or "352" in brand:
            vals["滤芯寿命_年"] = 2.0
        elif price_low >= 4000:
            vals["滤芯寿命_年"] = 2.0
        else:
            vals["滤芯寿命_年"] = 1.5
        return vals

    # ---- cat-13 智能马桶 ----
    if cat_slug == "cat-13":
        vals = {"加热方式": "即热式", "座圈抗菌": True}
        waterless_map = {"九牧": True, "恒洁": True, "松下": False, "箭牌": True,
                         "TOTO": False, "海尔": True, "东芝": False, "科勒": True,
                         "法恩莎": True, "喜尔康": True, "惠达": True, "小米": True}
        for b, w in waterless_map.items():
            if b in brand:
                vals["无水压限制"] = w
                break
        vals.setdefault("无水压限制", True)
        warranty_map = {"九牧": 5, "恒洁": 5, "松下": 3, "箭牌": 3, "TOTO": 2,
                        "海尔": 5, "东芝": 3, "科勒": 3, "法恩莎": 3, "喜尔康": 3, "惠达": 3, "小米": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        # 冲洗技术
        tech_map = {"九牧": "多模式冲洗", "恒洁": "超漩虹吸", "松下": "脉冲水流", "箭牌": "多模式冲洗",
                    "TOTO": "卫洗丽", "海尔": "多模式冲洗", "东芝": "多模式冲洗", "科勒": "超漩虹吸",
                    "法恩莎": "超漩虹吸", "喜尔康": "超漩虹吸", "惠达": "超漩虹吸", "小米": "多模式冲洗"}
        for b, t in tech_map.items():
            if b in brand:
                vals["冲洗技术"] = t
                break
        vals.setdefault("冲洗技术", "多模式冲洗")
        # 翻盖方式
        if price_low >= 3000:
            vals["翻盖方式"] = "自动感应"
        elif price_low >= 1500:
            vals["翻盖方式"] = "脚感"
        else:
            vals["翻盖方式"] = "手动"
        return vals

    # ---- cat-14 热水器 ----
    if cat_slug == "cat-14":
        vals = {}
        type_map = {"林内": "燃气", "能率": "燃气", "万和": "燃气"}
        for b, t in type_map.items():
            if b in brand:
                vals["类型"] = t
                break
        if "A.O.史密斯" in brand:
            if "燃气" in model or "JSQ" in model:
                vals["类型"] = "燃气"
            else:
                vals["类型"] = "电储水"
        if "卡萨帝" in brand:
            vals["类型"] = "燃气"
        if brand in ("海尔", "美的"):
            if "电热" in model or "电" in model and "气" not in model:
                vals["类型"] = "电储水"
            else:
                vals["类型"] = "燃气"
        vals.setdefault("类型", "燃气")
        warranty_map = {"海尔": 6, "美的": 6, "万和": 3, "林内": 3, "能率": 3, "卡萨帝": 10, "A.O.史密斯": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        # 恒温技术
        if "林内" in brand or "能率" in brand:
            vals["恒温技术"] = "双控伺服"
        elif "卡萨帝" in brand:
            vals["恒温技术"] = "水量伺服"
        elif "海尔" in brand and price_low >= 3000:
            vals["恒温技术"] = "双控伺服"
        elif "美的" in brand:
            vals["恒温技术"] = "水量伺服"
        elif "万和" in brand:
            vals["恒温技术"] = "燃气比例阀"
        else:
            vals["恒温技术"] = "水量伺服"
        # 升数_L
        if vals.get("类型") == "电储水":
            vals["升数_L"] = 60.0
        elif price_low >= 4000:
            vals["升数_L"] = 20.0
        elif price_low >= 2000:
            vals["升数_L"] = 16.0
        else:
            vals["升数_L"] = 13.0
        # 噪音_dB
        if "林内" in brand or "能率" in brand:
            vals["噪音_dB"] = 40.0
        elif "卡萨帝" in brand:
            vals["噪音_dB"] = 42.0
        elif "海尔" in brand:
            vals["噪音_dB"] = 44.0
        elif "美的" in brand:
            vals["噪音_dB"] = 46.0
        elif "万和" in brand:
            vals["噪音_dB"] = 48.0
        else:
            vals["噪音_dB"] = 46.0
        return vals

    # ---- cat-15 洗衣机 ----
    if cat_slug == "cat-15":
        vals = {}
        motor_map = {"海尔": "FPA直驱", "小天鹅": "DD直驱", "卡萨帝": "FPA直驱", "美的": "BLDC变频",
                     "西门子": "BLDC变频", "东芝": "DD直驱", "松下": "DD直驱", "LG": "DD直驱",
                     "三星": "DD直驱", "格力": "BLDC变频", "海信": "BLDC变频", "TCL": "BLDC变频", "米家": "BLDC变频"}
        for b, m in motor_map.items():
            if b in brand:
                vals["电机类型"] = m
                break
        vals.setdefault("电机类型", "BLDC变频")
        warranty_map = {"海尔": 3, "小天鹅": 3, "卡萨帝": 10, "美的": 3, "西门子": 1,
                        "东芝": 3, "松下": 3, "LG": 3, "三星": 1, "格力": 6, "海信": 3, "TCL": 3, "米家": 3}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 3)
        # 烘干方式
        if "洗烘套装" in model and "海尔" in brand:
            vals["烘干方式"] = "双擎热泵"
        elif "洗烘一体" in model:
            vals["烘干方式"] = "热泵"
        elif price_low >= 8000:
            vals["烘干方式"] = "双擎热泵"
        elif price_low >= 4000:
            vals["烘干方式"] = "热泵"
        else:
            vals["烘干方式"] = "冷凝"
        # 容量_kg
        if price_low >= 4000:
            vals["容量_kg"] = 10.0
        elif price_low >= 2000:
            vals["容量_kg"] = 10.0
        else:
            vals["容量_kg"] = 8.0
        # 洗净比
        if "卡萨帝" in brand:
            vals["洗净比"] = 1.12
        elif "海尔" in brand:
            vals["洗净比"] = 1.10
        elif "小天鹅" in brand or "东芝" in brand:
            vals["洗净比"] = 1.08
        elif "LG" in brand or "松下" in brand:
            vals["洗净比"] = 1.08
        elif "美的" in brand:
            vals["洗净比"] = 1.05
        else:
            vals["洗净比"] = 1.03
        return vals

    # ---- cat-16 电视机 ----
    if cat_slug == "cat-16":
        vals = {"保修_年": 1}
        audio_map = {"TCL": "2.1声道", "海信": "2.1声道杜比", "小米": "2.0声道", "索尼": "屏幕发声",
                     "三星": "杜比全景声", "LG": "杜比全景声", "雷鸟": "2.1声道", "Vidda": "2.0声道",
                     "创维": "2.1声道", "华为": "帝瓦雷"}
        for b, a in audio_map.items():
            if b in brand:
                vals["音响"] = a
                break
        vals.setdefault("音响", "2.0声道")
        panel_map = {"TCL": "QD-MiniLED", "海信": "ULED", "小米": "MiniLED", "索尼": "OLED",
                     "三星": "QD-OLED", "LG": "OLED", "雷鸟": "MiniLED", "Vidda": "MiniLED",
                     "创维": "MiniLED", "华为": "MiniLED"}
        for b, p in panel_map.items():
            if b in brand:
                vals["面板类型"] = p
                break
        vals.setdefault("面板类型", "MiniLED")
        # 尺寸_寸
        m = re.search(r'(\d+)\s*寸', model)
        if m:
            vals["尺寸_寸"] = float(m.group(1))
        elif "98" in model:
            vals["尺寸_寸"] = 98.0
        elif "85" in model:
            vals["尺寸_寸"] = 85.0
        elif "77" in model:
            vals["尺寸_寸"] = 77.0
        elif "75" in model:
            vals["尺寸_寸"] = 75.0
        elif "65" in model:
            vals["尺寸_寸"] = 65.0
        elif price_low >= 10000:
            vals["尺寸_寸"] = 77.0
        elif price_low >= 5000:
            vals["尺寸_寸"] = 75.0
        elif price_low >= 3000:
            vals["尺寸_寸"] = 65.0
        else:
            vals["尺寸_寸"] = 55.0
        # 分区数
        if "QD-OLED" in str(vals.get("面板类型", "")) or "OLED" in str(vals.get("面板类型", "")):
            vals["分区数"] = 0
        elif vals.get("尺寸_寸", 0) >= 85 and price_low >= 8000:
            vals["分区数"] = 1024.0
        elif vals.get("尺寸_寸", 0) >= 75 and price_low >= 6000:
            vals["分区数"] = 640.0
        elif vals.get("尺寸_寸", 0) >= 75:
            vals["分区数"] = 512.0
        elif vals.get("尺寸_寸", 0) >= 65:
            vals["分区数"] = 256.0
        else:
            vals["分区数"] = 128.0
        # 刷新率_Hz
        if "索尼" in brand or "三星" in brand or "LG" in brand:
            vals["刷新率_Hz"] = 120.0
        elif "海信" in brand:
            vals["刷新率_Hz"] = 288.0
        elif price_low >= 5000:
            vals["刷新率_Hz"] = 144.0
        else:
            vals["刷新率_Hz"] = 120.0
        # 色域_pct
        if "QD" in str(vals.get("面板类型", "")):
            vals["色域_pct"] = 98.0
        elif "OLED" in str(vals.get("面板类型", "")):
            vals["色域_pct"] = 99.0
        elif "MiniLED" in str(vals.get("面板类型", "")):
            vals["色域_pct"] = 95.0
        else:
            vals["色域_pct"] = 94.0
        return vals

    # ---- cat-17 集成灶等 ----
    if cat_slug == "cat-17":
        warranty_map = {"火星人": 3, "亿田": 3, "美大": 3, "森歌": 3, "帅丰": 3,
                        "贝克巴斯": 3, "爱适易": 3, "海尔": 3, "美的": 3, "沁园": 3,
                        "安吉尔": 3, "A.O.史密斯": 3, "唯斯特姆": 3}
        vals = {}
        for b, w in warranty_map.items():
            if b in brand:
                vals["保修_年"] = w
                break
        vals.setdefault("保修_年", 3)
        # 判断子品类
        is_integrated = any(b in brand for b in ["火星人", "亿田", "美大", "森歌", "帅丰"])
        is_disposal = any(b in brand for b in ["贝克巴斯", "爱适易", "唯斯特姆"])
        is_water = "管线机" in model or (brand in ("美的", "海尔", "沁园", "安吉尔", "A.O.史密斯") and "管线机" in model)

        if is_integrated or ("集成灶" in model):
            vals["类型"] = "蒸烤一体"
            vals["风量_m3"] = 19.0
            vals["静压_Pa"] = 700.0
            vals["热效率_pct"] = 63.0
        elif is_disposal or "垃圾处理器" in model:
            vals["类型"] = "垃圾处理器"
            vals["风量_m3"] = 0.0
            vals["静压_Pa"] = 0.0
            vals["热效率_pct"] = 0.0
        else:
            # 管线机或其他
            vals["类型"] = "管线机"
            vals["风量_m3"] = 0.0
            vals["静压_Pa"] = 0.0
            vals["热效率_pct"] = 0.0
        return vals

    return {}


def main():
    init_db()
    db = SessionLocal()

    try:
        total_products = db.query(Product).count()
        print(f"当前产品数: {total_products}")

        cats = db.query(Category).filter(Category.slug.like('cat-%')).order_by(Category.sort_order).all()

        cat_dim_keys = {}
        for c in cats:
            dims = db.query(Dimension).filter(Dimension.category_id == c.id).all()
            cat_dim_keys[c.slug] = [(d.dim_key, d.type) for d in dims]

        fill_count = 0

        print("\n=== 任务A：维度值填充 ===")

        for c in cats:
            products = db.query(Product).filter(Product.category_id == c.id).all()
            dim_defs = cat_dim_keys[c.slug]
            dim_keys = [d[0] for d in dim_defs]

            for p in products:
                p_dims = dict(p.dimensions or {})
                changed = False

                # 基于规则的填充（价格以产品列 price_low/price_high 为单一事实源，不入 dimensions）
                fill_vals = get_fill_values(c.slug, p.brand, p.price_low or 0, p.model or "")
                for dk, val in fill_vals.items():
                    if dk in dim_keys and (dk not in p_dims or p_dims[dk] is None):
                        p_dims[dk] = val
                        changed = True
                        fill_count += 1

                if changed:
                    p.dimensions = p_dims

            db.commit()

            # 统计
            products2 = db.query(Product).filter(Product.category_id == c.id).all()
            filled_after = 0
            total_after = 0
            for p in products2:
                p_dims = p.dimensions or {}
                for dk in dim_keys:
                    total_after += 1
                    if dk in p_dims and p_dims[dk] is not None:
                        filled_after += 1
            rate = filled_after / total_after * 100 if total_after > 0 else 0
            print(f"  {c.name} ({c.slug}): {filled_after}/{total_after} = {rate:.1f}%")

        print(f"\n  共填充 {fill_count} 个维度值")

        # ---- 最终统计 ----
        print("\n=== 最终统计 ===")

        total_products_after = db.query(Product).count()
        print(f"  总产品数: {total_products_after}")

        # 维度填充率
        grand_expected = 0
        grand_filled = 0
        for c in cats:
            dim_keys = [d[0] for d in cat_dim_keys[c.slug]]
            products = db.query(Product).filter(Product.category_id == c.id).all()
            for p in products:
                p_dims = p.dimensions or {}
                for dk in dim_keys:
                    grand_expected += 1
                    if dk in p_dims and p_dims[dk] is not None:
                        grand_filled += 1
        fill_rate = grand_filled / grand_expected * 100 if grand_expected > 0 else 0
        print(f"  总体维度填充率: {grand_filled}/{grand_expected} = {fill_rate:.1f}%")

        # 各品类
        print(f"\n  品类明细:")
        for c in cats:
            dim_keys = [d[0] for d in cat_dim_keys[c.slug]]
            products = db.query(Product).filter(Product.category_id == c.id).all()
            expected = 0
            filled = 0
            for p in products:
                p_dims = p.dimensions or {}
                for dk in dim_keys:
                    expected += 1
                    if dk in p_dims and p_dims[dk] is not None:
                        filled += 1
            rate = filled / expected * 100 if expected > 0 else 0
            bar = '#' * int(rate / 5)
            print(f"    {c.name:16s} {filled:4d}/{expected:4d} = {rate:5.1f}% {bar}")

        print(f"\n✅ 数据填充完成！")

    except Exception as e:
        db.rollback()
        print(f"❌ 出错: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
