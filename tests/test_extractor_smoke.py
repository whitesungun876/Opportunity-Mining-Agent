"""Extractor smoke test: offline (fake LLM) and optional online (real API)."""

from typing import List

from pydantic import BaseModel, Field

from src.nodes.extractor import extractor_node
from src.utils.schema import PainPoint


class PainPointList(BaseModel):
    items: List[PainPoint] = Field(default_factory=list)


class FakeStructuredLLM:
    def invoke(self, messages):
        return PainPointList(items=[
            PainPoint(
                complaint="订阅太贵",
                cause="低频使用也必须按月买会员",
                persona="低频用户",
                context="偶尔使用该软件",
                action_intent="希望按量付费/一次性付费",
                evidence=["我也觉得贵，能不能出个按量付费的啊？每次都要买一个月会员太心疼了。"],
            )
        ])


class FakeLLM:
    def with_structured_output(self, _schema):
        return FakeStructuredLLM()


def test_extractor_smoke_offline():
    comments = [
        "这个软件真好用，yyds！",
        "我也觉得贵，能不能出个按量付费的啊？每次都要买一个月会员太心疼了。",
        "楼上+1，上次我用了一次就没用了，白花了 99。",
    ]
    state = {"raw_comments": comments, "_llm_factory": lambda: FakeLLM()}

    out = extractor_node(state, max_retries=0, min_items_required=1)
    pains = out.get("extracted_pains", [])
    assert len(pains) >= 1

    raw = "\n".join(comments)
    for p in pains:
        assert isinstance(p, PainPoint)
        for ev in p.evidence:
            assert ev in raw
