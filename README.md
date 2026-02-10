# 🚀 Startup Oracle Agent

A LangGraph-based pipeline for startup opportunity discovery: extract pain points, cluster them into opportunities, score them, and generate reports from comments and social media text.

---

## ✨ Key Features

- **Policy Gate** – Budget control, compliance, rate limits  
- **Collector** – Collect raw data (search, Browser-use)  
- **Cleaner** – Denoise, dedupe, desensitize  
- **Extractor** – GPT-4o-based pain-point extraction (schema + anti-hallucination)  
- **Clusterer** – Cluster pain points into opportunities  
- **Validator** – Validate evidence and persistence  
- **Scorer** – Multi-dimensional opportunity scoring  
- **Memory** – Store opportunities in SQLite  
- **Reporter** – Generate final reports  

---

## 📁 Project Structure

startup-oracle-agent/
├── pyproject.toml
├── .env.example
├── src/
│ ├── main.py
│ ├── nodes/
│ ├── memory/
│ ├── utils/
│ └── tests/
├── data/
└── tests/


---

## ⚡ Quick Start

### 1️⃣ Install Dependencies

```bash
pip install -e .
2️⃣ Set Up Environment Variables
cp .env.example .env
Add your keys inside .env:

OPENAI_API_KEY=your_key
SERPAPI_API_KEY=your_key
BROWSER_USE_API_KEY=your_key
3️⃣ Run the Pipeline
Default run (fixture data):

python -m src.main
Real browser collection:

ORACLE_USE_BROWSER=1 python -m src.main
4️⃣ Run Tests
pytest tests/ -v
🔑 Environment Variables
Variable	Description
OPENAI_API_KEY	OpenAI API key
SERPAPI_API_KEY	SERP API key
BROWSER_USE_API_KEY	Browser-use API key
ORACLE_USE_BROWSER	Set to 1 for real browser collection
ORACLE_TARGET_URL	Direct URL to collect
ORACLE_SEARCH_KEYWORD	Keyword for dynamic URL
ORACLE_COLLECT_URL_TEMPLATE	URL template with {search_keyword}
LOG_LEVEL	Log level (default: INFO)
🌐 Collector URL Configuration (Any Website)
Direct URL
ORACLE_TARGET_URL=https://example.com/page
Or via state:

state["collector"]["target_url"]
Build URL from Keyword
ORACLE_SEARCH_KEYWORD=ai_tools
ORACLE_COLLECT_URL_TEMPLATE=https://www.xiaohongshu.com/explore/{search_keyword}
{search_keyword} will be replaced at runtime.

Works for any website that supports keyword-based URLs.


---

# ✅ 中文版本（GitHub 兼容）

```markdown
# 🚀 Startup Oracle Agent

基于 LangGraph 的初创机会发现流水线：  
从评论与社交媒体文本中提取痛点、聚类机会、评分并生成报告。

---

## ✨ 主要功能

- **Policy Gate** – 预算控制、合规检查、速率限制  
- **Collector** – 原始数据采集（搜索 / Browser-use）  
- **Cleaner** – 去噪、去重、脱敏  
- **Extractor** – 基于 GPT-4o 的结构化痛点抽取（防编造）  
- **Clusterer** – 痛点聚类为机会主题  
- **Validator** – 证据验证与持续性检查  
- **Scorer** – 多维度机会评分  
- **Memory** – 使用 SQLite 存储长期记忆  
- **Reporter** – 生成最终报告  

---

## 📁 项目结构

startup-oracle-agent/
├── pyproject.toml
├── .env.example
├── src/
│ ├── main.py
│ ├── nodes/
│ ├── memory/
│ ├── utils/
│ └── tests/
├── data/
└── tests/


---

## ⚡ 快速开始

### 1️⃣ 安装依赖

```bash
pip install -e .
2️⃣ 配置环境变量
cp .env.example .env
在 .env 文件中添加：

OPENAI_API_KEY=你的Key
SERPAPI_API_KEY=你的Key
BROWSER_USE_API_KEY=你的Key
3️⃣ 运行管道
默认使用示例数据：

python -m src.main
启用浏览器采集：

ORACLE_USE_BROWSER=1 python -m src.main
4️⃣ 运行测试
pytest tests/ -v
🔑 环境变量说明
变量	说明
OPENAI_API_KEY	OpenAI API 密钥
SERPAPI_API_KEY	SERP API 密钥
BROWSER_USE_API_KEY	浏览器 API 密钥
ORACLE_USE_BROWSER	设置为 1 使用浏览器采集
ORACLE_TARGET_URL	直接指定采集 URL
ORACLE_SEARCH_KEYWORD	关键词搜索
ORACLE_COLLECT_URL_TEMPLATE	含 {search_keyword} 的 URL 模板
LOG_LEVEL	日志级别（默认 INFO）
🌐 Collector 访问 URL 配置（任意网站）
直接指定 URL
ORACLE_TARGET_URL=https://example.com/page
或在代码中：

state["collector"]["target_url"]
使用关键词拼接 URL
ORACLE_SEARCH_KEYWORD=AI工具
ORACLE_COLLECT_URL_TEMPLATE=https://www.xiaohongshu.com/explore/{search_keyword}
