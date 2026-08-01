"""京东实测国补后价格写库（Kimi WebBridge 浏览器核验）

price_low = 国补后/到手价（用户要求的准确数字）
price_high = 原价（有核验来源时更新，否则保留原区间上限）
同时写入 data_points（dimension_key=价格_low）记录来源 URL。

运行：python backend/update_verified_prices.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, Product
from backend.scrapers.base import Collector


JD_SEARCH = "https://search.jd.com/Search?enc=utf-8&keyword={kw}"

# (brand, model, 国补后到手价, 原价/区间上限, 京东搜索关键词)
PRICE_UPDATES = [
    ("小米", "508升十字", 3598.9, 4234.0, "小米508冰箱"),
    ("苏泊尔", "DB28", 490.67, 699.0, "苏泊尔DB28燃气灶"),
    ("美的", "AK5 Pro", 1897.03, 2231.8, "美的AK5Pro油烟机"),
    ("美的", "白泽Max 1200G", 1398.96, 1828.7, "美的白泽Max净水器"),
    ("海尔", "山茶花510", 3880.13, 5286.0, "海尔山茶花510冰箱"),
    ("海尔", "云溪5.0洗烘套装", 9548.58, 12331.0, "海尔云溪5.0洗烘套装"),
    ("小天鹅", "小乌梅5.0洗烘套装", 9738.53, 12543.0, "小天鹅小乌梅5.0洗烘套装"),
    ("TCL", "T7L Pro 75寸", 6403.54, 7249.0, "TCL T7L Pro 75寸电视"),
    ("海信", "85E8Q", 9953.0, 11499.0, "海信85E8Q电视"),
    ("雷鸟", "鹤6 Ultra 85寸", 6473.11, 7646.0, "雷鸟鹤6Ultra85寸电视"),
    ("华凌", "N8HE1", 1741.65, 2099.0, "华凌N8HE1"),
    ("美的", "508海贝白", 2885.7, 3789.0, "美的508冰箱"),
    ("九牧", "X70", 6140.0, 6800.0, "九牧X70智能马桶"),
    ("恒洁", "R9", 14074.96, 15978.0, "恒洁R9智能马桶"),
    ("安吉尔", "玉龙Pro 1200G", 2018.24, 2650.0, "安吉尔玉龙Pro净水器"),
    ("美的", "RX600S Max", 3699.0, 4499.0, "美的RX600S Max洗碗机"),
]


def main():
    db = SessionLocal()
    collector = Collector(db)
    updated = 0
    not_found = []
    try:
        for brand, model, low, high, kw in PRICE_UPDATES:
            p = db.query(Product).filter(Product.brand == brand, Product.model == model).first()
            if p is None:
                not_found.append(f"{brand} {model}")
                continue
            old = (p.price_low, p.price_high)
            p.price_low = low
            p.price_high = high
            p.price_collected_at = datetime.now()
            db.commit()
            url = JD_SEARCH.format(kw=kw)
            src = collector.get_or_create_source("jd_html", url=url, method="browser")
            collector.save_point(p, "价格_low", low, src)
            updated += 1
            print(f"更新: {brand} {model} {old} -> ({low}, {high})")
    finally:
        collector.close()
    print(f"\n完成：更新 {updated} 款")
    for n in not_found:
        print("未找到:", n)


if __name__ == "__main__":
    main()
