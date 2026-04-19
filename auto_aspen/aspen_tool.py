"""
Aspen 综合仿真工具：供 openai-agents 的 Agent 通过 function calling 调用，
底层与 POST /api/simulation 相同（execute_comprehensive_simulation）。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from agents import function_tool


@function_tool(
    strict_mode=False,
    name_override="run_aspen_comprehensive_simulation",
    description_override=(
        "执行 ASPEN + 机组功率 + 技术文档的**综合仿真**（与 HTTP POST /api/simulation 等价）。"
        "当用户明确要求「跑仿真 / 算一下 / 出结果」且气量、进/出口压力、入口温度等必填参数已齐时调用；"
        "数值应优先与系统消息中的 partial_params（左侧表单）一致。返回 JSON 字符串摘要（成功时含概况与图表/文档链接）。"
    ),
)
async def run_aspen_comprehensive_simulation(
    gas_flow_rate: float,
    inlet_pressure: float,
    inlet_temperature: float,
    outlet_pressure: float,
    efficiency: float = 85.0,
    gas_composition: Optional[Dict[str, float]] = None,
    user_name: Optional[str] = None,
) -> str:
    """运行综合仿真并返回简要结果 JSON 字符串。"""
    # 延迟导入，避免与 main 的循环依赖（main 会加载 chat_stream）
    from main import GasComposition, SimulationRequest, execute_comprehensive_simulation

    gc_raw = gas_composition if isinstance(gas_composition, dict) else {}
    merged = {k: float(gc_raw.get(k, 0) or 0) for k in GasComposition.model_fields}
    gas = GasComposition(**merged)
    req = SimulationRequest(
        gas_flow_rate=float(gas_flow_rate),
        inlet_pressure=float(inlet_pressure),
        inlet_temperature=float(inlet_temperature),
        outlet_pressure=float(outlet_pressure),
        efficiency=float(efficiency),
        gas_composition=gas,
        user_name=user_name,
    )
    resp = await execute_comprehensive_simulation(req)
    dumped: Dict[str, Any] = resp.model_dump()

    brief: Dict[str, Any] = {
        "success": dumped.get("success"),
        "error_message": dumped.get("error_message"),
        "diagram_url": dumped.get("diagram_url"),
        "document_urls": dumped.get("document_urls"),
        "details": dumped
    }
    return json.dumps(brief, ensure_ascii=False)


# 装饰器把函数替换为 FunctionTool，供 Agent(tools=[...]) 使用
ASPEN_SIMULATION_TOOL = run_aspen_comprehensive_simulation
