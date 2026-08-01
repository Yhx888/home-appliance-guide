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
价格单一事实源为产品列 `price_low` / `price_high`，不入 dimensions JSON。
**v2 已恢复价格维度**：cat-1~cat-7、cat-9~cat-17 各含 `价格_low` 维度（weight=50，
higher_better=false），经 `PRICE_DIM_KEYS` 从产品列读取参与归一化与加权（0 视为无价格）。
cat-8 保留 `价格_全屋_万` / `风管机3匹_元` 业务维度。
`price_low` 为浏览器实测的国补后/到手价，`price_high` 为原价；更新后打 `price_collected_at`。

### 默认排序规则
1. 需人工核查产品（任一维度 data_points 被 verify 标记 manual_review_needed）排最后
2. 通用款（model 含"通用款"）次之
3. 具体型号按综合分降序

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
| `fix_verified_data.py` | 核验修复：小米508容量/双系统/嵌入深度、H5Pro价格精度、白泽Max RO膜寿命、洗衣机容量1010→10 | 官方参数核验后 |
| `add_new_models.py` | 博主主推新款入库（17 款，仅写入已核验参数/价格，维度带 data_points 来源） | 新款补充 |
| `update_verified_prices.py` | 京东浏览器实测国补后价格写库（price_low=到手价，price_high=原价） | 价格核验后 |
| `apply_scoring_changes.py` | 评分变更：16 品类插入价格维度 + 满意度/份额降权至 10 | 评分逻辑调整 |
| `export_static_data.py` | 导出 `data.json`（含每产品 `scores` 归一化分，4 位小数）供 GitHub Pages | **每次数据变更后必须运行** |

---

## scrapers/ 模块

| 文件 | 功能 |
|------|------|
| `base.py` | 采集调度器：单线程低频（2~5 秒间隔、每品类每日 ≤50）、失败指数退避、统一写 data_points |
| `jd.py` | 京东规格表 HTML 解析（搜索接口占位；价格走 jd_union / browser） |
| `jd_union.py` | 京东联盟 API（需 JD_UNION_APPKEY/SECRET，未配置时 dry-run 跳过） |
| `browser.py` | playwright 浏览器补采：京东/苏宁搜索页价格 + 渲染页规格兜底 |
| `energy_label.py` | 中国能效/水效标识备案查询（JS 渲染，半自动 + 浏览器核验） |
| `manufacturer.py` | 厂商官网采集（OFFICIAL_PAGES 清单 + 复用 data_sources 官网 URL，低频抓取规格表） |
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
| 产品数 | 448 |
| 维度定义 | 112（96 + 16 个价格_low，cat-8 保留 价格_全屋_万） |
| 维度填充率 | 97.3%（verify 报告口径，价格维度按产品列统计） |
| 数据点 | 2610+ 组（web_research / manufacturer_html / jd_html 浏览器核验） |
| data.json | 含 scores、price_collected_at、needs_review 字段 |

### 置信度分布（verify 报告）

| 区间 | 数量 | 占比 |
|------|-----:|-----:|
| 高 ≥0.9 | 1 | 0.1% |
| 中 0.5~0.9 | 1600 | 84.0% |
| 低 0.3~0.5 | 219 | 11.5% |
| 极低 <0.3 | 84 | 4.4% |
| 缺失 | 0 | 0% |
