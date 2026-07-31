# 开发工作流规范

## 日常操作

| 操作 | 命令 |
|------|------|
| 启动后端 | `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` |
| 导出静态数据 | `python backend\export_static_data.py` |
| 运行校对报告 | `python -m backend.scrapers.verify` |
| 查看 Git 状态 | `git status` |
| 提交改动 | `git add <文件>` → `git commit -m "信息"` → `git push origin master` |

---

## 任务核验清单

每次完成任务后对照检查：

| # | 检查项 | 验证方式 |
|---|--------|---------|
| 1 | 代码已提交 | `git status` 干净 |
| 2 | 已 push 到 GitHub | `git push origin master` |
| 3 | **规范文件已更新** | 检查 AGENTS.md / FRONTEND.md / BACKEND.md / SCHEMA.md / WORKFLOW.md |
| 4 | 数据有变化 | 已运行 `python backend\export_static_data.py` |
| 5 | GitHub Pages 已验证 | 浏览器打开确认（Ctrl+F5 强制刷新） |

---

## Bug 修复工作流

1. **定位**：用 JS evaluate / snapshot / screenshot 确认问题
2. **修复**：最小改动，优先编辑现有文件
3. **验证**：`node --check` 语法检查 + 浏览器视觉验证
4. **更新规范**：立即将修复内容写入对应的规范文件
5. **提交推送**：`git add` → `git commit` → `git push`

---

## Git 规则

- 代理：`127.0.0.1:7897`
- `backend/app.db` 和 `__pycache__/` 不提交（已 `.gitignore`）
- 提交信息用中文，简洁概括
- 文件逐个 `git add`，不用 `-A`（防误加 db 文件）
- **每次修改后立即 push**，同步 GitHub Pages

---

## 工具使用规则

| 工具 | 用途 |
|------|------|
| **AnySearch** | 网络搜索调研 |
| **Kimi WebBridge** | 浏览器交互：截图、点击、滚动 |
| **playwright** | 自动化浏览器操作 |
| **@observer** | 视觉分析截图 |
| **@designer** | UI/UX 设计、前端实现 |
| **@fixer** | 后端脚本、数据修复 |
| **@librarian** | 外部文档、API 查询 |

**禁止**：`webfetch`（一律不用）

---

## 数据变更后必做

```
1. 运行数据修复/扩充脚本
2. python backend\export_static_data.py   ← 重新导出 data.json
3. git add data.json
4. git commit -m "数据更新: ..."
5. git push origin master
```

---

## 规范文件体系

| 文件 | 职责 |
|------|------|
| `AGENTS.md` | 项目索引 + 快速导航 |
| `SCHEMA.md` | 品类维度定义、枚举映射、质量规则 |
| `FRONTEND.md` | 前端架构、组件、JS 函数、CSS |
| `BACKEND.md` | 后端 API、数据库、脚本、评分引擎 |
| `WORKFLOW.md`（本文件） | 开发工作流、Git 规则、核验清单 |
| `PLAN.md` | 目标模式执行提示词 |
