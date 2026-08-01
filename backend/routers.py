"""API 路由"""
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Category, Dimension, Product, DataPoint
from backend.schemas import CategoryOut, DimensionOut, ProductOut, ProductListOut, ProductDim
from backend.scorer import Scorer

router = APIRouter()


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    """品类列表 + 各品类维度定义"""
    categories = db.query(Category).order_by(Category.sort_order).all()

    result = []
    for cat in categories:
        dims = db.query(Dimension).filter(Dimension.category_id == cat.id).all()
        dim_out = []
        for d in dims:
            enum_vals = []
            if d.enum_values:
                try:
                    enum_vals = json.loads(d.enum_values)
                except (json.JSONDecodeError, TypeError):
                    enum_vals = []
            dim_out.append(DimensionOut(
                dim_key=d.dim_key,
                label=d.label,
                type=d.type,
                unit=d.unit or "",
                higher_better=d.higher_better if d.higher_better is not None else True,
                default_weight=d.default_weight or 50,
                enum_values=enum_vals,
            ))
        result.append(CategoryOut(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            icon=cat.icon or "",
            sort_order=cat.sort_order or 0,
            product_count=db.query(Product).filter(Product.category_id == cat.id).count(),
            dimensions=dim_out,
        ))
    return result


@router.get("/categories/{slug}/products", response_model=ProductListOut)
def list_products(
    slug: str,
    brands: str = Query("", description="品牌筛选，逗号分隔"),
    price_min: float = Query(0),
    price_max: float = Query(0),
    sort_key: str = Query("", description="排序维度 key"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    weights: str = Query("", description="权重 JSON"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """某品类产品列表，支持筛选排序"""
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="品类不存在")

    # 获取该品类所有产品（用于全局归一化）
    all_products = db.query(Product).filter(Product.category_id == category.id).all()

    # 获取维度定义
    dims = db.query(Dimension).filter(Dimension.category_id == category.id).all()
    dim_map = {d.dim_key: d for d in dims}

    # 收集全局维度值范围
    all_dim_values = Scorer.collect_all_dim_values(all_products, dim_map)

    # 解析权重：必须 JSON 对象，值必须 0-100 数字
    weights_dict = {}
    if weights:
        try:
            parsed = json.loads(weights)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="weights 必须是合法 JSON 对象")
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="weights 必须是 JSON 对象")
        for k, v in parsed.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise HTTPException(status_code=400, detail=f"weights 中 {k} 必须是 0-100 的数字")
            if not 0 <= v <= 100:
                raise HTTPException(status_code=400, detail=f"weights 中 {k} 超出 0-100 范围")
        weights_dict = parsed

    # 筛选（price_min/price_max = 0 视为未过滤，不排除价格未知产品）
    query = db.query(Product).filter(Product.category_id == category.id)
    if brands:
        brand_list = [b.strip() for b in brands.split(",") if b.strip()]
        if brand_list:
            query = query.filter(Product.brand.in_(brand_list))
    if price_min > 0:
        query = query.filter(Product.price_high >= price_min)
    if price_max > 0:
        query = query.filter(Product.price_low <= price_max)

    # 排序键校验：仅允许本品类维度 key 或 total_score
    if sort_key and sort_key != "total_score" and sort_key not in dim_map:
        raise HTTPException(status_code=400, detail=f"未知排序键: {sort_key}")

    # 全量筛选 → 计算得分 → 排序 → 切片分页（数百行规模全量取成本可忽略，保证跨页有序）
    filtered = query.all()
    total = len(filtered)

    # 需人工核查的产品（任一维度被 verify 标记 manual_review_needed）默认排后
    review_ids = {
        row[0] for row in db.query(Product.id)
        .join(DataPoint, DataPoint.product_id == Product.id)
        .filter(Product.category_id == category.id, DataPoint.status == "manual_review_needed")
        .distinct()
        .all()
    }

    scorer = Scorer(db)
    product_list = []
    for p in filtered:
        scores = scorer.calc_product_scores(p, dim_map, weights_dict, all_dim_values)
        total_score = Scorer.calc_total_score(scores)
        product_list.append(ProductOut(
            id=p.id,
            category_id=p.category_id,
            brand=p.brand,
            model=p.model or "",
            price_low=p.price_low or 0,
            price_high=p.price_high or 0,
            dimensions=p.dimensions or {},
            rating=p.rating or 0,
            dim_scores=scores,
            total_score=total_score,
        ))

    # 排序：单维度按归一化分（缺失维度恒有 normalized=0 条目，按 0 分参与排序），否则按综合分
    # 方向：asc/desc 是原始值语义；normalized 对 higher_better=false 维度（价格/噪音等）已反转，需取反
    if sort_key and sort_key != "total_score":
        dim_def = dim_map.get(sort_key)
        reverse = (sort_dir == "desc") != (dim_def is not None and not dim_def.higher_better)
        product_list.sort(key=lambda x: x.dim_scores.get(sort_key, ProductDim(normalized=0, weight=0)).normalized, reverse=reverse)
    else:
        # 默认综合排序：需人工核查 → 通用款 → 具体型号按综合分降序
        product_list.sort(
            key=lambda x: (
                1 if x.id in review_ids else 0,
                1 if "通用款" in (x.brand + x.model) else 0,
                -x.total_score,
            )
        )

    # 切片分页
    start = (page - 1) * page_size
    product_list = product_list[start:start + page_size]

    return ProductListOut(
        total=total,
        page=page,
        page_size=page_size,
        products=product_list,
    )


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """单产品详情"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 获取品类维度
    dims = db.query(Dimension).filter(Dimension.category_id == product.category_id).all()
    dim_map = {d.dim_key: d for d in dims}

    # 获取同品类所有产品用于全局归一化
    all_products = db.query(Product).filter(Product.category_id == product.category_id).all()
    all_dim_values = Scorer.collect_all_dim_values(all_products, dim_map)

    scorer = Scorer(db)
    scores = scorer.calc_product_scores(product, dim_map, {}, all_dim_values)
    total_score = Scorer.calc_total_score(scores)

    return ProductOut(
        id=product.id,
        category_id=product.category_id,
        brand=product.brand,
        model=product.model or "",
        price_low=product.price_low or 0,
        price_high=product.price_high or 0,
        dimensions=product.dimensions or {},
        rating=product.rating or 0,
        dim_scores=scores,
        total_score=total_score,
    )


@router.get("/categories/{slug}/dimensions", response_model=list[DimensionOut])
def list_dimensions(slug: str, db: Session = Depends(get_db)):
    """某品类维度定义列表"""
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="品类不存在")

    dims = db.query(Dimension).filter(Dimension.category_id == category.id).all()
    result = []
    for d in dims:
        enum_vals = []
        if d.enum_values:
            try:
                enum_vals = json.loads(d.enum_values)
            except (json.JSONDecodeError, TypeError):
                enum_vals = []
        result.append(DimensionOut(
            dim_key=d.dim_key,
            label=d.label,
            type=d.type,
            unit=d.unit or "",
            higher_better=d.higher_better if d.higher_better is not None else True,
            default_weight=d.default_weight or 50,
            enum_values=enum_vals,
        ))
    return result
