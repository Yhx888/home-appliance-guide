"""API 路由"""
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Category, Dimension, Product
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

    # 解析权重
    weights_dict = {}
    if weights:
        try:
            weights_dict = json.loads(weights)
        except (json.JSONDecodeError, TypeError):
            pass

    # 筛选
    query = db.query(Product).filter(Product.category_id == category.id)
    if brands:
        brand_list = [b.strip() for b in brands.split(",") if b.strip()]
        if brand_list:
            query = query.filter(Product.brand.in_(brand_list))
    if price_min > 0:
        query = query.filter(Product.price_high >= price_min)
    if price_max > 0:
        query = query.filter(Product.price_low <= price_max)

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    # 计算得分
    scorer = Scorer(db)
    product_list = []
    for p in products:
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

    # 排序
    if sort_key:
        reverse = sort_dir == "desc"
        product_list.sort(key=lambda x: (
            x.dim_scores.get(sort_key, ProductDim(normalized=0, weight=0)).normalized
            if sort_key in x.dim_scores
            else x.total_score
        ), reverse=reverse)
    else:
        product_list.sort(key=lambda x: x.total_score, reverse=True)

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



