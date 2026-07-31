# 全国家电选购指南 — 全栈项目

覆盖 17 品类（+ 4 专题子页）的家电选购指南。前端支持**双模式**：本地 FastAPI 后端 + GitHub Pages 静态托管。数据 490 产品，经网络调研（web_research）+ 规则填充 + 多方核验校对。

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
    export_static_data.py  # 导出 data.json 供 GitHub Pages 使用
    scrapers/
      jd.py             # 京东数据采集（占位实现，未启用）
      manufacturer.py   # 厂商官网数据采集（占位实现，未启用）
      verify.py         # 多方核验校对引擎 + 质量报告（默认只读，--apply 写回）
    app.db           # SQLite 数据库（不提交 git，490 产品）
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
| 产品数 | 490 |
| 维度定义 | 96（128 - 32 价格键，cat-8 保留 价格_全屋_万） |
| 维度填充率 | 98.3%（verify 报告口径 2729/2775；enrich 口径 97.9%） |
| 数据点 | 2870 条（全部 web_research/search，单一来源） |
| data.json | 352 KB（含每产品 scores 归一化分） |

置信度分布（verify 报告）：中 0.5~0.9 = 885（87.6%）、低 0.3~0.5 = 100（9.9%）、极低 <0.3 = 25（2.5%）、高 ≥0.9 = 0、缺失 0。

---

## 部署

- **本地**：`http://localhost:8000`（需启动后端）
- **GitHub Pages**：`https://yhx888.github.io/home-appliance-guide/`（静态 data.json）
- Git 代理：`127.0.0.1:7897`
- 禁止使用：`webfetch`
