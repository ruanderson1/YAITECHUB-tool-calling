import json
from pathlib import Path

from langchain_core.messages import AIMessage

from app.agent.agentRunner import MAX_TOOL_CALLS, AgentRun, AgentRunner
from evals.run_golden_set import evaluate_case, load_cases

CASES = Path(__file__).resolve().parents[1] / "evals" / "golden_set.json"

def test_golden_set_has_at_least_twenty_valid_unique_cases() -> None:
    cases = load_cases(CASES)
    assert len(cases) >= 20
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["category"] for case in cases} >= {"consulta", "baixa", "erro", "fora_escopo"}

def test_evaluator_accepts_expected_call() -> None:
    case = json.loads(CASES.read_text(encoding="utf-8"))[0]
    run = AgentRun("Teclado: 10 unidades em estoque", [{"event":"tool_call", "tool":"consultar_estoque", "arguments":{"name":"teclado"}}])
    assert evaluate_case(case, run).passed

def test_evaluator_rejects_forbidden_mutation() -> None:
    case = next(c for c in load_cases(CASES) if c["id"] == "consulta_sem_alterar")
    run = AgentRun("Monitor: 4 unidades", [{"event":"tool_call", "tool":"baixar_estoque", "arguments":{"name":"Monitor", "quantity":1}}])
    result = evaluate_case(case, run)
    assert not result.passed
    assert not result.checks["forbidden_tools"]


def test_agent_stops_after_five_tool_calls() -> None:
    class FakeLLM:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            calls = [
                {
                    "name": "ferramenta_inexistente",
                    "args": {"index": index},
                    "id": str(index),
                    "type": "tool_call",
                }
                for index in range(MAX_TOOL_CALLS + 1)
            ]
            return AIMessage(content="", tool_calls=calls)

    result = AgentRunner(FakeLLM()).run_with_trace("Teste o limite")
    executed = [event for event in result.trace if event["event"] == "tool_call"]
    limits = [event for event in result.trace if event["event"] == "tool_limit_reached"]

    assert len(executed) == MAX_TOOL_CALLS
    assert len(limits) == 1
    assert limits[0]["limit"] == MAX_TOOL_CALLS


def test_evaluator_records_execution_metrics() -> None:
    case = json.loads(CASES.read_text(encoding="utf-8"))[0]
    run = AgentRun(
        "Teclado: 10 unidades em estoque",
        [
            {
                "event": "model_call",
                "sequence": 1,
                "input_tokens": 600,
                "cached_input_tokens": 100,
                "output_tokens": 120,
            },
            {
                "event": "tool_call",
                "tool": "consultar_estoque",
                "arguments": {"name": "Teclado"},
            },
            {
                "event": "tool_result",
                "tool": "consultar_estoque",
                "result": "Teclado: 10 unidades em estoque",
            },
            {
                "event": "model_call",
                "sequence": 2,
                "input_tokens": 400,
                "cached_input_tokens": 0,
                "output_tokens": 80,
            },
        ],
    )

    result = evaluate_case(case, run, duration_ms=123.456)

    assert result.duration_ms == 123.46
    assert result.model_calls == 2
    assert result.tool_calls == 1
    assert result.tool_errors == 0
    assert result.input_tokens == 1000
    assert result.cached_input_tokens == 100
    assert result.output_tokens == 200
    assert result.estimated_cost_usd == 0.0001255
