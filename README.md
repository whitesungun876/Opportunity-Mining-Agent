English Version 
## Startup Oracle Agent

A LangGraph-based pipeline for startup opportunity discovery: extract pain points, cluster them into opportunities, score, and produce reports from comments and social media text.

# Key Features

Policy Gate: Budget, compliance, rate limits
Collector: Collect raw data (search, Browser-use)
Cleaner: Denoise, dedupe, desensitize
Extractor: GPT-4o-based pain-point extraction (schema + anti-hallucination)
Clusterer: Cluster pain points into opportunities
Validator: Validate evidence and persistence
Scorer: Opportunity scoring (multi-dimensional + total score)
Memory: Store opportunities in SQLite
Reporter: Generate final reports

# Project Structure

startup-oracle-agent/
├── pyproject.toml          # Project metadata and dependencies
├── .env.example            # Environment variable template
├── src/                    # Source code
│   ├── main.py             # Entry point: build graph & run
│   ├── nodes/              # Node logic
│   ├── memory/             # Vector DB, SQLite memory
│   ├── utils/              # Utility files
│   └── tests/              # Unit & smoke tests
├── data/                   # Data storage (raw, cleaned, runs)
└── tests/                  # Tests

# Quick Start

Install Dependencies
pip install -e .  # Editable install

Set Up Environment Variables
cp .env.example .env
Add your keys (e.g., OPENAI_API_KEY) to the .env file

Run the Pipeline
python -m src.main  # Default run with fixture data

For real browser collection:
ORACLE_USE_BROWSER=1 python -m src.main

Run Tests
pytest tests/ -v

# Environment Variables

| Variable              | Description                            |
| --------------------- | -------------------------------------- |
| `OPENAI_API_KEY`      | OpenAI API key                         |
| `SERPAPI_API_KEY`     | SERP API key                           |
| `BROWSER_USE_API_KEY` | Browser-use API key                    |
| `ORACLE_USE_BROWSER`  | Set to `1` for real browser collection |
| `LOG_LEVEL`           | Log level (default: INFO)              |

**Collector URL configuration (any website)**
- **Direct URL:** set `ORACLE_TARGET_URL=https://example.com/page` or `state["collector"]["target_url"]` to open a specific page.
- **Build URL from keyword (any site):** set `ORACLE_SEARCH_KEYWORD=your_keyword` and `ORACLE_COLLECT_URL_TEMPLATE=https://yoursite.com/path/{search_keyword}`; `{search_keyword}` is replaced at runtime. Example (Xiaohongshu): `ORACLE_COLLECT_URL_TEMPLATE=https://www.xiaohongshu.com/explore/{search_keyword}`; same pattern for other sites.

中文版本 
## Startup Oracle Agent

基于 LangGraph 的初创机会发现流水线：从评论和社交媒体文本中提取痛点、聚类机会、评分并生成报告。

# 主要功能

Policy Gate: 预算、合规、速率限制
Collector: 原始数据采集（搜索、Browser-use）
Cleaner: 去噪、去重、脱敏
Extractor: 基于 GPT-4o 的痛点抽取（结构化 + 防编造）
Clusterer: 聚类痛点为机会
Validator: 证据验证与持续性检查
Scorer: 机会评分（多维度 + 总分）
Memory: SQLite 存储机会
Reporter: 生成最终报告

# 项目结构

startup-oracle-agent/
├── pyproject.toml          # 项目元数据与依赖
├── .env.example            # 环境变量模板
├── src/                    # 源代码
│   ├── main.py             # 入口：构建图并运行
│   ├── nodes/              # 节点逻辑
│   ├── memory/             # 向量库，SQLite 记忆
│   ├── utils/              # 工具文件
│   └── tests/              # 单元与冒烟测试
├── data/                   # 数据存储（原始、清理、运行结果）
└── tests/                  # 测试

# 快速开始

安装依赖
pip install -e .  # 可编辑安装

配置环境变量
cp .env.example .env
在 .env 文件中添加你的 API 密钥（如 OPENAI_API_KEY）

运行管道
python -m src.main  # 默认使用 fixture 数据

启用浏览器采集：
ORACLE_USE_BROWSER=1 python -m src.main

运行测试
pytest tests/ -v

# 环境变量
| 变量                   | 说明                  |
| --------------------- | ---------------       |
| `OPENAI_API_KEY`      | OpenAI API 密钥        |
| `SERPAPI_API_KEY`     | SERP API 密钥          |
| `BROWSER_USE_API_KEY` | 浏览器 API 密钥         |
| `ORACLE_USE_BROWSER`  | 设置为 `1` 使用浏览器采集 |
| `LOG_LEVEL`           | 日志级别（默认：INFO）    |


Collector 访问 URL 配置（任意网站）
- 直接指定 URL：`ORACLE_TARGET_URL=https://example.com/page` 或 state["collector"]["target_url"]
- 用关键词拼 URL（任意站）：设置 `ORACLE_SEARCH_KEYWORD=关键词` 和 `ORACLE_COLLECT_URL_TEMPLATE=https://目标站/路径/{search_keyword}`，其中 `{search_keyword}` 会被替换。例如小红书：`ORACLE_COLLECT_URL_TEMPLATE=https://www.xiaohongshu.com/explore/{search_keyword}`；其他站同理。