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
.nav-wrap           → 导航栏（nav-tab × 22，仅子页显示）
.container           → 主内容区
  .home-hub#homeHub  → 主页模块中心
    .hub-heading     → 分组标题（壹 品类选购 / 贰 专题指南）
    .category-grid   → 17 品类卡（renderCategoryGrid 动态生成，N 款 · M 维度）
    .topic-grid      → 5 个专题入口 .topic-entry（静态）
  .section#overview* → 速查总览三 section（子页聚合显示）
  .section#cat-*     → 品类子页
    .filter-panel    → 筛选面板
      .priority-tags → 优先级标签（多选）
      .brand-tags    → 品牌标签（多选）
      .price-range   → 价格区间
    .dim-table-wrap  → 动态对比表格
  .section#topic-*   → 专题子页
```

---

## 筛选面板

### 优先级标签
17 品类各有预设标签，定义在 `PRIORITY_TAGS`。**多选**模式：选中多个标签后按均分权重传给 API 的 `weights` 参数。

示例（cat-1 抽油烟机）：
```
[大吸力优先] [高静压] [静音] [性价比] [综合推荐]
```

每个标签对应 `sort_key` + `sort_dir`。

### 品牌筛选
标签样式，点击切换选中。收集后通过 `brands` 参数传给 API。

### 价格筛选
两个数字输入框，对应 `price_min` / `price_max`。

---

## 动态表格 (`renderDimTable`)

### 结构
- 列头：品牌型号 | 价格 | 维度1..n | 推荐星级
- 每行一个产品（品牌 + 具体型号）
- 品牌型号列为京东搜索链接

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
| `renderCategoryGrid()` | 主页品类卡动态生成（product_count + 交错 rise 淡入） |
| `toggleCard(header)` | 卡片折叠/展开 |
| `doSearch(query)` | 主页模块卡过滤（匹配品类名/专题名，搜索框仅主页可见） |
| `fetchCategories()` | 获取品类列表（API / 静态数据，含 product_count 兜底） |
| `fetchProducts(slug, params)` | 获取产品列表，含筛选排序 |
| `initCategoryView(slug)` | 初始化品类子页：展开卡片 + 创建 filter-panel |
| `createFilterPanel()` | 构建 filter-panel DOM |
| `populatePriorityTags()` | 按品类填充优先级标签 |
| `applyFilters(slug)` | 收集筛选状态 → 请求数据 → 渲染表格 |
| `resetFilters(slug)` | 恢复默认筛选（综合推荐 + 全品牌 + 不限价） |
| `renderDimTable(products, dims)` | 渲染动态对比表格 |
| `loadStaticData()` | 加载 data.json（静态模式） |
| `getStars(score)` | 分数转星级 |
| `formatDimValue(val, dim)` | 维度值格式化 |

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
| `.dim-table-dynamic` | 动态对比表格 |
| `.dim-green` / `.dim-yellow` / `.dim-red` | 维度值颜色分级（暖调背景） |
| `.score-cell` | 星级评分列 |
| `.jd-link` | 京东搜索链接 |
| `.card-header` / `.card-body` | 折叠卡片 |
