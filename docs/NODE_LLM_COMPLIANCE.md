# Node LLM Compliance Check

对照标准：🟢 规则/算法型（不用 LLM） vs 🔵 认知型（必须用 LLM）

---

## 🟢 不应使用 LLM 的节点

| 节点 | 标准要求 | 当前实现 | 符合 |
|------|----------|----------|------|
| **Collector** | 浏览器/爬虫自动化 | 占位，无任何 LLM/API 调用 | ✅ |
| **Cleaner** | 文本处理、正则、hash、simhash、规则 | 仅 `re`/`hashlib`/dataclass，无 langchain/openai | ✅ |
| **Policy Gate** | 控制流、计数器 | 仅 `os.getenv` + if/else，无 LLM | ✅ |
| **Persistence / Memory** | 存储 (SQLite/Chroma) | `memory/` 下无 LLM 引用 | ✅ |

---

## 🔵 应使用 LLM 的节点

| 节点 | 标准要求 | 当前实现 | 符合 |
|------|----------|----------|------|
| **Extractor** | 语义理解：不满、原因、persona、证据等 | `ChatOpenAI` + 结构化输出，支持 `_llm_factory` | ✅ |
| **Clusterer** | 抽象与概念合并 | 图已改为 `clusterer_node()`；默认 LLM，`_cluster_rule_only=True` 时回退规则 | ✅ |
| **Validator** | 推理：证据、持续性 | LLM 输出 `ValidationList`（passed + reason），`_validator_rule_only` 时回退规则 | ✅ |
| **Scorer** | 商业维度打分 | LLM 输出 `ScoreCardList`（五维 0–5），`_scorer_rule_only` 时回退固定分 | ✅ |
| **Reporter** | 结构化 → 可读简报 | 纯模板拼接；若需认知型可再加 LLM | ⚠️ |

---

## 回退规则（无需 API 时）

- **Clusterer**：`state["_cluster_rule_only"] = True` → 使用 `cluster()` 按 complaint 前缀分组。
- **Validator**：`state["_validator_rule_only"] = True` → 使用 `sample_size >= 0 and confidence >= 0` 过滤。
- **Scorer**：`state["_scorer_rule_only"] = True` → 各维度固定 2.5。

---

## 结论

- **🟢 无 LLM 节点**：Collector、Cleaner、Policy Gate、Memory 均符合。
- **🔵 认知型节点**：Extractor、Clusterer、Validator、Scorer 均已接入 LLM；失败时自动回退到规则，测试可注入 `_llm_factory`。
