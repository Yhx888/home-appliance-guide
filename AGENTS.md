# 全国家电选购指南 — 全栈项目

覆盖 17 品类（+ 4 专题子页）的家电选购指南。前端支持**双模式**：本地 FastAPI 后端 + GitHub Pages 静态托管。数据 448 产品，经网络调研（web_research）+ 规则填充 + 多方核验校对。

---

## 架构

```
home-appliance-guide/
  index.html          # 前端页面（HTML+CSS+JS 全内联，支持双模式）
  data.json           # 静态数据文件（GitHub Pages 用，由 export_static_data.py 导出）
  backend/
    main.py           # FastAPI 入口（root() 返回 index.html + API，无 /static 挂载）
    database.py       # 数据库模型定义（SQLite）
    schemas.py        # Pydantic 请求/响应模型
    routers.py        # API 路由
    scorer.py         # 加权评分排序引擎（价格由产品列承载）
    seed_data.py      # 数据迁移：从 index.html 解析写入数据库（支持 k 单位、rowspan 展开、多表解析）
    expand_data.py    # 数据扩充：网络调研（web_research）数据批量补充（逐条去重）
    enrich_data.py    # 数据富化：规则填补缺失维度值
    fix_data.py       # 数据修复：补型号 + JD 价格 + 参数修正（保留价格区间）
    fix_verified_data.py   # 核验修复：官方/多源核验后修正已知数据错误
    add_new_models.py      # 博主主推新款入库（仅写入已核验参数/价格）
    update_verified_prices.py  # 京东浏览器实测国补后价格写库
    apply_scoring_changes.py   # 评分变更：价格维度入分 + 主观维度降权
    export_static_data.py  # 导出 data.json 供 GitHub Pages 使用
    scrapers/
      base.py           # 采集调度器：低频限速 + 失败退避 + 统一落库
      jd.py             # 京东数据采集（占位实现，未启用）
      jd_union.py       # 京东联盟 API（需 AppKey/Secret，未配置时跳过）
      browser.py        # playwright 浏览器补采（京东/苏宁价格 + 渲染页规格）
      energy_label.py   # 中国能效/水效标识备案查询（半自动）
      manufacturer.py   # 厂商官网规格表采集（低频）
      verify.py         # 多方核验校对引擎 + 质量报告（默认只读，--apply 写回）
    tests/
      test_scorer_price.py  # 价格评分/权重/枚举映射单元测试
    app.db           # SQLite 数据库（不提交 git，448 产品）
  AGENTS.md           # AI 工作上下文（本文件，项目索引）
  SCHEMA.md           # 数据规范（品类维度定义、枚举映射、质量规则）
  PLAN.md             # 目标模式执行提示词
```

---

## 规范文件体系

| 文件 | 职责 | 何时查阅 |
|------|------|---------|
| **AGENTS.md**（本文件） | 项目索引、快速导航 | 每次任务开始 |
| [SCHEMA.md](SCHEMA.md) | 17 品类维度定义、枚举映射、质量规则 | 修改数据结构 |
| [FRONTEND.md](FRONTEND.md) | 前端架构、组件层次、JS 函数索引、CSS 变量 | 修改前端 |
| [BACKEND.md](BACKEND.md) | 后端 API、数据库模型、评分引擎、数据管道 | 修改后端 |
| [WORKFLOW.md](WORKFLOW.md) | Git 规则、核验清单、Bug 修复流程、数据变更流程 | 执行操作 |
| [PLAN.md](PLAN.md) | 目标模式执行提示词 | 从头构建 |

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r backend\requirements.txt

# 2. 初始化数据管道（有严格顺序依赖，后一步依赖前一步产物，不可跳步）
python -m backend.seed_data        # 从 index.html 解析初始数据
python -m backend.expand_data      # 网络调研数据批量补充（扩充产品数）
python -m backend.enrich_data      # 规则填补缺失维度值
python -m backend.fix_data         # 补型号 + 价格修正
python backend\fix_verified_data.py         # 核验修复（官方核验后）
python backend\add_new_models.py            # 新款入库（可选）
python backend\update_verified_prices.py    # 京东实测国补后价格写库（可选）
python backend\apply_scoring_changes.py     # 价格维度入分 + 权重调整（一次性）

# 3. 启动后端
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 4. 数据变更后重新导出（每次数据变更后必须运行）
python backend\export_static_data.py

# 5. 校对报告（默认只读，--apply 才写回）
python -m backend.scrapers.verify
```

---

## 数据统计（当前，验收口径）

| 指标 | 值 |
|------|-----|
| 品类数 | 17 |
| 产品数 | 448 |
| 维度定义 | 112（96 + 16 个价格_low，cat-8 保留 价格_全屋_万） |
| 维度填充率 | 97.3%（verify 报告口径，价格维度按产品列统计） |
| 数据点 | 2610+ 组（web_research / manufacturer_html / jd_html 浏览器核验） |
| data.json | 428 KB（含 scores、price_collected_at、needs_review） |

置信度分布（verify 报告）：中 0.5~0.9 = 1600（84.0%）、低 0.3~0.5 = 219（11.5%）、极低 <0.3 = 84（4.4%）、高 ≥0.9 = 1、缺失 0。

价格说明：`price_low` 为浏览器实测国补后/到手价（20 款已核验），`price_high` 为原价；价格参与综合评分（权重 50）。需人工核查产品（当前 1 款：宫菱 MARS）默认排最后。

---

## 部署

- **本地**：`http://localhost:8000`（需启动后端）
- **GitHub Pages**：`https://yhx888.github.io/home-appliance-guide/`（静态 data.json）
- Git 代理：`127.0.0.1:7897`
- 禁止使用：`webfetch`
