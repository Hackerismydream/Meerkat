from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class ScriptRunner:
    name = "script"
    allowed_tools = []

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        output = {
            "speaker_note": input_data.get("speaker_note", "当前直播信号出现波动，请场控确认 OBS 和网络状态，主播先暂停关键商品承诺。"),
            "target": input_data.get("target", "field_control"),
            "can_send_to_owncast": bool(input_data.get("can_send_to_owncast", False)),
            "requires_operator_confirm": bool(input_data.get("requires_operator_confirm", True)),
        }
        return AgentResult(agent_name=self.name, status="OK", output=output, confidence=0.88)
