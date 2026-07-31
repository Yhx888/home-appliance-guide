# 全国家电选购指南 — 全栈项目

覆盖 17 品类（+ 4 专题）的家电选购指南。前端支持**双模式**：本地 FastAPI 后端 + GitHub Pages 静态托管。数据 493 产品，维度填充率 97.8%，双源覆盖 100%。

---

## 架构

```
home-appliance-guide/
  index.html          # 前端页面（HTML+CSS+JS 全内联，支持双模式）
  data.json           # 静态数据文件（GitHub Pages 用，289KB）
  backend/
    main.py           # FastAPI 入口（serve 静态文件 + API）
    database.py       # 数据库模型定义（SQLite）
    schemas.py        # Pydantic 请求/响应模型
    routers.py        # API 路由
    scorer.py         # 加权评分排序引擎
    seed_data.py      # 数据迁移：从 index.html 解析写入数据库
    expand_data.py    # 数据扩充：网络调研数据批量补充
    enrich_data.py    # 数据富化：填补维度值 + 创建双数据源
    fix_data.py       # 数据修复：补型号 + JD 价格 + 参数修正
    export_static_data.py  # 导出 data.json 供 GitHub Pages 使用
    scrapers/
      jd.py             # 京东数据采集（HTML 解析 + 截图多模态）
      manufacturer.py   # 厂商官网数据采集
      verify.py         # 多方核验校对引擎 + 质量报告
    app.db           # SQLite 数据库（不提交 git，493 产品）
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
# 后端
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 数据变更后重新导出
python backend\export_static_data.py

# 校对报告
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
| 数据点 | 10,752 |

---

## 部署

- **本地**：`http://localhost:8000`（需启动后端）
- **GitHub Pages**：`https://yhx888.github.io/home-appliance-guide/`（静态 data.json）
- Git 代理：`127.0.0.1:7897`
- 禁止使用：`webfetch`
