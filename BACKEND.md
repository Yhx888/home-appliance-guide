# 后端开发规范

FastAPI + SQLite 后端，serve 前端静态文件 + RESTful API。

---

## 启动

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
访问 `http://localhost:8000`，API 前缀 `/api`。

---

## 文件职责

| 文件 | 职责 |
|------|------|
| `main.py` | FastAPI 应用、CORS、静态文件挂载、启动事件 |
| `database.py` | SQLAlchemy ORM 模型定义（5 表） |
| `schemas.py` | Pydantic 请求/响应模型 |
| `routers.py` | 4 个 API 端点 |
| `scorer.py` | `Scorer` 类：标准化得分 + 加权综合分 |

---

## API 端点

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/categories` | — | 品类列表 + 各品类维度定义 |
| GET | `/api/categories/{slug}/products` | `brands`, `price_min`, `price_max`, `sort_key`, `sort_dir`, `weights`, `page`, `page_size` | 筛选排序后的产品列表 |
| GET | `/api/products/{id}` | — | 单产品详情 |
| GET | `/api/categories/{slug}/dimensions` | — | 品类维度定义列表 |

---

## 数据库模型

```sql
categories (id, name, slug, icon, sort_order)
dimensions (id, category_id→categories, dim_key, label, type, unit, higher_better, default_weight, enum_values)
products   (id, category_id→categories, brand, model, price_low, price_high, dimensions=JSON, rating)
data_sources (id, platform, url, method, collected_at)
data_points  (id, product_id→products, dimension_key, source_id→data_sources, raw_value, numeric_value, confidence, status)
```

- 数据库文件：`backend/app.db`（不提交 git）
- `products.dimensions` 为 JSON 字段：`{"风量_m3": 26.0, "静压_Pa": 975.0, ...}`

---

## 评分引擎（scorer.py）

### 归一化
- **float**：全局 min/max 归一化，`higher_better` 反转
- **enum**：硬编码映射表（`ENUM_SCORE_MAP`，22 组）
- **bool**：true=100, false=0

### 综合分
```python
total_score = Σ(normalized_i × weight_i) / Σ(weight_i)
```

---

## 数据管道脚本

按执行顺序：

| 脚本 | 功能 | 何时运行 |
|------|------|---------|
| `seed_data.py` | 从 index.html 解析初始数据 | 首次初始化数据库 |
| `expand_data.py` | 网络调研数据批量补充产品 | 需要扩充产品数量 |
| `enrich_data.py` | 填补缺失维度值 + 创建双数据源 | 数据不完整时 |
| `fix_data.py` | 补型号 + JD 价格 + 参数修正 | 数据错误修复 |
| `export_static_data.py` | 导出 `data.json` 供 GitHub Pages | **每次数据变更后必须运行** |

---

## scrapers/ 模块

| 文件 | 功能 |
|------|------|
| `jd.py` | 京东商品采集（HTML 解析 + 截图多模态兜底） |
| `manufacturer.py` | 厂商官网采集 |
| `verify.py` | 多方校对引擎：数值核对 → 视觉核验 → 质量报告 |

### 运行校对
```bash
python -m backend.scrapers.verify
```

---

## 数据统计（当前）

| 指标 | 值 |
|------|-----|
| 品类数 | 17 |
| 产品数 | 493 |
| 维度定义 | 128 |
| 维度填充率 | 97.8% |
| 双源覆盖 | 100% |
| 数据来源记录 | 7 |
| 数据点 | 10,752 |
