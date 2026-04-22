"""
唯一对话流式出口：使用 OpenAI Agents SDK（from agents import Agent, Runner）。
将 Runner.run_streamed 的事件映射为 SSE（data: JSON 行 + 最后 [DONE]）。
"""
from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from agents import Agent, Runner, RunConfig

from auto_aspen.aspen_tool import ASPEN_SIMULATION_TOOL


class ChatStreamRequest(BaseModel):
    """多轮对话 + 可选模型覆盖 + 左侧表单快照（每次请求随带）。"""
    messages: List[Dict[str, str]] = Field(
        ...,
        min_length=1,
        description="对话历史，每项含 role(user/assistant) 与 content，至少一条",
    )
    partial_params: Optional[Dict[str, Any]] = Field(
        None,
        description="当前页表单工况快照；服务端会作为系统消息注入，每次请求都会带上",
    )
    model: Optional[str] = Field(
        None,
        description="覆盖 AGENT_MODEL；默认 gpt-4o-mini",
    )


def _sse_line(obj: Dict[str, Any]) -> bytes:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")


def _extract_text_delta(data: Any) -> Optional[str]:
    """从 Responses API 流式事件中取出文本增量。"""
    if data is None:
        return None
    d = getattr(data, "delta", None)
    if isinstance(d, str) and d:
        return d
    return None


def _build_agent(model_name: str) -> Agent:
    instructions = (
        os.getenv("AGENT_INSTRUCTIONS", "").strip()
        or (
            "你是透平/工艺仿真相关的中文助手。用户左侧表单中的工况参数会通过系统消息以 JSON（partial_params）提供；"
            "凡涉及气量、压力、温度、气体组成等，**优先采用系统消息中的数值**。\n"
            "你拥有工具 **run_aspen_comprehensive_simulation**：在用户明确要求「跑仿真 / 综合计算 / 出结果 / 算一下工况」时调用。"
            "调用时请传入与 partial_params 一致的数值；若用户要 **EC 机组** 或表单快照中 `unit_scheme` 为 `ec`，必须传入 `unit_scheme=\"ec\"`，以便生成 EC 专用 PPT。\n"
            "**渲染规则（必须严格遵守）**：\n"
            "1. **禁止在正文中打印任何 JSON 原始数据**。严禁将工具返回的 JSON 或用户输入的参数 JSON 直接展示给用户。请直接用自然语言或表格回复结果。\n"
            "2. **详细仿真数据展示**：仿真成功后，必须从工具返回的 `details` 字段中提取关键数据（如轴功率、出口温度、多变效率、质量流量等），并使用 **Markdown 表格** 展示。\n"
            "3. **透平一维设计指标展示**：仿真成功后，必须从 `details.power_results.selection_output.选型输出.透平一维设计指标` 中提取数据（叶轮直径、设计转速、喷嘴马赫数、设计效率、设计评价），并使用 **Markdown 表格** 单独展示。\n"
            "4. **机组示意图展示**：仿真成功后，必须使用 Markdown 图片语法展示机组示意图，格式为：`![机组示意图](图片路径)`。请务必使用工具返回的 `diagram_url`，确保以 `/static` 开头，且必须闭合括号 `)`。\n"
            "5. **文件下载展示**：仿真结果中的技术报告（在 `document_urls` 中），必须使用链接语法展示，格式为：`[点击下载：技术报告名称](文件路径)`。确保路径以 `/static` 开头。\n"
            "6. **回复完整性**：请确保你的回复是完整的 Markdown 格式，不要在输出路径时突然中断。"
            "7. **机组方案**：请根据用户输入的机组方案，选择相应的机组示意图和文件下载链接。"
            "8. 不要出现这种地址：http://127.0.0.1:8000/(/static/re/%E4%BA%A4%E6%B5%81PPT_20260421_214019.pptx) 括号是多余的"
            "9. 也不要出现 file:// 这种地址, 渲染时无法使用"
        )
    )
    return Agent(
        name="Assistant",
        instructions=instructions,
        model=model_name,
        tools=[ASPEN_SIMULATION_TOOL],
    )


def _messages_with_system(body: ChatStreamRequest) -> List[Dict[str, str]]:
    """在对话前插入一条系统消息，携带本次请求的表单快照（不写入前端 history，仅服务端拼接）。"""
    out: List[Dict[str, str]] = []
    if body.partial_params:
        out.append(
            {
                "role": "system",
                "content": (
                    "【当前工况表单快照 partial_params】以下为用户在页面左侧表单中填写的最新数值，"
                    "单位：气量 scmh，压力 MPaA，温度 ℃，效率 %，气体组分为体积分数%；"
                    "`unit_scheme` 为 `pressure_difference`（压差）或 `ec`（EC 机组）。"
                    "涉及工况、计算、组分、机组方案等时**必须以本 JSON 为准**。\n"
                    + json.dumps(body.partial_params, ensure_ascii=False)
                ),
            }
        )
    out.extend(body.messages)
    return out


async def stream_chat_sse(body: ChatStreamRequest) -> AsyncIterator[bytes]:
    """
    Yields SSE: data: {"type":"delta","text":"..."} ... data: {"type":"done"} ... data: [DONE]
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        yield _sse_line({"type": "error", "message": "未配置 OPENAI_API_KEY"})
        yield b"data: [DONE]\n\n"
        return

    model_name = (body.model or os.getenv("AGENT_MODEL") or "gpt-4o-mini").strip()
    agent = _build_agent(model_name)

    try:
        result = Runner.run_streamed(
            agent,
            input=_messages_with_system(body),
            run_config=RunConfig(tracing_disabled=True),
        )
    except Exception as e:
        logger.exception("Runner.run_streamed failed to start")
        yield _sse_line({"type": "error", "message": str(e)})
        yield b"data: [DONE]\n\n"
        return

    try:
        async for event in result.stream_events():
            if event.type == "raw_response_event":
                chunk = event.data
                # 如果是 ResponseFunctionCallArgumentsDeltaEvent，并且 delta 以 ':{"' 开头，则跳过 yield
                if getattr(chunk, "type", "") == "response.function_call_arguments.delta":
                    pass  # 不 yield
                else:
                    text = _extract_text_delta(chunk)
                    if text:
                        yield _sse_line({"type": "delta", "text": text})
             
            elif event.type == "run_item_stream_event":
                if event.name == "tool_called":
                    msg = "工具调用中…"
                    try:
                        it = event.item
                        raw = getattr(it, "raw_item", None)
                        nm = None
                        if raw is not None:
                            nm = getattr(raw, "name", None)
                            if nm is None and isinstance(raw, dict):
                                nm = raw.get("name")
                        if nm:
                            msg = f"正在执行工具：{nm}"
                    except Exception:
                        pass
                    yield _sse_line({"type": "status", "message": msg})
                elif event.name == "tool_output":
                    yield _sse_line({"type": "status", "message": "工具已返回，模型处理中…"})
            elif event.type == "agent_updated_stream_event":
                yield _sse_line(
                    {
                        "type": "status",
                        "message": f"切换至 {event.new_agent.name}",
                    }
                )
    except Exception as e:
        logger.exception("stream_events failed")
        yield _sse_line({"type": "error", "message": str(e)})

    yield _sse_line({"type": "done"})
    yield b"data: [DONE]\n\n"
