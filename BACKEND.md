# 后端开发规范

FastAPI + SQLite 后端，root() 返回 index.html + RESTful API。

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
| `main.py` | FastAPI 应用、CORS、root() 返回 index.html（无 /static 挂载）、启动时 init_db |
| `database.py` | SQLAlchemy ORM 模型定义（5 表） |
| `schemas.py` | Pydantic 请求/响应模型 |
| `routers.py` | 4 个 API 端点 |
| `scorer.py` | `Scorer` 类：标准化得分 + 加权综合分（价格由产品列承载） |

---

## API 端点

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/categories` | — | 品类列表 + 各品类维度定义 |
| GET | `/api/categories/{slug}/products` | `brands`, `price_min`, `price_max`, `sort_key`, `sort_dir`, `weights`, `page`, `page_size` | 筛选排序后的产品列表 |
| GET | `/api/products/{id}` | — | 单产品详情 |
| GET | `/api/categories/{slug}/dimensions` | — | 品类维度定义列表 |

### list_products 行为

- **筛选**：`brands`（逗号分隔）；`price_min` / `price_max`（=0 视为未过滤，与产品价格区间有交集即命中）
- **排序键校验**：`sort_key` 仅允许本品类维度 key 或 `total_score`，非法值返回 **400**；`sort_dir` 仅 `asc`/`desc`（pattern 校验）
- **权重校验**：`weights` 必须是 JSON 对象、值必须为 0-100 的数字，否则返回 **400**
- **全量取 → 计算得分 → 排序 → 切片分页**：先对全部筛选结果逐条计算各维度 normalized 分与综合分，Python 层整体排序后再切片分页（跨页连续有序；数百行规模全量取成本可忽略）
- **排序方向**：单维度按 normalized 分排序，`asc`/`desc` 为原始值语义——`higher_better=false` 维度（价格/噪音等）的 normalized 分已反转，排序方向取反恢复原始值语义；不传 `sort_key` 时默认综合分降序
- 页面默认 `page_size=50`（上限 200），前端实际请求 `page_size=100`

---

## 数据库模型

```sql
categories (id, name, slug, icon, sort_order)
dimensions (id, category_id→categories, dim_key, label, type, unit, higher_better, default_weight, enum_values)
products   (id, category_id→categories, brand, model, price_low, price_high, dimensions=JSON, rating)
data_sources (id, platform, url, method, collected_at)   -- platform 当前实际为 web_research / search
data_points  (id, product_id→products, dimension_key, source_id→data_sources, raw_value, numeric_value, confidence, status)
```

- 数据库文件：`backend/app.db`（不提交 git）
- `products.dimensions` 为 JSON 字段：`{"风量_m3": 26.0, "静压_Pa": 975.0, ...}`，**不含价格键**（价格走产品列）
- **路径说明**：全部路径均基于 `Path(__file__)` 派生，任意 CWD 运行正确——`database.py` 的 `DATABASE_URL`、`export_static_data.py` 的 `OUTPUT_PATH`、`main.py` 的 index.html、`verify.py` 的包路径均不依赖启动目录

---

## 评分引擎（scorer.py）

### 归一化
- **float**：全局 min/max 归一化，`higher_better` 反转
- **enum**：硬编码映射表（`ENUM_SCORE_MAP`，22 组），找不到时按 enum_values 位置降序兜底
- **bool**：true=100, false=0

### 价格
价格单一事实源为产品列 `price_low` / `price_high`，不入 dimensions。批3 后价格维度已从维度定义移除（cat-8 的 `价格_全屋_万` / `风管机3匹_元` 为独立业务维度，保留），
`PRICE_DIM_KEYS = {"价格_low": "price_low", "价格_high": "price_high"}` 映射保留为兜底机制：若未来重新引入价格维度定义，自动从产品列读取参与归一化与加权（0 视为无价格）。

### 综合分
```python
total_score = Σ(normalized_i × weight_i) / Σ(weight_i)
```

---

## 数据管道脚本

按执行顺序（有严格顺序依赖，后一步依赖前一步产物，不可跳步）：

| 脚本 | 功能 | 何时运行 |
|------|------|---------|
| `seed_data.py` | 从 index.html 解析初始数据（支持 k 单位、rowspan 展开、多表解析；DIMENSIONS 不含价格键） | 首次初始化数据库 |
| `expand_data.py` | 网络调研（web_research）数据批量补充产品（逐条按 category_id+brand+model 去重，DataSource 按 platform+method 复用） | 需要扩充产品数量 |
| `enrich_data.py` | 规则填补缺失维度值（不产生 verified 数据） | 数据不完整时 |
| `fix_data.py` | 补型号 + 价格修正（只修 low>high 颠倒与 0=0 无数据情况，保留价格区间，无中值塌缩） | 数据错误修复 |
| `export_static_data.py` | 导出 `data.json`（含每产品 `scores` 归一化分，4 位小数）供 GitHub Pages | **每次数据变更后必须运行** |

---

## scrapers/ 模块

| 文件 | 功能 |
|------|------|
| `jd.py` | 京东商品采集（**占位实现，未启用**） |
| `manufacturer.py` | 厂商官网采集（**占位实现，未启用**） |
| `verify.py` | 多方校对引擎：数值核对 → 质量报告（argparse：默认只读，`--apply` 才写回） |

### 运行校对
```bash
python -m backend.scrapers.verify         # 只读质量报告（默认）
python -m backend.scrapers.verify --apply # 写回：多源一致的数值共识写入 products.dimensions
```
- 写回前校验维度 type：**enum/text 维度禁止数值写回**（避免把"一级"写成浮点数）
- 置信度只来自真实核验流程（`calculate_confidence` 多源公式聚合 data_points），无伪造估算

---

## 数据统计（当前，验收口径）

| 指标 | 值 |
|------|-----|
| 品类数 | 17 |
| 产品数 | 490 |
| 维度定义 | 96（128 - 32 价格键，cat-8 保留 价格_全屋_万） |
| 维度填充率 | 98.3%（verify 报告口径 2729/2775；enrich 口径 97.9%） |
| 数据点 | 2870 条（全部 web_research/search，单一来源） |
| data.json | 352 KB（含每产品 scores 归一化分） |

### 置信度分布（verify 报告）

| 区间 | 数量 | 占比 |
|------|-----:|-----:|
| 高 ≥0.9 | 0 | 0% |
| 中 0.5~0.9 | 885 | 87.6% |
| 低 0.3~0.5 | 100 | 9.9% |
| 极低 <0.3 | 25 | 2.5% |
| 缺失 | 0 | 0% |
