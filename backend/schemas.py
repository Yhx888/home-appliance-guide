"""Pydantic 请求/响应模型"""
from typing import Optional
from pydantic import BaseModel


class DimensionOut(BaseModel):
    """维度定义输出"""
    dim_key: str
    label: str
    type: str
    unit: str = ""
    higher_better: bool = True
    default_weight: int = 50
    enum_values: list[str] = []

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    """品类输出"""
    id: int
    name: str
    slug: str
    icon: str = ""
    sort_order: int = 0
    product_count: int = 0
    dimensions: list[DimensionOut] = []

    class Config:
        from_attributes = True


class ProductQuery(BaseModel):
    """产品查询参数"""
    brands: str = ""
    price_min: float = 0
    price_max: float = 0
    sort_key: str = ""
    sort_dir: str = "desc"
    weights: str = ""  # JSON 字符串
    page: int = 1
    page_size: int = 50


class ProductDim(BaseModel):
    """单维度的标准化得分"""
    raw: float | str | bool | None = None
    normalized: float = 0
    weight: int = 50


class ProductOut(BaseModel):
    """产品输出"""
    id: int
    category_id: int
    brand: str
    model: str = ""
    price_low: float = 0
    price_high: float = 0
    dimensions: dict = {}
    rating: float = 0
    dim_scores: dict[str, ProductDim] = {}  # 标准化得分
    total_score: float = 0
    needs_review: bool = False  # 人工核查标记（占位型号等）
    data_incomplete: bool = False  # 维度缺失权重 ≥30%，评分不可信

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    """产品列表输出（含分页）"""
    total: int
    page: int
    page_size: int
    products: list[ProductOut]
