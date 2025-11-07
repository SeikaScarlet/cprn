# CPRN - Calculable Preprocessed Road Network

**可计算路网** - 基于高精度地图和设施数据的可计算道路网络

## 📚 项目说明

CPRN 是一个用于构建和应用可计算路网的工具库，支持：
- 高精度地图数据处理
- 设施（门架、服务区、枢纽）拓扑绑定
- 路网图构建与优化
- 拓扑检索与路径分析

## 🗂️ 项目结构

```
cprn/
├── cprn/           # 核心库代码
├── doc/            # 技术文档
├── jnb/            # Jupyter Notebooks
│   ├── create/    # CPRN 构建流程
│   └── app/       # 应用示例
└── pyproject.toml
```

## 📖 文档与笔记

### 技术文档
- `doc/` - 架构设计、构建总结等正式文档

### 工作笔记（Obsidian Vault）
- **位置**: `../cprn_notes/`
- **内容**: 版本构建记录、工程挑战、核心概念
- **访问**: 使用 Obsidian 打开 `cprn_notes/` 查看完整知识库

**版本构建记录** 👉 [`cprn_notes/Builds/`](../cprn_notes/Builds/)

## 🚀 快速开始

```python
from cprn.data.pickle import PickleIO
from cprn.model.topo.topo_search import CprnTopoSearch

# 加载 CPRN 模型
dg_cprn = PickleIO.load_from_pickle('path/to/model.pkl')

# 拓扑检索
cts = CprnTopoSearch(dg_cprn)
```

## 📦 最新版本

- **V4.1.7** (2025-11-06): 枢纽设施绑定
- 详见: [`cprn_notes/Builds/v417_works.md`](../cprn_notes/Builds/v417_works.md)
