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
