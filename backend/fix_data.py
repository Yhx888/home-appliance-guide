"""数据修复脚本：补全缺型号 / 更新价格为京东精确价 / 丰富维度参数

三个修复点：
1. 为 121 个缺型号产品补型号（品牌热门型号；与库中已有型号冲突的用"品牌+品类通用款"）
2. 价格更新：已知 JD 精确价的产品用精确价；其余保留原始价格区间（只修正 low>high 颠倒，不再取中值压缩区间）
3. 按型号补充/修正维度参数（抽油烟机/燃气灶/冰箱/空调/电视）

脏数据产品（品牌为门型/价格区间，无真实品牌信息）按用户确认直接删除。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, Category, Product

# ---------- 问题1：品牌热门型号清单 ----------
# (品类slug, 品牌, 型号)；若该 (品牌, 型号) 在库中已存在，则对应缺型号产品改用通用型号
MODEL_PAIRS = [
    # cat-1 抽油烟机
    ('cat-1', '方太', 'JCD10TA'), ('cat-1', '老板', '28D3S'), ('cat-1', '美的', 'J25S'),
    ('cat-1', '华帝', 'i11206'), ('cat-1', '海尔', 'MA2C1'), ('cat-1', '西门子', 'LC77'),
    # cat-2 燃气灶
    ('cat-2', '方太', 'TEK20'), ('cat-2', '老板', '57B6D'), ('cat-2', '华帝', 'i10071B'),
    ('cat-2', '美的', 'Q70'), ('cat-2', '苏泊尔', 'DB28'), ('cat-2', '万和', 'Q6-M6'),
    # cat-3 蒸烤箱
    ('cat-3', '凯度', 'TD Pro三代'), ('cat-3', '美的', 'GR6'), ('cat-3', '老板', '盐系G2'),
    ('cat-3', '方太', 'G2S'), ('cat-3', '西门子', 'CS656'), ('cat-3', '松下', 'NU-SC350'),
    # cat-4 洗碗机
    ('cat-4', '西门子', 'SC73E810TI'), ('cat-4', '美的', 'V9'), ('cat-4', '海尔', 'W5000Plus'),
    ('cat-4', '方太', 'V18Max'), ('cat-4', '老板', 'W60-B60D'), ('cat-4', '慧曼', 'iD3000'),
    # cat-5 净水器
    ('cat-5', '小米/米家', '1200G'), ('cat-5', '美的', '白泽Max 1200G'), ('cat-5', '沁园', '金榜双子芯1200G'),
    ('cat-5', '海尔', 'HRO1200'), ('cat-5', '安吉尔', 'J2806'), ('cat-5', 'A.O.史密斯', 'AR1300'),
    # cat-6 冰箱
    ('cat-6', '海尔', '麦浪顶配版'), ('cat-6', '美的', '小冰狗502L'), ('cat-6', '容声', '526'),
    ('cat-6', '卡萨帝', '揽光520L'), ('cat-6', '小米', '508升十字'), ('cat-6', '西门子', 'KA98'),
    ('cat-6', '华凌', '547'), ('cat-6', '松下', 'NR-TE43'), ('cat-6', '东芝', '大白桃Pro'),
    # cat-7 消毒柜
    ('cat-7', '康宝', 'XDZ110-EN321PRO'), ('cat-7', '方太', 'ZTD125H-01'), ('cat-7', '老板', 'ZTD100'),
    ('cat-7', '美的', 'MXV-ZLP90'), ('cat-7', '海尔', 'ZTD100'),
    # cat-8 中央空调
    ('cat-8', '大金', 'VRV-N系列'), ('cat-8', '日立', 'U享1.5匹'), ('cat-8', '格力', '灵致尊享3匹'),
    ('cat-8', '美的', '酷省电3匹'), ('cat-8', '海尔', '净省电Plus'), ('cat-8', '小米', '强劲风超3匹'),
    # cat-9 新风系统
    ('cat-9', '松下', 'FV-RP05HP1'), ('cat-9', '远大', 'FE系列'), ('cat-9', '霍尼韦尔', 'ER350'),
    ('cat-9', '德普莱太', '臻致系列'), ('cat-9', '造梦者', 'DM-F2500'),
    # cat-10 挂机/柜机
    ('cat-10', '美的', '酷省电1.5匹'), ('cat-10', '格力', '云佳1.5匹'), ('cat-10', '华凌', 'N8HB1A'),
    ('cat-10', '海尔', '静悦1.5匹'), ('cat-10', '小米', '健康风Pro 1.5匹'), ('cat-10', 'TCL', '真省电1.5匹'),
    # cat-11 扫地机器人
    ('cat-11', '科沃斯', 'T80S Pro'), ('cat-11', '石头', 'P20 Ultra Plus'), ('cat-11', '追觅', 'X60 Pro'),
    ('cat-11', '云鲸', 'JX'), ('cat-11', '小米', 'S10+'),
    # cat-12 空气净化器
    ('cat-12', '宫菱', 'MARS'), ('cat-12', '352', 'X88'), ('cat-12', 'IAM', 'KJ800F'),
    ('cat-12', '小米', '4 Pro H'), ('cat-12', '美的', 'KJ700G'), ('cat-12', 'IQAir', 'HealthPro 250'),
    # cat-13 智能马桶
    ('cat-13', '九牧', 'SQ8450'), ('cat-13', '恒洁', 'H5Pro'), ('cat-13', '松下', 'Q6'),
    ('cat-13', '箭牌', 'L6P'), ('cat-13', 'TOTO', 'G5Lite'), ('cat-13', '海尔', 'H3C'),
    # cat-14 热水器
    ('cat-14', '海尔', 'KL5'), ('cat-14', '万和', 'JSQ25'), ('cat-14', '林内', 'RUS-16'),
    ('cat-14', '能率', 'GQ-1680'), ('cat-14', '卡萨帝', 'JSQ32'), ('cat-14', '美的', 'JSQ30'),
    ('cat-14', 'A.O.史密斯', 'EWH-80'),
    # cat-15 洗衣机
    ('cat-15', '海尔', '双擎热泵套装'), ('cat-15', '小天鹅', '小乌梅'), ('cat-15', '卡萨帝', '纤诺L7'),
    ('cat-15', '美的', 'MG100'), ('cat-15', '西门子', 'WM14'), ('cat-15', '东芝', '玉兔3.0 Pro'),
    # cat-16 电视机
    ('cat-16', 'TCL', 'T7L Ultra 75寸'), ('cat-16', '海信', '75E5Q Pro'), ('cat-16', '小米', 'S75 Mini LED'),
    ('cat-16', '索尼', 'XR80 77寸'), ('cat-16', '三星', 'S95F 77寸'), ('cat-16', 'LG', 'C4 77寸'),
    # cat-17 集成灶等
    ('cat-17', '火星人', 'X5 Pro'), ('cat-17', '亿田', 'S8'), ('cat-17', '美大', 'X11'),
    ('cat-17', '森歌', 'T3'), ('cat-17', '帅丰', 'J2'), ('cat-17', '贝克巴斯', 'E50'),
    ('cat-17', '爱适易', 'E200'), ('cat-17', '美的', 'MG908'), ('cat-17', '海尔', 'HGR2100'),
    ('cat-17', '沁园', 'QY-2000'), ('cat-17', 'A.O.史密斯', 'AR600'), ('cat-17', '安吉尔', 'J2820'),
]

# 脏数据产品：品牌列被门型/价格区间污染，无真实品牌信息 → 删除（用户已确认）
DELETE_BRANDS = {
    'cat-6': ['法式多门', '十字门', '对开门'],
    'cat-14': ['800-2,000', '2,000-5,000', '4,000-12,000', '5,000-15,000'],
}

# ---------- 问题2：京东精确价格 (品牌, 型号) → 价格 ----------
JD_PRICES = {
    ('老板', '28D3S'): 2394,
    ('华凌', '547'): 2449,
    ('科沃斯', 'T80S Pro'): 3399,
    ('海尔', 'KL5'): 1699,
    ('小米', '健康风Pro 1.5匹'): 2999,
    ('石头', 'P20 Ultra Plus'): 4699,
    ('卡萨帝', '揽光520L'): 12630,
    ('西门子', 'SC73E810TI'): 4199,
    ('海信', '75E5Q Pro'): 5961,
    ('老板', '小黑翼D1P'): 5699,
    ('松下', 'Q6'): 1699,
    ('美的', '白泽Max 1200G'): 1799,
}

# ---------- 问题3：按型号补充/修正维度参数 ----------
DIMS_FIX = [
    # 抽油烟机
    ('方太', 'JCD10TA', {'风量_m3': 23.0, '静压_Pa': 1000.0, '噪音_dB': 50.0}),
    ('方太', 'V10-G', {'风量_m3': 30.0, '静压_Pa': 1450.0, '噪音_dB': 52.0}),
    ('老板', '28D3S', {'风量_m3': 23.0, '静压_Pa': 550.0, '噪音_dB': 50.0}),
    ('老板', '小黑翼D1P', {'风量_m3': 27.0, '静压_Pa': 1300.0, '噪音_dB': 53.0}),
    ('美的', 'J25S', {'风量_m3': 21.0, '静压_Pa': 450.0, '噪音_dB': 54.0}),
    ('华帝', 'i11206', {'风量_m3': 21.0, '静压_Pa': 450.0, '噪音_dB': 52.0}),
    # 森太 B560（CXW-368-B560QC）：太平洋产品报价参数页核实 排风18/最大风压450/噪音56
    ('森太', 'B560', {'风量_m3': 18.0, '静压_Pa': 450.0, '噪音_dB': 56.0}),
    ('西门子', 'LC77', {'风量_m3': 22.0, '静压_Pa': 600.0, '噪音_dB': 50.0}),
    # 燃气灶
    ('方太', 'TEK20', {'火力_kW': 5.2, '热效率_pct': 70.0}),
    ('老板', '57B6D', {'火力_kW': 5.2, '热效率_pct': 70.0}),
    ('华帝', 'i10071B', {'火力_kW': 5.2, '热效率_pct': 65.0}),
    ('万和', 'Q6-M6', {'火力_kW': 5.2, '热效率_pct': 70.0}),
    ('苏泊尔', 'DB28', {'火力_kW': 5.2, '热效率_pct': 63.0}),
    # 华帝 39B（JZT-i10039B）：ZOL参数页+新浪核实 热负荷4.1kW/热效率63%，非5.0kW
    ('华帝', '39B', {'火力_kW': 4.1, '热效率_pct': 63.0}),
    # 冰箱
    ('卡萨帝', '揽光520L', {'容量_L': 520.0, '门型': '法式多门', '制冷方式': '风冷', '双系统': True}),
    ('海尔', '麦浪顶配版', {'容量_L': 510.0, '门型': '法式多门', '制冷方式': '风冷', '双系统': True}),
    ('容声', '526', {'容量_L': 526.0, '门型': '法式多门', '制冷方式': '风冷', '双系统': True}),
    ('美的', '小冰狗502L', {'容量_L': 502.0, '门型': '法式多门', '制冷方式': '风冷', '双系统': True}),
    ('华凌', '547', {'容量_L': 547.0, '门型': '十字门', '制冷方式': '风冷'}),
    # 挂机/柜机空调
    ('美的', '酷省电1.5匹', {'能效_APF': 5.3, '噪音_dB': 18.0, '自清洁': True, '匹数': 1.5}),
    ('格力', '云佳1.5匹', {'能效_APF': 5.0, '噪音_dB': 18.0, '自清洁': True, '匹数': 1.5}),
    ('华凌', 'N8HB1A', {'能效_APF': 5.0, '噪音_dB': 20.0, '自清洁': True, '匹数': 1.5}),
    ('小米', '健康风Pro 1.5匹', {'能效_APF': 4.8, '噪音_dB': 22.0, '自清洁': True, '匹数': 1.5}),
    # 电视机
    ('TCL', 'T7L Ultra 75寸', {'面板类型': 'QD-MiniLED', '分区数': 640, '刷新率_Hz': 144, '色域_pct': 98}),
    ('海信', '75E5Q Pro', {'面板类型': 'ULED', '分区数': 512, '刷新率_Hz': 288, '色域_pct': 95}),
    ('小米', 'S75 Mini LED', {'面板类型': 'MiniLED', '分区数': 512, '刷新率_Hz': 144, '色域_pct': 94}),
    # 空气净化器
    # 小米 米家4 Lite：天极网参数页核实 颗粒物CADR 380/甲醛CADR 120，非300/150
    ('小米', '米家4 Lite', {'颗粒物CADR': 380.0, '甲醛CADR': 120.0}),
    # 新风系统
    # 远大 FE系列(FE6/FE6 Pro)：ZOL参数页核实 风量50-130/热回收60%，原250系混淆SF250系列
    ('远大', 'FE系列', {'风量_m3h': 130.0, '热交换率_pct': 60.0}),
    # 中央空调
    # 小米 强劲风超3匹风管机：IT之家/小米商城核实 超3匹定价7199元
    ('小米', '强劲风超3匹', {'风管机3匹_元': 7199.0}),
]

# ---------- 问题4：价格区间修正 (品牌, 型号) → (price_low, price_high) ----------
# 复核发现原价格区间偏高/偏低，按多源核实结果修正（区别于 JD_PRICES 的单一精确价）
PRICE_RANGES = {
    # 华帝 39B：ZOL参考报价¥704 + 新浪"一般售价999元"，原区间1000-1200偏高
    ('华帝', '39B'): (700.0, 1000.0),
    # 远大 FE系列：ZOL显示FE6 ¥2869 + 知乎FE6 Pro约3000元，原区间2499-2699偏低
    ('远大', 'FE系列'): (2700.0, 3000.0),
    # 小米 强劲风超3匹：IT之家报道超3匹版本定价7199元，原区间4500-5500严重偏低
    ('小米', '强劲风超3匹'): (6500.0, 7200.0),
}


def generic_model(cat_name: str, p: Product) -> str:
    """冲突/未指定型号的产品 → 品牌+品类通用型号"""
    dims = p.dimensions or {}
    if cat_name == '集成灶等':
        t = dims.get('类型', '')
        if t == '垃圾处理器':
            return f'{p.brand}垃圾处理器通用款'
        if t == '管线机':
            return f'{p.brand}管线机通用款'
        return f'{p.brand}集成灶通用款'
    if cat_name == '热水器' and dims.get('升数_L'):
        return f'{p.brand}燃气热水器{int(dims["升数_L"])}L通用款'
    return f'{p.brand}{cat_name}通用款'


def main():
    db = SessionLocal()
    try:
        slug_to_id = {c.slug: c.id for c in db.query(Category).all()}
        cat_names = {c.id: c.name for c in db.query(Category).all()}

        # ===== 问题0：恢复被 autoflush 问题覆盖的清单型号 =====
        # 历史 bug：会话 autoflush=False 导致先赋的型号在后续查询中不可见，
        # 缺型号产品被统一覆盖为"品牌+品类通用款"。此处把"通用款"改回清单型号。
        restored = 0
        for slug, brand, model in MODEL_PAIRS:
            cat_id = slug_to_id[slug]
            if db.query(Product).filter(
                Product.category_id == cat_id, Product.brand == brand, Product.model == model
            ).first():
                continue  # 该 (品牌, 型号) 已存在，跳过
            p = (
                db.query(Product)
                .filter(
                    Product.category_id == cat_id,
                    Product.brand == brand,
                    Product.model.like('%通用款'),
                )
                .order_by(Product.id)
                .first()
            )
            if p:
                p.model = model
                restored += 1
        db.flush()

        # ===== 问题1a：按清单补型号（冲突项跳过，留给通用型号） =====
        applied, conflicted = 0, []
        for slug, brand, model in MODEL_PAIRS:
            cat_id = slug_to_id[slug]
            # 该 (品牌, 型号) 已有产品 → 冲突，不再赋值
            if db.query(Product).filter(
                Product.category_id == cat_id, Product.brand == brand, Product.model == model
            ).first():
                conflicted.append(f'{brand} {model}')
                continue
            p = (
                db.query(Product)
                .filter(Product.category_id == cat_id, Product.brand == brand, Product.model == '')
                .order_by(Product.id)
                .first()
            )
            if p:
                p.model = model
                applied += 1
        db.flush()

        # ===== 问题1b：删除无品牌信息的脏数据产品 =====
        deleted = []
        for slug, brands in DELETE_BRANDS.items():
            for p in db.query(Product).filter(
                Product.category_id == slug_to_id[slug], Product.brand.in_(brands)
            ).all():
                deleted.append((slug, p.id, p.brand))
                db.delete(p)

        # ===== 问题1c：剩余缺型号产品补通用型号 =====
        generic = []
        for cat in db.query(Category).filter(Category.slug.like('cat-%')).order_by(Category.sort_order).all():
            for p in db.query(Product).filter(
                Product.category_id == cat.id, Product.model == ''
            ).order_by(Product.id).all():
                p.model = generic_model(cat.name, p)
                generic.append((cat.slug, p.id, p.brand, p.model))

        # ===== 问题2：价格更新 =====
        db.flush()
        jd_applied = []
        for (brand, model), price in JD_PRICES.items():
            p = db.query(Product).filter(Product.brand == brand, Product.model == model).first()
            if p:
                p.price_low = p.price_high = float(price)
                jd_applied.append((p.id, brand, model, price))
            else:
                print(f'警告: JD价格未匹配产品 {brand} {model}')

        # ===== 问题2a：价格区间修正（多源核实的区间，区别于 JD 单一精确价） =====
        range_applied = []
        for (brand, model), (low, high) in PRICE_RANGES.items():
            p = db.query(Product).filter(Product.brand == brand, Product.model == model).first()
            if p:
                p.price_low, p.price_high = low, high
                range_applied.append((p.id, brand, model, low, high))
            else:
                print(f'警告: 价格区间未匹配产品 {brand} {model}')

        # ===== 问题2b：价格区间修正（只处理颠倒/无数据，保留合法区间） =====
        # 旧逻辑把合法区间（low < high）取中值整到 10 元，摧毁区间信息，已废弃。
        # 现在只修 price_low > price_high 的颠倒；price_low=price_high=0 无数据不猜测；单边为 0 的残缺数据保持原样。
        price_fixed = 0
        for p in db.query(Product).all():
            low, high = p.price_low or 0, p.price_high or 0
            if low == high:
                continue  # 无数据(0,0)或已确定价格（含 JD 精确价），保持不动
            if low > 0 and high > 0 and low > high:
                # 区间颠倒 → 交换修正
                p.price_low, p.price_high = high, low
                price_fixed += 1
            # 其余情况（合法区间 low<high）保持不动

        # ===== 问题3：补充/修正维度参数 =====
        dims_applied = 0
        for brand, model, updates in DIMS_FIX:
            p = db.query(Product).filter(Product.brand == brand, Product.model == model).first()
            if not p:
                print(f'警告: 参数补充未匹配产品 {brand} {model}')
                continue
            # 注意：不能先取 p.dimensions 再原地 update —— 那会修改 SQLAlchemy
            # 记录的旧值对象，重新赋值后新旧相等，commit 时不会发出 UPDATE。
            # 必须直接构造新 dict 再赋值。
            p.dimensions = {**(p.dimensions or {}), **updates}
            dims_applied += 1

        db.commit()

        # ===== 统计 =====
        remaining = (
            db.query(Product).filter(Product.model == '').count()
        )
        total = db.query(Product).count()
        print(f'== 修复完成 ==')
        print(f'恢复被覆盖型号: {restored} 个')
        print(f'清单型号补全: {applied} 个 (冲突跳过 {len(conflicted)} 个: {", ".join(conflicted[:10])}...)')
        print(f'通用型号补全: {len(generic)} 个')
        print(f'删除脏数据产品: {len(deleted)} 个 {deleted}')
        print(f'JD精确价格: {len(jd_applied)} 个 {jd_applied}')
        print(f'价格区间修正: {len(range_applied)} 个 {range_applied}')
        print(f'价格颠倒修正: {price_fixed} 个')
        print(f'维度参数补充: {dims_applied} 个产品')
        print(f'剩余缺型号: {remaining}')
        print(f'产品总数: {total}')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
