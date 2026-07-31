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
  AGENTS.md           # AI 工作上下文
  SCHEMA.md           # 数据规范（品类维度定义、枚举映射、质量规则）
  PLAN.md             # 目标模式执行提示词
```

---

## 后端

| 文件 | 职责 |
|------|------|
| `main.py` | FastAPI 实例、CORS、静态文件挂载 |
| `database.py` | SQLAlchemy 引擎、会话工厂、全部 ORM 模型 |
| `schemas.py` | Pydantic 模型：CategoryOut、DimensionOut、ProductOut、ProductQuery |
| `routers.py` | 路由：`/api/categories`、`/api/categories/{slug}/products`、`/api/products/{id}` |
| `scorer.py` | `Scorer` 类，标准化得分 + 加权综合分计算 |
| `seed_data.py` | 从 index.html 解析现有数据，执行初始化写入 |
| `expand_data.py` | 数据扩充：网络调研数据批量补充产品 |
| `enrich_data.py` | 数据富化：填补维度值 + 创建双数据源 |
| `fix_data.py` | 数据修复：补型号 + JD 价格 + 参数修正 |
| `export_static_data.py` | 导出 data.json 供 GitHub Pages 使用 |
| `scrapers/jd.py` | 京东商品参数采集：L1 HTML 解析 + L2 截图多模态兜底 |
| `scrapers/manufacturer.py` | 厂商官网参数采集 |
| `scrapers/verify.py` | 多源校对：数值核对 → 视觉核验回路 → 质量报告 |

**启动命令**（在项目根目录执行）：
```
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
访问 `http://localhost:8000` 即可使用。

---

## 数据库（SQLite）

5 个核心表：

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `categories` | 品类元信息 | id, name, slug, icon |
| `dimensions` | 品类维度定义（每品类独立注册） | id, category_id(FK), dim_key, label, type, unit, higher_better, default_weight |
| `products` | 产品数据 | id, category_id(FK), brand, model, price_low, price_high, dimensions(JSON), rating |
| `data_sources` | 数据来源记录 | id, platform, url, collected_at |
| `data_points` | 单源原始数据点（用于校对） | id, product_id(FK), dimension_key, source_id(FK), raw_value, numeric_value, confidence |

---

## API

| 端点 | 参数 | 说明 |
|------|------|------|
| `GET /api/categories` | — | 品类列表 + 各品类维度定义 |
| `GET /api/categories/{slug}/products` | `brands, price_min/max, sort_key, sort_dir, weights` | 排序筛选后的产品列表 |
| `GET /api/products/{id}` | — | 单产品详情 + 数据来源 |
| `GET /api/categories/{slug}/dimensions` | — | 某品类维度定义列表 |

---

## 工具使用规则

| 工具 | 用途 | 说明 |
|------|------|------|
| **Kimi WebBridge** | 浏览器交互：打开网页、截图、点击、滚动 | 用于京东/厂商页面导航和复杂交互操作 |
| **playwright** | 自动浏览器截图、批量页面操作 | 配合 `@observer` 做多模态规格参数提取 |
| **AnySearch** | 网络搜索调研 | 搜索产品参数、比价信息、品牌资料 |
| Bash / pip | 后端依赖安装、启动服务 | — |
| Read / Write / Edit | 文件操作 | 修改 index.html 和 backend/ 代码 |
| Glob / Grep | 文件/内容搜索 | 快速定位代码 |

**禁止**：`webfetch`（一律不用）

---

## 数据采集流程

```
1. 确定品类和品牌列表（每品类 ≥8 品牌）
2. 对每个品牌:
   a. AnySearch 搜索该品牌该品类的热门产品型号
   b. Kimi WebBridge / playwright 打开京东搜索结果页
   c. 尝试直接读取页面 HTML 中的规格参数表
   d. 如果 HTML 拿不到参数，截图规格区域 + @observer 视觉提取
   e. 将提取到的数据写入 data_points + data_sources
3. 厂商官网做同样流程补充
4. 运行 verify.py 校对，触发视觉核验回路修复低置信度项
```

---

## 数据校对流程

```
数值核对 → 每(product, dimension) 分组 data_points
  ├─ 多源一致(偏差<15%) → 置信度≥0.9，直接写入 products.dimensions
  ├─ 多源偏差>20% → 标记"需人工核查"
  └─ 单源 → 置信度0.5，标记"待补充"

视觉核验（对标记项）：
  → Kimi WebBridge 打开产品页 → 截图参数区 → @observer 提取
  → 新 data_point 加入 → 重新校对
```

---

## 数据完成标准（当前状态）

- [x] 品类数 = 17
- [x] 每品类 ≥8 品牌（小众品类 ≥5）
- [x] 总产品数 ≥500（实际 493，7 条脏数据已清理）
- [x] 关键维度填充率 ≥80%（实际 97.8%）
- [x] 双源覆盖产品比例 ≥70%（实际 100%）
- [x] 核心品牌（美的/海尔/格力等）100% 覆盖
- [x] 无"需人工核查"未解决项（0 条）
- [x] API 全部正常响应
- [x] `http://localhost:8000` 前端可用，筛选排序交互正常

---

## 前端规范

- CSS 变量定义在 `:root`，直接使用变量名
- 卡片结构：`.section > .card > .card-header + .card-body`，折叠由 `toggleCard()` 驱动
- 多维度对比表：`table.dim-table-dynamic`，横向维度标签为列头、纵向每行一个产品（品牌+型号）
- 筛选面板：`.filter-panel` 在 dim-table 上方，包含：
  - 优先级标签（多选）：按 17 品类各自的核心维度预设标签按钮，多选后按均分权重综合排序
  - 品牌多选：标签样式，点击切换
  - 价格区间：两个输入框
  - 应用/重置按钮
- 表格数据动态渲染：`renderDimTable(products, dims)` 替代静态 table
- 维度值颜色分级：float 维度按分位数（前25%绿、中50%黄、后25%红）着色
- 综合得分改为星级：≥85=★★★★★, ≥70=★★★★☆, ≥55=★★★☆☆, ≥40=★★☆☆☆, <40=★☆☆☆☆
- 导航切换：`switchTab(id)` 不变，切到品类时自动展开对比卡片并调用 API
- 搜索：`doSearch(query)` 保留本地搜索逻辑
- **双模式**：本地（localhost）走 API 后端；GitHub Pages 自动检测并读取 `data.json` 静态运行

---

## GitHub Pages

- 地址：`https://yhx888.github.io/home-appliance-guide/`
- 静态数据文件：`data.json`（289KB，含 17 品类完整数据）
- 每次数据修改后需重新运行 `python backend\export_static_data.py` 导出 data.json
- CDN 有缓存延迟，push 后 1-2 分钟生效，强制刷新（Ctrl+F5）可绕过

---

## Git 规则

### 基础配置
- 代理：`127.0.0.1:7897`
- 数据库文件 `backend/app.db` 不提交（已在 .gitignore 中）
- `__pycache__/` 目录不提交

### 提交策略
每次完成一个有意义的里程碑后立即提交，包括：

| 时机 | 示例提交信息 |
|------|------------|
| 每个 Phase 完成后 | `Phase 1: 后端骨架搭建完成` |
| 关键功能完成 | `实现加权排序引擎` |
| 数据更新 | `新增抽油烟机品类数据（9品牌45产品）` |
| Bug 修复 | `修复筛选面板价格区间滑块不响应的问题` |

### 提交规范
- 提交信息用中文，简洁概括改动内容
- 提交前运行 `git status` 检查待提交文件，确保只包含本阶段改动的文件
- 不要混合多个不相关的改动到同一个提交
- 提交格式：`git add <文件>； git commit -m "信息"`（文件逐个添加，不加 `-A` 以防误加 db 文件）
- **每次完成修改后必须立即 `git push`，同步到 GitHub Pages**

### 分支建议
- 主分支 `master` 保持稳定
- 每个大阶段可以在主分支上直接 commit，不做复杂分支管理
- 如遇到实验性改动需要来回尝试，先用 `git stash` 暂存再继续

### 提交前检查清单
- [ ] `git status` 确认没有意外包含 `app.db` 或 `__pycache__`
- [ ] `git diff --cached` 确认改动的文件符合预期
- [ ] 代码可以正常运行（后端不报错）

### Bug 修复工作流
- **每次修完 bug 后，必须立即更新 AGENTS.md**（反映修复内容、新增的注意事项）
- 每次任务开始时，对照下方核验清单逐项检查完成情况

### 任务核验清单
| 检查项 | 说明 |
|--------|------|
| 代码已提交 | `git status` 干净，commit 信息清晰 |
| 已 push 到 GitHub | `git push origin master` 执行成功 |
| AGENTS.md 已更新 | 修复内容、架构变化已写入 |
| 数据有变化 | 重新运行 `python backend\export_static_data.py` |
| GitHub Pages 已验证 | 等 CDN 传播后用浏览器确认页面正常 |
