"""数据库模型定义 — SQLAlchemy ORM"""
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

# 基于本文件位置派生绝对路径，避免依赖启动时的 CWD（Windows 盘符路径转 URL 用正斜杠）
DATABASE_URL = f"sqlite:///{(Path(__file__).resolve().parent / 'app.db').as_posix()}"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Category(Base):
    """品类元信息"""
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="品类中文名")
    slug = Column(String(50), unique=True, nullable=False, comment="品类标识符")
    icon = Column(String(10), default="", comment="图标 emoji")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, server_default=func.now())

    dimensions = relationship("Dimension", back_populates="category", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Dimension(Base):
    """品类维度定义"""
    __tablename__ = "dimensions"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    dim_key = Column(String(50), nullable=False, comment="维度标识符，如 风量_m3")
    label = Column(String(50), nullable=False, comment="中文显示名")
    type = Column(String(20), nullable=False, default="float", comment="数据类型: float/enum/bool/text")
    unit = Column(String(30), default="", comment="单位")
    higher_better = Column(Boolean, default=True, comment="是否越大越好")
    default_weight = Column(Integer, default=50, comment="默认权重 0-100")
    enum_values = Column(Text, default="", comment="枚举值列表 JSON 字符串")

    category = relationship("Category", back_populates="dimensions")


class Product(Base):
    """产品数据"""
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    brand = Column(String(50), nullable=False, comment="品牌")
    model = Column(String(100), default="", comment="型号")
    price_low = Column(Float, default=0, comment="最低价")
    price_high = Column(Float, default=0, comment="最高价")
    dimensions = Column(JSON, default=dict, comment="维度值 JSON {dim_key: value}")
    rating = Column(Float, default=0, comment="综合评分")
    created_at = Column(DateTime, server_default=func.now())

    category = relationship("Category", back_populates="products")
    data_points = relationship("DataPoint", back_populates="product", cascade="all, delete-orphan")


class DataSource(Base):
    """数据来源"""
    __tablename__ = "data_sources"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(30), nullable=False, comment="平台: jd/manufacturer/xhs")
    url = Column(Text, default="", comment="来源 URL")
    method = Column(String(20), default="html", comment="采集方式: html/vision")
    collected_at = Column(DateTime, server_default=func.now())

    data_points = relationship("DataPoint", back_populates="source", cascade="all, delete-orphan")


class DataPoint(Base):
    """单源原始数据点"""
    __tablename__ = "data_points"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    dimension_key = Column(String(50), nullable=False, comment="维度标识符")
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    raw_value = Column(String(200), default="", comment="原始文本值")
    numeric_value = Column(Float, nullable=True, comment="解析后的数值")
    confidence = Column(Float, default=0.5, comment="置信度")
    status = Column(String(20), default="pending", comment="状态: pending/verified/disputed/manual_review_needed")

    product = relationship("Product", back_populates="data_points")
    source = relationship("DataSource", back_populates="data_points")


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
