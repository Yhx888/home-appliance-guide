# 全国家电选购指南

纯静态单页 HTML 全国家电对比指南，覆盖 17 品类 + 8 专题，通过 GitHub Pages 发布。

## 常用命令

| 命令 | 用途 |
|------|------|
| 直接浏览器打开 `index.html` | 本地预览 |
| `git add index.html; git commit -m "..."` | 提交修改 |
| `git push origin master` | 推送到 GitHub（需代理 127.0.0.1:7897） |

无构建工具、无依赖、无 `npm install`。

## 架构

```
home-appliance-guide/
  index.html    # 唯一起效文件，HTML+CSS+JS 全内联
  AGENTS.md     # AI 工作上下文
  .gitignore    # 排除编辑器配置
```

## 关键文件

- `index.html` — 全部页面内容（约 1400 行），包含 CSS（<style>）、HTML 结构、JS（<script>）

## 代码风格

- CSS 变量定义在 `:root`，前缀无命名空间，直接使用变量名
- 卡片结构：`.section > .card > .card-header + .card-body`，折叠展开由 `toggleCard()` 驱动
- 选购买建议卡片：`.advice-card` 带金色边框，自动生成 "💡 选购建议" 标题
- 多维度对比表：`table.dim-table`，横向为品牌、纵向为维度
- 导航切换：`switchTab(id)` → `scrollIntoView`
- 搜索过滤：`doSearch(query)` → 按品类 section 全文匹配

## 坑

- GitHub Pages 有 CDN 缓存，push 后需等数分钟才生效，加 `?v=随机数` 可绕过
- 本项目配置了 git 代理 `127.0.0.1:7897`，push 前需确保代理软件运行
- 所有数据硬编码在 HTML 中，修改数据需直接编辑 `<table>` 行

## 工作流

- **编辑品类数据**：直接在 `index.html` 中修改对应品类的 `<table>` 内容
- **添加新品类**：复制现有品类 section 结构，修改 `id`、标题和数据
- **修改样式**：编辑 `<style>` 块中的 CSS 变量或类定义
- **发布**：修改后 commit → push，GitHub Pages 自动部署
