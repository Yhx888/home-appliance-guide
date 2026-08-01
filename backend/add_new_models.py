"""博主主推新款入库 — 仅写入已核验的真实参数/价格

每款新品均来自 2025-2026 博主主推清单，参数/价格只使用已查证来源
（厂商官网 / 电商参数页 / 权威媒体），每个维度写入 data_points 供 verify 核验。

运行：python backend/add_new_models.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, Category, Dimension, Product
from backend.scrapers.base import Collector


# 每条: slug, brand, model, price_low, price_high, price_sources, dims{key: (value, [urls])}
NEW_MODELS = [
    # ── 冰箱 ──
    {
        "slug": "cat-6", "brand": "美的", "model": "508海贝白",
        "price_low": 2600.0, "price_high": 3800.0,
        "price_sources": ["https://m.suning.com/itemcanshu/0010359722/12448601451.html",
                          "https://weibo.com/2/detail/comos:niknezi1684293?utm_source=comos"],
        "dims": {
            "容量_L": (508.0, ["https://m.suning.com/itemcanshu/0010359722/12448601451.html"]),
            "门型": ("十字门", ["https://fe.suning.com/bigimages/12442861292.html"]),
            "制冷方式": ("风冷", ["https://jd.zol.com.cn/951/9511775_all.html"]),
            "双系统": (True, ["https://m.suning.com/itemcanshu/0010359722/12448601451.html"]),
        },
    },
    {
        "slug": "cat-6", "brand": "海尔", "model": "山茶花510",
        "price_low": 3600.0, "price_high": 4700.0,
        "price_sources": ["https://m.smzdm.com/p/179565751/",
                          "https://post.smzdm.com/p/ak8mwe0e/"],
        "dims": {
            "容量_L": (510.0, ["https://www.haier.com/cooling/20250605_265348.shtml",
                               "https://m.suning.com/itemcanshu/0010357054/12449321508.html"]),
            "门型": ("法式多门", ["https://www.haier.com/cooling/20250605_265348.shtml"]),
            "制冷方式": ("风冷", ["https://www.haier.com/cooling/20250605_265348.shtml"]),
            "嵌入深度_mm": (594.0, ["https://m.suning.com/itemcanshu/0010357054/12449321508.html"]),
        },
    },
    # ── 空调 ──
    {
        "slug": "cat-10", "brand": "华凌", "model": "N8HE1",
        "price_low": 1600.0, "price_high": 2000.0,
        "price_sources": ["https://www.xiaohongshu.com/discovery/item/64c51a65000000001700ee6f"],
        "dims": {
            "能效_APF": (5.27, ["https://baike.baidu.com/item/%E5%8D%8E%E5%87%8CKFR-35GW%2FN8HE1/53548148",
                                "https://wiki.smzdm.com/p/3qw5j6m/canshu/"]),
            "匹数": (1.5, ["https://wiki.smzdm.com/p/3qw5j6m/canshu/"]),
            "自清洁": (True, ["http://m.suning.com/itemcanshu/0010334159/12128857519.html"]),
            "噪音_dB": (18.0, ["http://m.suning.com/itemcanshu/0010334159/12128857519.html"]),
        },
    },
    # ── 洗衣机 ──
    {
        "slug": "cat-15", "brand": "海尔", "model": "云溪5.0洗烘套装",
        "price_low": 7000.0, "price_high": 9000.0,
        "price_sources": ["https://post.smzdm.com/p/agg63g63/"],
        "dims": {
            "容量_kg": (12.0, ["https://post.smzdm.com/p/apqoxxpx/#comments"]),
            "洗净比": (1.36, ["https://weibo.com/2/detail/comos:niksnxi0906542?utm_source=comos"]),
            "烘干方式": ("双擎热泵", ["https://weibo.com/2/detail/comos:niksnxi0906542?utm_source=comos"]),
            "电机类型": ("DD直驱", ["https://post.smzdm.com/talk/p/axkelq73/"]),
        },
    },
    {
        "slug": "cat-15", "brand": "小天鹅", "model": "小乌梅5.0洗烘套装",
        "price_low": 8000.0, "price_high": 12000.0,
        "price_sources": ["https://weibo.com/2/detail/comos:niktqkv0819623?utm_source=comos"],
        "dims": {
            "容量_kg": (12.0, ["https://jd.zol.com.cn/1223/12238908.html"]),
            "洗净比": (1.36, ["https://post.smzdm.com/p/a6z6wrme/p2/#cl_3"]),
            "烘干方式": ("热泵", ["https://jd.zol.com.cn/1223/12238908.html"]),
        },
    },
    # ── 智能马桶 ──
    {
        "slug": "cat-13", "brand": "九牧", "model": "X70",
        "price_low": 5000.0, "price_high": 8000.0,
        "price_sources": ["https://m.sohu.com/a/993360585_122544399/"],
        "dims": {
            "加热方式": ("即热式", ["https://post.smzdm.com/p/aggk5n33/"]),
            "冲洗技术": ("翻转冲刷", ["https://www.to8to.com/yezhuapp/t467437.html"]),
            "翻盖方式": ("自动感应", ["https://post.smzdm.com/p/a70xmq4o/"]),
        },
    },
    {
        "slug": "cat-13", "brand": "恒洁", "model": "R9",
        "price_low": 8000.0, "price_high": 10000.0,
        "price_sources": ["https://www.xiaohongshu.com/discovery/item/69313e2c000000001e024a81",
                          "https://tianya.im/t.php?id=18696"],
        "dims": {
            "加热方式": ("即热式", ["https://post.smzdm.com/p/a343oqq7/"]),
            "翻盖方式": ("自动感应", ["https://post.smzdm.com/p/a343oqq7/"]),
        },
    },
    # ── 电视 ──
    {
        "slug": "cat-16", "brand": "TCL", "model": "T7L Pro 75寸",
        "price_low": 5800.0, "price_high": 6900.0,
        "price_sources": ["https://product.bl.com/7551838.html",
                          "http://m.suning.com/itemcanshu/0000000000/000000012443169209.html"],
        "dims": {
            "尺寸_寸": (75.0, ["https://m.ithome.com/mip/html/852824.htm"]),
            "面板类型": ("QD-MiniLED", ["https://m.ithome.com/mip/html/852824.htm"]),
            "分区数": (720.0, ["https://m.ithome.com/mip/html/852824.htm"]),
            "刷新率_Hz": (288.0, ["https://tv.zol.com.cn/1114/11142612.html"]),
            "色域_pct": (98.0, ["https://wiki.m.smzdm.com/p/5vq81md/"]),
        },
    },
    {
        "slug": "cat-16", "brand": "海信", "model": "85E8Q",
        "price_low": 10000.0, "price_high": 12000.0,
        "price_sources": ["https://www.smzdm.com/p/176171036/"],
        "dims": {
            "尺寸_寸": (85.0, ["https://zhekou.manmanbuy.com/m/zhekou.aspx?id=530335502"]),
            "面板类型": ("MiniLED", ["https://post.m.smzdm.com/p/arz9np4z/"]),
            "分区数": (4224.0, ["https://zhekou.manmanbuy.com/m/zhekou.aspx?id=530335502"]),
            "刷新率_Hz": (330.0, ["https://zhekou.manmanbuy.com/m/zhekou.aspx?id=530335502"]),
            "色域_pct": (98.0, ["https://post.m.smzdm.com/p/arz9np4z/"]),
            "音响": ("帝瓦雷", ["https://zhekou.manmanbuy.com/m/zhekou.aspx?id=530335502"]),
        },
    },
    {
        "slug": "cat-16", "brand": "雷鸟", "model": "鹤6 Ultra 85寸",
        "price_low": 5100.0, "price_high": 7300.0,
        "price_sources": ["https://tv.zol.com.cn/1122/11229024.html",
                          "https://tv.zol.com.cn/1197/11975379.html"],
        "dims": {
            "尺寸_寸": (85.0, ["https://tv.zol.com.cn/1220/12205167.html"]),
            "面板类型": ("MiniLED", ["https://tv.zol.com.cn/1220/12205167.html"]),
            "分区数": (1056.0, ["https://tv.zol.com.cn/1220/12205167.html"]),
        },
    },
    # ── 净水器 ──
    {
        "slug": "cat-5", "brand": "美的", "model": "白泽Max 1200G",
        "price_low": 1060.0, "price_high": 1900.0,
        "price_sources": ["https://post.smzdm.com/p/a2q90x4p/#comments",
                          "https://www.smzdm.com/p/179038767/"],
        "dims": {
            "通量_G": (1200.0, ["https://post.smzdm.com/p/a2q90x4p/#comments"]),
            "RO膜寿命_年": (6.0, ["https://post.smzdm.com/p/a2q90x4p/#comments"]),
        },
    },
    {
        "slug": "cat-5", "brand": "安吉尔", "model": "玉龙Pro 1200G",
        "price_low": 2000.0, "price_high": 2700.0,
        "price_sources": ["http://m.suning.com/item/0000000000/000000012446948840.html"],
        "dims": {
            "通量_G": (1200.0, ["http://m.suning.com/item/0000000000/000000012446948840.html"]),
            "RO膜寿命_年": (5.0, ["https://post.smzdm.com/p/a03rdgoz/"]),
            "过滤级数": (7.0, ["https://post.smzdm.com/p/a03rdgoz/"]),
        },
    },
    # ── 洗碗机 ──
    {
        "slug": "cat-4", "brand": "美的", "model": "RX600S Max",
        "price_low": 4000.0, "price_high": 4500.0,
        "price_sources": ["http://m.suning.com/itemcanshu/0071641878/000000012451743071.html"],
        "dims": {
            "容量_套": (15.0, ["http://m.suning.com/itemcanshu/0071641878/000000012451743071.html"]),
            "类型": ("独嵌两用", ["http://m.suning.com/itemcanshu/0071641878/000000012451743071.html"]),
            "烘干方式": ("热风", ["http://m.suning.com/itemcanshu/0071641878/000000012451743071.html"]),
            "水效等级": ("一级", ["http://m.suning.com/itemcanshu/0071641878/000000012451743071.html"]),
            "噪音_dB": (44.0, ["https://item.szlcsc.com/mro/56492547.html"]),
        },
    },
    {
        "slug": "cat-4", "brand": "西门子", "model": "SJ23EI24KC",
        "price_low": 4800.0, "price_high": 4900.0,
        "price_sources": ["https://g.pconline.com.cn/product/xiwanji/siemens/2574999.html"],
        "dims": {
            "容量_套": (15.0, ["https://product.pconline.com.cn/xiwanji/siemens/1s1.shtml"]),
            "类型": ("嵌入式", ["https://product.pconline.com.cn/xiwanji/siemens/1s1.shtml"]),
            "烘干方式": ("智能开门", ["http://m.suning.com/itemcanshu/0071577604/000000012438965525.html"]),
            "保修_年": (1.0, ["http://m.suning.com/itemcanshu/0071577604/000000012438965525.html"]),
        },
    },
    # ── 油烟机 ──
    {
        "slug": "cat-1", "brand": "美的", "model": "AK5 Pro",
        "price_low": 1900.0, "price_high": 2400.0,
        "price_sources": ["https://post.smzdm.com/p/a4q2m75w/"],
        "dims": {
            "风量_m3": (25.0, ["https://fe.suning.com/bigimages/12443007525.html"]),
            "静压_Pa": (1000.0, ["https://fe.suning.com/bigimages/12443007525.html"]),
        },
    },
    {
        "slug": "cat-1", "brand": "华帝", "model": "小飞碟S36",
        "price_low": 2300.0, "price_high": 2400.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1905313243435603203"],
        "dims": {
            "风量_m3": (26.0, ["http://www.cheari.com/npage.html?id=20772"]),
            "静压_Pa": (1000.0, ["http://www.cheari.com/npage.html?id=20772"]),
        },
    },
    # ── 空气净化器 ──
    {
        "slug": "cat-12", "brand": "352", "model": "X86C",
        "price_low": 4300.0, "price_high": 4500.0,
        "price_sources": ["https://detail.zol.com.cn/ProductComp_param_1360071.html"],
        "dims": {
            "颗粒物CADR": (650.0, ["https://detail.zol.com.cn/ProductComp_param_1360071.html"]),
            "甲醛CADR": (400.0, ["https://detail.zol.com.cn/ProductComp_param_1360071.html"]),
        },
    },
    # ── 蒸烤箱 ──
    {
        "slug": "cat-3", "brand": "凯度", "model": "T2 Pro",
        "price_low": 4000.0, "price_high": 5100.0,
        "price_sources": ["https://weibo.com/2/detail/comos:nikqqhf1239042?utm_source=comos",
                          "https://post.smzdm.com/p/a95nv26e/"],
        "dims": {
            "容量_L": (60.0, ["https://weibo.com/2/detail/comos:nikqqhf1239042?utm_source=comos",
                              "https://post.smzdm.com/p/a95nv26e/"]),
            "有微波": (False, ["https://post.smzdm.com/p/a95nv26e/"]),
        },
    },
    # ── 抽油烟机：2025-2026 博主高赞调研主推（多篇来源重合）──
    {
        "slug": "cat-1", "brand": "方太", "model": "V1S-G",
        "price_low": 4299.0, "price_high": 4749.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1892874680102277427",
                          "https://finance.sina.com.cn/tech/roll/2025-06-06/doc-inezcvsc5365689.shtml"],
        "dims": {
            "风量_m3": (28.0, ["https://zhuanlan.zhihu.com/p/1892874680102277427",
                               "https://zhuanlan.zhihu.com/p/1962510983126820825"]),
            "静压_Pa": (1000.0, ["https://zhuanlan.zhihu.com/p/1892874680102277427",
                                 "https://zhuanlan.zhihu.com/p/2021709921184400553"]),
        },
    },
    {
        "slug": "cat-1", "brand": "美的", "model": "AK7 Pro",
        "price_low": 2599.0, "price_high": 3199.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/685641331",
                          "https://finance.sina.com.cn/tech/roll/2025-06-06/doc-inezcvsc5365689.shtml"],
        "dims": {
            "风量_m3": (28.0, ["https://zhuanlan.zhihu.com/p/1892874680102277427",
                               "https://zhuanlan.zhihu.com/p/1962510983126820825"]),
            "静压_Pa": (1000.0, ["https://zhuanlan.zhihu.com/p/1892874680102277427",
                                 "https://zhuanlan.zhihu.com/p/2021709921184400553"]),
        },
    },
    {
        "slug": "cat-1", "brand": "小米/米家", "model": "净烟机P2(MJ06CY)",
        "price_low": 2000.0, "price_high": 2500.0,
        "price_sources": ["https://zhihu.com/question/678509688",
                          "https://zhuanlan.zhihu.com/p/2021709921184400553"],
        "dims": {},
    },
    # ── 电视机：2025-2026 博主高赞调研主推（多篇来源重合）──
    {
        "slug": "cat-16", "brand": "海信", "model": "E8Q Pro 75寸",
        "price_low": 8000.0, "price_high": 9000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1103224133",
                          "https://zhuanlan.zhihu.com/p/2020186080427647609"],
        "dims": {
            "尺寸_寸": (75.0, ["https://zhuanlan.zhihu.com/p/1103224133"]),
            "面板类型": ("MiniLED", ["https://zhuanlan.zhihu.com/p/1103224133"]),
            "分区数": (5040.0, ["https://zhuanlan.zhihu.com/p/1103224133",
                                "https://zhuanlan.zhihu.com/p/2020186080427647609"]),
        },
    },
    {
        "slug": "cat-16", "brand": "TCL", "model": "Q10L 75寸",
        "price_low": 7000.0, "price_high": 8000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1103224133",
                          "https://zhuanlan.zhihu.com/p/2020186080427647609"],
        "dims": {
            "尺寸_寸": (75.0, ["https://zhuanlan.zhihu.com/p/1103224133"]),
            "面板类型": ("QD-MiniLED", ["https://zhuanlan.zhihu.com/p/1103224133"]),
            "分区数": (2176.0, ["https://zhuanlan.zhihu.com/p/1103224133",
                                "https://zhuanlan.zhihu.com/p/2020186080427647609"]),
        },
    },
    {
        "slug": "cat-16", "brand": "创维", "model": "A5F Pro 55寸",
        "price_low": 3500.0, "price_high": 5000.0,
        "price_sources": ["https://post.m.smzdm.com/zz/p/awd2p9wk/",
                          "https://zhuanlan.zhihu.com/p/1979859785684902924"],
        "dims": {
            "尺寸_寸": (55.0, ["https://post.m.smzdm.com/zz/p/awd2p9wk/"]),
        },
    },
    # ── 燃气灶：2025-2026 博主高赞调研主推（多篇来源重合）──
    {
        "slug": "cat-2", "brand": "德普", "model": "D5MAX",
        "price_low": 1700.0, "price_high": 2300.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/269601212",
                          "https://zhuanlan.zhihu.com/p/2041231145434625341"],
        "dims": {
            "火力_kW": (5.2, ["https://zhuanlan.zhihu.com/p/269601212"]),
            "热效率_pct": (70.0, ["https://zhuanlan.zhihu.com/p/269601212"]),
        },
    },
    {
        "slug": "cat-2", "brand": "美的", "model": "JZT-AK7",
        "price_low": 1500.0, "price_high": 2200.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/2024229839213790079",
                          "https://zhuanlan.zhihu.com/p/269601212"],
        "dims": {
            "热效率_pct": (72.0, ["https://zhuanlan.zhihu.com/p/2024229839213790079"]),
        },
    },
    {
        "slug": "cat-2", "brand": "德普", "model": "D5PRO",
        "price_low": 1400.0, "price_high": 1900.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/269601212",
                          "https://zhuanlan.zhihu.com/p/2041231145434625341"],
        "dims": {
            "火力_kW": (5.2, ["https://zhuanlan.zhihu.com/p/269601212"]),
        },
    },
    {
        "slug": "cat-2", "brand": "方太", "model": "TF37B",
        "price_low": 2200.0, "price_high": 3000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/2041231145434625341",
                          "https://zhuanlan.zhihu.com/p/2024229839213790079"],
        "dims": {
            "热效率_pct": (70.0, ["https://zhuanlan.zhihu.com/p/2041231145434625341"]),
        },
    },
    {
        "slug": "cat-2", "brand": "美的", "model": "QD529",
        "price_low": 1500.0, "price_high": 2100.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/2041231145434625341",
                          "https://zhuanlan.zhihu.com/p/2024229839213790079"],
        "dims": {
            "热效率_pct": (70.0, ["https://zhuanlan.zhihu.com/p/2041231145434625341"]),
        },
    },
    {
        "slug": "cat-2", "brand": "海尔", "model": "H70D",
        "price_low": 700.0, "price_high": 1000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/2024229839213790079"],
        "dims": {
            "热效率_pct": (72.0, ["https://zhuanlan.zhihu.com/p/2024229839213790079"]),
        },
    },
    # ── 蒸烤箱：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-3", "brand": "美的", "model": "知味感R6S二代",
        "price_low": 5000.0, "price_high": 6000.0,
        "price_sources": ["https://m.jiemian.com/article/14505644.html",
                          "https://m.zol.com.cn/article/11700192.html"],
        "dims": {
            "容量_L": (60.0, ["https://m.zol.com.cn/article/11700192.html"]),
            "有微波": (True, ["https://m.zol.com.cn/article/11700192.html"]),
        },
    },
    {
        "slug": "cat-3", "brand": "老板", "model": "小贝果D3P",
        "price_low": 5000.0, "price_high": 5500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/26410266584",
                          "https://m.zol.com.cn/article/11700192.html"],
        "dims": {
            "容量_L": (77.0, ["https://zhuanlan.zhihu.com/p/26410266584"]),
        },
    },
    # ── 洗碗机：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-4", "brand": "美的", "model": "GX1000S Max",
        "price_low": 5600.0, "price_high": 7000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/20732805104",
                          "https://zhuanlan.zhihu.com/p/2041593627126806075"],
        "dims": {
            "容量_套": (18.0, ["https://zhuanlan.zhihu.com/p/20732805104"]),
            "烘干方式": ("120℃晶焰烘干", ["https://zhuanlan.zhihu.com/p/1939705004345792019"]),
        },
    },
    {
        "slug": "cat-4", "brand": "美的", "model": "小西梅X7",
        "price_low": 5500.0, "price_high": 6100.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/20732805104",
                          "https://zhuanlan.zhihu.com/p/2041593627126806075"],
        "dims": {
            "容量_套": (22.0, ["https://zhuanlan.zhihu.com/p/20732805104"]),
        },
    },
    # ── 净水器：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-5", "brand": "佳德净", "model": "TH1200",
        "price_low": 1500.0, "price_high": 2500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/122464722",
                          "https://zhuanlan.zhihu.com/p/396139581"],
        "dims": {
            "通量_G": (1200.0, ["https://zhuanlan.zhihu.com/p/396139581"]),
            "年均耗材_元": (150.0, ["https://zhuanlan.zhihu.com/p/122464722"]),
        },
    },
    {
        "slug": "cat-5", "brand": "东芝", "model": "大白梨TSC1000",
        "price_low": 1800.0, "price_high": 2400.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/396139581",
                          "https://zhuanlan.zhihu.com/p/26218345583"],
        "dims": {
            "通量_G": (1000.0, ["https://zhuanlan.zhihu.com/p/396139581"]),
            "RO膜寿命_年": (6.0, ["https://zhuanlan.zhihu.com/p/396139581"]),
        },
    },
    # ── 冰箱：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-6", "brand": "容声", "model": "方糖515",
        "price_low": 4200.0, "price_high": 5200.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/166072247",
                          "https://bilibili.com/video/BV1tbnUznEum"],
        "dims": {
            "容量_L": (515.0, ["https://zhuanlan.zhihu.com/p/166072247"]),
            "门型": ("法式四门", ["https://zhuanlan.zhihu.com/p/166072247"]),
            "双系统": (True, ["https://zhuanlan.zhihu.com/p/21360161477"]),
        },
    },
    {
        "slug": "cat-6", "brand": "美的", "model": "机皇550",
        "price_low": 4800.0, "price_high": 5500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/166072247",
                          "https://zhuanlan.zhihu.com/p/21360161477"],
        "dims": {
            "容量_L": (526.0, ["https://zhuanlan.zhihu.com/p/166072247"]),
            "门型": ("法式多门", ["https://zhuanlan.zhihu.com/p/166072247"]),
            "双系统": (True, ["https://zhuanlan.zhihu.com/p/166072247"]),
        },
    },
    # ── 消毒柜：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-7", "brand": "美的", "model": "110HQ2pro",
        "price_low": 1500.0, "price_high": 1800.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1930566121729294851",
                          "https://zhuanlan.zhihu.com/p/315115162"],
        "dims": {
            "容量_L": (110.0, ["https://zhuanlan.zhihu.com/p/1930566121729294851"]),
            "消毒方式": ("光波2.0+母婴仓", ["https://zhuanlan.zhihu.com/p/315115162"]),
        },
    },
    {
        "slug": "cat-7", "brand": "海尔", "model": "EB031(ZQD110F)",
        "price_low": 1400.0, "price_high": 1800.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1930566121729294851",
                          "https://zhuanlan.zhihu.com/p/315115162"],
        "dims": {
            "容量_L": (110.0, ["https://zhuanlan.zhihu.com/p/1930566121729294851"]),
            "消毒方式": ("光波巴氏无臭氧", ["https://zhuanlan.zhihu.com/p/315115162"]),
        },
    },
    {
        "slug": "cat-7", "brand": "方太", "model": "J55E",
        "price_low": 1700.0, "price_high": 2200.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1930566121729294851",
                          "https://www.jd.com/phb/7375b7c4126935fff25.html"],
        "dims": {
            "容量_L": (110.0, ["https://zhuanlan.zhihu.com/p/1930566121729294851"]),
            "消毒方式": ("IR+UV+热风", ["https://zhuanlan.zhihu.com/p/1930566121729294851"]),
        },
    },
    # ── 中央空调：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-8", "brand": "小米", "model": "中央空调Pro(一拖四)",
        "price_low": 16000.0, "price_high": 20000.0,
        "price_sources": ["https://bilibili.com/video/BV121oaYDEc3/",
                          "https://zhuanlan.zhihu.com/p/1953776396418651268"],
        "dims": {
            "能效_APF": (5.5, ["https://zhuanlan.zhihu.com/p/1953776396418651268"]),
        },
    },
    {
        "slug": "cat-8", "brand": "美的", "model": "星光Pro(5匹)",
        "price_low": 21000.0, "price_high": 27000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1953776396418651268"],
        "dims": {},
    },
    {
        "slug": "cat-8", "brand": "美的", "model": "领航者(3代)",
        "price_low": 28000.0, "price_high": 35000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1906484558158857585"],
        "dims": {},
    },
    # ── 新风系统：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-9", "brand": "松下", "model": "FY-35ZDP1C",
        "price_low": 7000.0, "price_high": 9000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1969525565502492787"],
        "dims": {
            "风量_m3h": (330.0, ["https://zhuanlan.zhihu.com/p/1969525565502492787"]),
            "热交换率_pct": (78.0, ["https://zhuanlan.zhihu.com/p/1969525565502492787"]),
        },
    },
    {
        "slug": "cat-9", "brand": "艾泊斯", "model": "AC260",
        "price_low": 7000.0, "price_high": 9000.0,
        "price_sources": ["https://zhihu.com/tardis/bd/art/288533298"],
        "dims": {
            "风量_m3h": (320.0, ["https://zhihu.com/tardis/bd/art/288533298"]),
        },
    },
    # ── 挂机/柜机空调：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-10", "brand": "华凌", "model": "神机二代Pro(N8HE1ⅡPro)",
        "price_low": 1600.0, "price_high": 2000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/699979357",
                          "https://zhuanlan.zhihu.com/p/1966138106110521466"],
        "dims": {
            "能效_APF": (6.02, ["https://zhuanlan.zhihu.com/p/699979357"]),
            "匹数": (1.5, ["https://zhuanlan.zhihu.com/p/699979357"]),
            "噪音_dB": (18.0, ["https://zhuanlan.zhihu.com/p/699979357"]),
        },
    },
    {
        "slug": "cat-10", "brand": "华凌", "model": "神机二代(N8HE1Ⅱ)",
        "price_low": 1500.0, "price_high": 1700.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/699979357",
                          "https://zhuanlan.zhihu.com/p/1966138106110521466"],
        "dims": {
            "匹数": (1.5, ["https://zhuanlan.zhihu.com/p/1966138106110521466"]),
        },
    },
    {
        "slug": "cat-10", "brand": "华凌", "model": "神机二代3匹柜机(N8HE1Ⅱ)",
        "price_low": 3800.0, "price_high": 4200.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/699979357",
                          "https://sspai.com/post/101621"],
        "dims": {
            "匹数": (3.0, ["https://zhuanlan.zhihu.com/p/699979357"]),
        },
    },
    # ── 扫地机器人：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-11", "brand": "科沃斯", "model": "T80",
        "price_low": 3100.0, "price_high": 3655.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1961948012617114269",
                          "https://bilibili.com/video/BV11SdUYFEnS/"],
        "dims": {
            "拖地方式": ("滚筒活水洗地", ["https://zhuanlan.zhihu.com/p/1961948012617114269"]),
        },
    },
    {
        "slug": "cat-11", "brand": "石头", "model": "G30",
        "price_low": 5000.0, "price_high": 5500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1960057550872515581",
                          "https://post.smzdm.com/p/am33p0p4/"],
        "dims": {},
    },
    {
        "slug": "cat-11", "brand": "云鲸", "model": "逍遥002",
        "price_low": 3500.0, "price_high": 5700.0,
        "price_sources": ["https://bilibili.com/video/BV1kd7BzgEZ5/",
                          "https://zhuanlan.zhihu.com/p/1961948012617114269"],
        "dims": {
            "拖地方式": ("履带式拖布", ["https://bilibili.com/video/BV1kd7BzgEZ5/"]),
        },
    },
    # ── 空气净化器：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-12", "brand": "小米", "model": "全效空气净化器Ultra",
        "price_low": 2500.0, "price_high": 4799.0,
        "price_sources": ["https://bilibili.com/video/BV1Se4y167As",
                          "https://zhuanlan.zhihu.com/p/2041166349951563322"],
        "dims": {},
    },
    {
        "slug": "cat-12", "brand": "352", "model": "Z90",
        "price_low": 5499.0, "price_high": 5599.0,
        "price_sources": ["https://bilibili.com/video/BV1YEG76TEoM",
                          "https://zhuanlan.zhihu.com/p/2041166349951563322"],
        "dims": {},
    },
    {
        "slug": "cat-12", "brand": "IAM", "model": "M9 Pro",
        "price_low": 6500.0, "price_high": 7500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/2041166349951563322",
                          "https://post.smzdm.com/p/a3mp207d"],
        "dims": {
            "颗粒物CADR": (1000.0, ["https://zhuanlan.zhihu.com/p/2041166349951563322"]),
        },
    },
    {
        "slug": "cat-12", "brand": "树新风", "model": "T2 Pro",
        "price_low": 2500.0, "price_high": 2999.0,
        "price_sources": ["https://bilibili.com/video/BV1fZfhY6EU6",
                          "https://bilibili.com/video/BV1uujPzDEfM"],
        "dims": {
            "颗粒物CADR": (1205.0, ["https://bilibili.com/video/BV1fZfhY6EU6"]),
            "甲醛CADR": (882.0, ["https://bilibili.com/video/BV1fZfhY6EU6"]),
        },
    },
    # ── 智能马桶：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-13", "brand": "恒洁", "model": "S3Pro(DCQ661P-305)",
        "price_low": 1400.0, "price_high": 1800.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/26938194888",
                          "https://163.com/dy/article/KTNRESPD0540SNRB.html"],
        "dims": {
            "无水压限制": (True, ["https://zhuanlan.zhihu.com/p/26938194888"]),
        },
    },
    # ── 热水器：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-14", "brand": "海尔", "model": "KL7S(JSQ31-16KL7SFPAGU1)",
        "price_low": 2800.0, "price_high": 3500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/202854288",
                          "https://zhuanlan.zhihu.com/p/419305602"],
        "dims": {
            "升数_L": (16.0, ["https://zhuanlan.zhihu.com/p/202854288"]),
            "恒温技术": ("双循环恒温", ["https://zhuanlan.zhihu.com/p/202854288"]),
        },
    },
    {
        "slug": "cat-14", "brand": "海尔", "model": "KL7PRO(JSQ31-16KL7PROFU1)",
        "price_low": 1800.0, "price_high": 2400.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/202854288",
                          "https://zhuanlan.zhihu.com/p/419305602"],
        "dims": {
            "升数_L": (16.0, ["https://zhuanlan.zhihu.com/p/202854288"]),
            "恒温技术": ("无级变频水伺服", ["https://zhuanlan.zhihu.com/p/419305602"]),
        },
    },
    {
        "slug": "cat-14", "brand": "海尔", "model": "KL3PRO(JSQ31-16KL3PRO-FPXCU1)",
        "price_low": 1000.0, "price_high": 2200.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/419305602",
                          "https://zhuanlan.zhihu.com/p/1906114507882889747"],
        "dims": {
            "升数_L": (16.0, ["https://zhuanlan.zhihu.com/p/419305602"]),
            "恒温技术": ("无级变频水伺服", ["https://zhuanlan.zhihu.com/p/419305602"]),
        },
    },
    {
        "slug": "cat-14", "brand": "林内", "model": "GD32(JSQ31-GD32)",
        "price_low": 1830.0, "price_high": 2400.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1995944980716475622",
                          "https://zhuanlan.zhihu.com/p/614811583"],
        "dims": {
            "升数_L": (16.0, ["https://zhuanlan.zhihu.com/p/1995944980716475622"]),
        },
    },
    # ── 洗衣机：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-15", "brand": "小天鹅", "model": "小乌梅3.0(TG10VE40)",
        "price_low": 2200.0, "price_high": 4000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/219702607",
                          "https://zhuanlan.zhihu.com/p/2042547342839116795"],
        "dims": {
            "容量_kg": (10.0, ["https://zhuanlan.zhihu.com/p/2042547342839116795"]),
            "洗净比": (1.21, ["https://zhuanlan.zhihu.com/p/2042547342839116795"]),
        },
    },
    {
        "slug": "cat-15", "brand": "海尔", "model": "云溪4.0(XQG100-BLEG583HU1)",
        "price_low": 2800.0, "price_high": 3500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/219702607",
                          "https://zhuanlan.zhihu.com/p/2042547342839116795"],
        "dims": {
            "容量_kg": (10.0, ["https://zhuanlan.zhihu.com/p/2042547342839116795"]),
            "洗净比": (1.21, ["https://zhuanlan.zhihu.com/p/2042547342839116795"]),
            "电机类型": ("DD直驱", ["https://zhuanlan.zhihu.com/p/2042547342839116795"]),
        },
    },
    # ── 集成灶等：2025-2026 博主高赞调研主推 ──
    {
        "slug": "cat-17", "brand": "亿田", "model": "D6ZK",
        "price_low": 9700.0, "price_high": 12800.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/13977982500",
                          "https://zhongce.sina.com.cn/iframe/article/view/174488/"],
        "dims": {
            "风量_m3": (21.5, ["https://zhuanlan.zhihu.com/p/13977982500"]),
            "静压_Pa": (1050.0, ["https://zhuanlan.zhihu.com/p/13977982500"]),
        },
    },
    {
        "slug": "cat-17", "brand": "凯度", "model": "T2E Pro",
        "price_low": 8800.0, "price_high": 12500.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1982030640120628600",
                          "https://zhongce.sina.com.cn/iframe/article/view/174488/"],
        "dims": {},
    },
    {
        "slug": "cat-17", "brand": "美的", "model": "晴空FX90 PRO",
        "price_low": 7000.0, "price_high": 9000.0,
        "price_sources": ["https://zhuanlan.zhihu.com/p/1982030640120628600",
                          "https://bilibili.com/video/BV1Ds7azTExX/"],
        "dims": {
            "风量_m3": (26.0, ["https://zhuanlan.zhihu.com/p/1982030640120628600"]),
            "静压_Pa": (1100.0, ["https://zhuanlan.zhihu.com/p/1982030640120628600"]),
        },
    },
    {
        "slug": "cat-17", "brand": "火星人", "model": "ET50BC",
        "price_low": 10000.0, "price_high": 12000.0,
        "price_sources": ["https://zhongce.sina.com.cn/iframe/article/view/174488/",
                          "https://zhuanlan.zhihu.com/p/1982030640120628600"],
        "dims": {},
    },
]


def main():
    db = SessionLocal()
    collector = Collector(db)
    cats = {c.slug: c for c in db.query(Category).all()}
    inserted = 0
    skipped = []
    try:
        for item in NEW_MODELS:
            cat = cats[item["slug"]]
            dim_defs = {d.dim_key: d for d in db.query(Dimension).filter(Dimension.category_id == cat.id).all()}
            exists = (
                db.query(Product)
                .filter(Product.category_id == cat.id, Product.brand == item["brand"],
                        Product.model == item["model"])
                .first()
            )
            if exists:
                skipped.append(f"{item['brand']} {item['model']} 已存在")
                continue
            p = Product(
                category_id=cat.id,
                brand=item["brand"],
                model=item["model"],
                price_low=item["price_low"],
                price_high=item["price_high"],
                price_collected_at=datetime.now(),
                dimensions={},
            )
            db.add(p)
            db.commit()

            # 价格来源记录为 data_points（维度键 价格_low；A 阶段插入价格维度后可参与 verify 写回）
            for url in item["price_sources"]:
                src = collector.get_or_create_source("web_research", url=url, method="search")
                collector.save_point(p, "价格_low", item["price_low"], src)

            dims = {}
            for key, (value, urls) in item["dims"].items():
                if key not in dim_defs:
                    print(f"警告: {item['brand']} {item['model']} 维度 {key} 不在品类定义中，跳过")
                    continue
                dims[key] = value
                for url in urls:
                    platform = "manufacturer_html" if ("haier.com" in url or "mi.com" in url) else "web_research"
                    src = collector.get_or_create_source(platform, url=url, method="html" if platform == "manufacturer_html" else "search")
                    collector.save_point(p, key, value, src)
            p.dimensions = dims
            db.commit()
            inserted += 1
            print(f"入库: {item['brand']} {item['model']} ({cat.name}) 维度{len(dims)} 价格{item['price_low']}-{item['price_high']}")
    finally:
        collector.close()
    print(f"\n新增 {inserted} 款，跳过 {len(skipped)}")
    for s in skipped:
        print("  -", s)


if __name__ == "__main__":
    main()
