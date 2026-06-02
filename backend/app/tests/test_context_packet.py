"""ContextPacket tests."""

from app.context.packet import ContextPacket


def test_context_packet_defaults():
    packet = ContextPacket(
        node_name="pain_extract",
        goal="extract pains",
        input_items=[{"id": "1"}],
        token_budget=1000,
        output_schema={"items": "list"},
        prompt_version="test:v1",
    )
    assert packet.evidence_ids == []
    assert packet.memory_snippets == []
    assert packet.node_name == "pain_extract"
