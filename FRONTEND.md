# 前端开发规范

全国家电选购指南前端以 `index.html` 为唯一入口，HTML+CSS+JS 全内联，支持双模式运行。

---

## 运行模式

| 模式 | 检测条件 | 数据来源 |
|------|---------|---------|
| **本地模式** | `hostname` 含 `localhost` 或 `127.0.0.1` | FastAPI 后端 `/api/*` |
| **静态模式** | 其他（GitHub Pages 等） | `data.json` 静态文件 |

`IS_STATIC` 变量控制分支，`fetchCategories` / `fetchProducts` 自动适配。

---

## 页面结构（SPA 双层路由）

| 视图 | URL hash | 内容 |
|------|----------|------|
| 主页（模块中心） | 无 | Hero + 搜索 + `#homeHub`（17 品类卡 + 5 专题入口），导航栏隐藏 |
| 品类子页 | `#cat-1`~`#cat-17` | 面包屑 + filter-panel + 对比表格 + 详情卡片 |
| 速查总览 | `#overview` | 聚合 `#overview` + `#overview-aftersale` + `#overview-tco` 三个 section |
| 专题子页 | `#topic-1` / `#topic-5` / `#topic-6` / `#topic-8` | 全屋智能 / 按预算方案 / 行业趋势 / 品牌软实力 |

路由由 `hashchange` 驱动：`onHashChange()` 用 `SUB_PAGE_RE` 匹配 hash，命中→`showSubPage(id)`，否则→`showMainView()`。`body.is-home` / `body.is-sub` 类驱动 CSS 状态（导航栏主页隐藏、Hero 子页压缩为细条页头）。

---

## 组件层次

```
.hero               → 编辑刊风页头（行首 kicker + 衬线标题 + 朱红印章 .hero-seal + 搜索框）
.nav-wrap           → 导航栏（nav-tab × 22，仅子页显示，sticky 吸顶）
.container           → 主内容区
  .home-hub#homeHub  → 主页模块中心
    .hub-heading     → 分组标题（壹 品类选购 / 贰 专题指南）
    .category-grid   → 17 品类卡（renderCategoryGrid 动态生成，N 款 · M 维度）
    .topic-grid      → 5 个专题入口 .topic-entry（静态：速查总览 + 4 专题子页）
  .section#overview* → 速查总览三 section（子页聚合显示）
  .section#cat-*     → 品类子页
    .filter-panel    → 筛选面板（initCategoryView 动态创建）
      .priority-tags → 优先级标签（多选）
      .brand-tags    → 品牌标签（多选）
      .price-range-row → 价格区间（两个 .price-input 输入框）
    .dim-table-wrap  → 动态对比表格容器（renderDimTable 动态创建，插在 filter-panel 之后）
  .section#topic-*   → 专题子页
```

---

## 筛选面板

### 优先级标签
17 品类各有预设标签，定义在 `PRIORITY_TAGS`（数组元素 `[标签文字, sort_key, sort_dir]`，默认选中"综合推荐"）。

**多选 + 均分权重**：选中多个非"综合推荐"标签时，权重均分（`Math.floor(100 / n)`）打包成 `weights` 对象传给请求，`sort_key` 置空；只选"综合推荐"时 `weights=null`，走默认 `total_score` 排序。至少保留一个选中。

示例（cat-1 抽油烟机）：
```
[大吸力优先] [高静压] [静音] [性价比] [综合推荐]
```

**排序消费**：
- 后端模式：`weights` 传给 API 作为自定义权重参与综合分计算（`total_score = Σ(normalized × weight) / Σ(weight)`），按综合分降序；单维度排序按维度 normalized 分（后端已处理 `higher_better=false` 的方向反转）
- 静态模式：权重排序与单维度排序统一消费 data.json 导出的 `scores`（各维度 normalized 分，4 位小数，与后端同一 scorer 算法）；单维度排序同样按 `higher_better` 反转方向；默认排序消费 `total_score`
- 价格（性价比标签）：价格已恢复为维度 `价格_low`（weight=50，higher_better=false），
  由产品列 `price_low` 承载，参与综合分与单维排序；`price_low` 为浏览器实测的国补后/到手价

### 默认排序
- 综合推荐（默认）：需人工核查（`needs_review`）排最后 → 通用款（"代表款"徽标）次之 → 具体型号按 `total_score` 降序

### 品牌筛选
标签样式，点击切换选中。收集后通过 `brands` 参数传给 API（"全部"标签 `data-brand="__all__"` 清空选中）。

### 价格筛选
`.price-range-row` 内两个数字输入框（`data-price="min"/"max"`），对应 `price_min` / `price_max`；=0 视为未过滤，与产品价格区间有交集即命中。

---

## 动态表格 (`renderDimTable`)

### 结构
- 列头：品牌型号 | 价格 | 维度1..n | 推荐星级
- 每行一个产品（品牌 + 具体型号）
- 品牌型号列为京东搜索链接
- 表格容器 `.dim-table-wrap` 由 JS 动态创建（复用/创建，插在 filter-panel 后面），内部为 `.table-wrap > table.dim-table-dynamic`
- 价格列取产品列 `price_low`（`formatPrice` 格式化，≥1 万显示"x.x万"）；有 `price_collected_at` 时显示"更新于 YYYY-MM-DD"小字
- 文本型维度（type=text）不参与表格展示

### 滚动吸顶
- **首列 sticky left 有效**（`.dim-table-dynamic th:first-child / td:first-child` 品牌型号列固定）
- 表头吸顶（`th` 声明 `position:sticky; top:0`）**实际不生效**（父容器无独立滚动上下文）；导航栏 `.nav-wrap` 吸顶正常

### 颜色分级
仅 float 维度生效。计算该维度全部产品值的 25%/75% 分位数：
- 前 25% → 绿色（`.dim-green`）
- 中间 50% → 黄色（`.dim-yellow`）
- 后 25% → 红色（`.dim-red`）
- 配合 `higher_better` 反转判断

### 星级评分
`total_score` 映射为星级：
```
≥85 → ★★★★★
≥70 → ★★★★☆
≥55 → ★★★☆☆
≥40 → ★★☆☆☆
<40 → ★☆☆☆☆
```

---

## JS 函数索引

| 函数 | 职责 |
|------|------|
| `onHashChange()` | 路由入口：hash 匹配 `SUB_PAGE_RE` → showSubPage，否则 showMainView |
| `showMainView()` | 主页视图：隐藏全部 section，显示 homeHub，body 加 `is-home` |
| `showSubPage(id)` | 子页视图：隐藏 homeHub，显示目标 section（overview 聚合三个）+ 面包屑，body 加 `is-sub`，cat-* 额外调 initCategoryView |
| `highlightNavTab(id)` | 导航 tab 高亮并滚动到可见 |
| `switchTab(id)` | 统一改写 `location.hash`，由 hashchange 驱动视图 |
| `toggleCard(header)` | 卡片折叠/展开 |
| `toggleSub(header)` | 子章节折叠/展开 |
| `doSearch(query)` | 主页模块卡过滤（匹配品类名/专题名，搜索框仅主页可见） |
| `renderCategoryGrid()` | 主页品类卡动态生成（product_count + 交错 rise 淡入） |
| `loadStaticData()` | 加载 data.json（静态模式，带缓存） |
| `showModeIndicator()` | 静态模式显示"📦 静态数据模式"指示器（IIFE 立即执行） |
| `fetchCategories()` | 获取品类列表（API / 静态数据，含 product_count 兜底） |
| `fetchProducts(slug, params)` | 获取产品列表：静态模式本地筛选+排序，本地模式请求 API |
| `initCategoryView(slug)` | 初始化品类子页：展开卡片 + 创建 filter-panel + 触发首次加载 |
| `createFilterPanel(slug, cat)` | 构建 filter-panel DOM（优先级/品牌/价格/操作按钮 + 事件绑定） |
| `populateFilterPanel(panel, cat)` | 填充面板数据：优先级标签 + 品牌标签 |
| `populatePriorityTags(panel, slug)` | 按品类预设填充优先级标签（多选切换，至少保留一个） |
| `populateBrandTags(panel, products, selected)` | 从产品数据提取品牌填充标签（含"全部"） |
| `applyFilters(slug)` | 收集筛选状态 → 请求数据 → 渲染表格（API 失败时恢复静态表） |
| `resetFilters(slug)` | 恢复默认筛选（综合推荐 + 全品牌 + 不限价） |
| `restoreStaticTable(section)` | API 不可用时移除动态表、恢复静态表格显示 |
| `renderDimTable(panel, products, dims)` | 渲染动态对比表格（内部嵌套 `getDimClass` 做分位颜色分级） |
| `formatPrice(val)` | 价格格式化（≥1 万 → "x.x万"） |
| `formatDimValue(val, type, unit)` | 维度值格式化（bool → ✅/❌） |
| `getStars(score)` | 分数转星级 |
| `escapeHtml(str)` | HTML 转义（品牌/型号文本安全输出） |

---

## CSS 变量（暖纸编辑风）

```css
:root {
  --primary: #b03a2e; --primary-light: #c94c3d;   /* 朱红主色 */
  --accent: #b0782a; --teal: #2f5d62;             /* 赭金点缀 / 黛青辅助 */
  --bg: #f6f1e7; --card: #fffdf8;                 /* 暖纸底 / 纸卡 */
  --text: #2b2620; --text-light: #867867;         /* 墨色 / 次级 */
  --border: #e6dcc9; --radius: 10px;
  --success: #3d7a4e; --danger: #b03a2e; --warning: #b0782a;
  --shadow: 0 2px 10px rgba(89,74,51,.08);
  --serif: "Noto Serif SC","Source Han Serif SC","Songti SC","STSong","SimSun",serif; /* 标题衬线栈，不引入外部字体 */
}
```

---

## 关键 CSS 类

| 类 | 用途 |
|----|------|
| `body.is-home` / `body.is-sub` | 视图状态：主页隐导航 / 子页压缩 Hero |
| `.home-hub` / `.hub-heading` | 主页模块中心 / 分组标题（壹贰章号） |
| `.category-card` / `.topic-entry` | 品类卡 / 专题入口卡（rise 交错淡入） |
| `.hero-seal` | 朱红方章印记（纯 CSS） |
| `.breadcrumb` | 子页面包屑（← 返回全部模块） |
| `.filter-panel` | 筛选面板容器 |
| `.priority-tag` / `.priority-tag.active` | 优先级标签 / 选中态 |
| `.brand-tag` / `.brand-tag.active` | 品牌标签 / 选中态 |
| `.price-range-row` / `.price-input` | 价格区间行 / 价格输入框 |
| `.dim-table-wrap` | 动态表格容器（JS 创建） |
| `.dim-table-dynamic` | 动态对比表格 |
| `.dim-green` / `.dim-yellow` / `.dim-red` | 维度值颜色分级（暖调背景） |
| `.score-cell` | 星级评分列 |
| `.jd-link` | 京东搜索链接 |
| `.card-header` / `.card-body` | 折叠卡片 |
