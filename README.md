# 全国家电选购指南

覆盖 17 品类 448 款产品的家电选购参考，数据经网络调研 + 规则填充 + 多方核验校对，支持筛选、多维度排序与星级推荐。

## 访问方式

- **GitHub Pages（静态）**：https://yhx888.github.io/home-appliance-guide/
- **本地（FastAPI 后端）**：`http://localhost:8000`

## 快速启动

```bash
pip install -r backend\requirements.txt
python -m backend.seed_data
python -m backend.expand_data
python -m backend.enrich_data
python -m backend.fix_data
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## 文档

- [AGENTS.md](AGENTS.md) — 项目索引与快速导航
- [SCHEMA.md](SCHEMA.md) — 数据规范（品类维度定义、枚举映射、质量规则）
- [WORKFLOW.md](WORKFLOW.md) — Git 规则、核验清单、数据变更流程
