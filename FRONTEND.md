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

## 页面结构（SPA 双视图）

| 视图 | URL hash | 内容 |
|------|----------|------|
| 主页面 | 无 / `#home` | Hero + 搜索 + 品类卡片网格 + 速查表 + 专题 |
| 品类子页 | `#cat-1`~`#cat-17` | 面包屑 + filter-panel + 对比表格 + 详情卡片 |

`switchTab()` 驱动视图切换，`initCategoryView()` 初始化品类页面。

---

## 组件层次

```
.hero               → 标题 + 搜索框
.nav-wrap           → 导航栏（nav-tab × 22）
.container           → 主内容区
  .section#overview  → 速查总览（主页面）
  .section#cat-*     → 品类子页面
    .filter-panel    → 筛选面板
      .priority-tags → 优先级标签（多选）
      .brand-tags    → 品牌标签（多选）
      .price-range   → 价格区间
    .dim-table-wrap  → 动态对比表格
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
| `switchTab(id)` | 导航切换，品类 tab 额外触发 initCategoryView |
| `toggleCard(header)` | 卡片折叠/展开 |
| `doSearch(query)` | 本地搜索过滤（全文匹配品类名/品牌名） |
| `fetchCategories()` | 获取品类列表（API / 静态数据） |
| `fetchProducts(slug, params)` | 获取产品列表，含筛选排序 |
| `initCategoryView(slug)` | 初始化品类子页面：展开卡片 + 创建 filter-panel |
| `createFilterPanel()` | 构建 filter-panel DOM |
| `populatePriorityTags()` | 按品类填充优先级标签 |
| `applyFilters(slug)` | 收集筛选状态 → 请求数据 → 渲染表格 |
| `resetFilters(slug)` | 恢复默认筛选（综合推荐 + 全品牌 + 不限价） |
| `renderDimTable(products, dims)` | 渲染动态对比表格 |
| `loadStaticData()` | 加载 data.json（静态模式） |
| `getStars(score)` | 分数转星级 |
| `formatDimValue(val, dim)` | 维度值格式化 |

---

## CSS 变量

```css
:root {
  --primary: #2563eb; --primary-light: #3b82f6;
  --accent: #f59e0b; --bg: #f5f7fa; --card: #fff;
  --text: #1e293b; --text-light: #64748b;
  --border: #e2e8f0; --radius: 12px;
  --success: #10b981; --danger: #ef4444; --warning: #f59e0b;
}
```

---

## 关键 CSS 类

| 类 | 用途 |
|----|------|
| `.filter-panel` | 筛选面板容器 |
| `.priority-tag` / `.priority-tag.active` | 优先级标签 / 选中态 |
| `.brand-tag` / `.brand-tag.active` | 品牌标签 / 选中态 |
| `.dim-table-dynamic` | 动态对比表格 |
| `.dim-green` / `.dim-yellow` / `.dim-red` | 维度值颜色分级 |
| `.score-cell` | 星级评分列 |
| `.jd-link` | 京东搜索链接 |
| `.card-header` / `.card-body` | 折叠卡片 |
