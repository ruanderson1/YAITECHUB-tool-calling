"""Executa o golden set e produz um relatório estruturado da avaliação."""
from __future__ import annotations

import argparse, json, sys, unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from sqlalchemy import delete

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent.agentRunner import AgentRun, AgentRunner
from app.core.config import get_settings
from app.core.llm_factory import create_llm
from app.db.database import Base, SessionLocal, engine
from app.db.models import Product
from app.db.seed import PRODUCTS

GPT_5_NANO_PRICING_PER_MILLION = {
    "input": 0.05,
    "cached_input": 0.005,
    "output": 0.40,
}

@dataclass(frozen=True)
class CaseResult:
    """Resultado e métricas observadas durante a execução de um caso."""

    id: str
    category: str
    passed: bool
    checks: dict[str, bool]
    answer: str
    trace: list[dict[str, Any]]
    error: str | None = None
    duration_ms: float = 0.0
    model_calls: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

def normalize(value: object) -> str:
    """Normaliza um valor para comparações sem caixa, acentos ou espaços externos."""
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    return "".join(c for c in text if not unicodedata.combining(c))

def load_cases(path: Path) -> list[dict[str, Any]]:
    """Carrega e valida a estrutura mínima do conjunto de avaliação.

    Raises:
        ValueError: Se o arquivo não contiver casos suficientes, campos
            obrigatórios ou identificadores únicos.
    """
    cases = json.loads(path.read_text(encoding="utf-8"))
    required = {"id", "category", "question", "expected_tool"}
    if not isinstance(cases, list) or len(cases) < 20:
        raise ValueError("O golden set deve conter pelo menos 20 casos.")
    if any(not required.issubset(case) for case in cases):
        raise ValueError("Casos precisam de id, category, question e expected_tool.")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Os ids devem ser unicos.")
    return cases

def reset_inventory() -> None:
    """Restaura o catálogo de demonstração para isolar cada caso avaliado.

    Esta operação remove todos os produtos da base configurada e, portanto,
    deve ser usada somente em ambientes de desenvolvimento ou teste.
    """
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.execute(delete(Product))
        session.add_all(Product(name=n, quantity=q) for n, q in PRODUCTS)
        session.commit()

def timestamped_report_path(now: datetime | None = None) -> Path:
    """Gera um caminho de relatório único usando data e hora locais."""
    moment = now or datetime.now().astimezone()
    timestamp = moment.strftime("%Y-%m-%d_%H-%M-%S_%f")
    return ROOT / "evals" / f"golden_report_{timestamp}.json"

def evaluate_case(
    case: dict[str, Any],
    run: AgentRun,
    duration_ms: float = 0.0,
    model: str = "gpt-5-nano",
) -> CaseResult:
    """Compara uma execução com as expectativas e calcula suas métricas.

    A aprovação exige que todas as verificações declaradas pelo caso sejam
    satisfeitas. O custo só é estimado quando há uma tabela conhecida para o
    modelo informado.
    """
    calls = [e for e in run.trace if e["event"] == "tool_call"]
    tools = [e["tool"] for e in calls]
    expected = case["expected_tool"]
    checks = {
        "tool": expected in tools if expected else not tools,
        "forbidden_tools": not set(case.get("forbidden_tools", [])).intersection(tools),
    }
    expected_args = case.get("expected_args", {})
    if expected and expected_args:
        matching = [e for e in calls if e["tool"] == expected]
        checks["arguments"] = bool(matching) and any(all(normalize(call["arguments"].get(k)) == normalize(v) for k, v in expected_args.items()) for call in matching)
    answer = normalize(run.answer)
    checks["answer_any_of"] = all(any(normalize(term) in answer for term in group) for group in case.get("answer_any_of", []))
    checks["answer_must_not_include"] = all(normalize(term) not in answer for term in case.get("answer_must_not_include", []))
    model_calls = sum(event["event"] == "model_call" for event in run.trace)
    model_events = [event for event in run.trace if event["event"] == "model_call"]
    input_tokens = sum(int(event.get("input_tokens", 0)) for event in model_events)
    cached_input_tokens = sum(
        int(event.get("cached_input_tokens", 0)) for event in model_events
    )
    output_tokens = sum(int(event.get("output_tokens", 0)) for event in model_events)
    uncached_input_tokens = max(0, input_tokens - cached_input_tokens)
    estimated_cost_usd = 0.0
    if model == "gpt-5-nano" or model.startswith("gpt-5-nano-"):
        estimated_cost_usd = (
            uncached_input_tokens * GPT_5_NANO_PRICING_PER_MILLION["input"]
            + cached_input_tokens
            * GPT_5_NANO_PRICING_PER_MILLION["cached_input"]
            + output_tokens * GPT_5_NANO_PRICING_PER_MILLION["output"]
        ) / 1_000_000
    tool_calls = len(calls)
    tool_errors = sum(
        event["event"] == "tool_result"
        and normalize(event.get("result", "")).startswith("erro")
        for event in run.trace
    )
    return CaseResult(
        case["id"],
        case["category"],
        all(checks.values()),
        checks,
        run.answer,
        run.trace,
        duration_ms=round(duration_ms, 2),
        model_calls=model_calls,
        tool_calls=tool_calls,
        tool_errors=tool_errors,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=round(estimated_cost_usd, 10),
    )

def main() -> int:
    """Executa todos os casos e retorna sucesso quando o score atinge o limite."""
    parser = argparse.ArgumentParser(description="Avalia o agente com o golden set.")
    parser.add_argument("--cases", type=Path, default=ROOT / "evals" / "golden_set.json")
    parser.add_argument(
        "--output",
        type=Path,
        help="Caminho opcional; por padrao, usa um nome unico com data e hora.",
    )
    parser.add_argument("--fail-under", type=float, default=.80)
    args = parser.parse_args()
    if not 0 <= args.fail_under <= 1:
        parser.error("--fail-under deve estar entre 0 e 1")
    output_path = args.output or timestamped_report_path()
    cases, settings = load_cases(args.cases), get_settings()
    runner, results = AgentRunner(create_llm(settings.llm_provider, settings.llm_model)), []
    for index, case in enumerate(cases, 1):
        started_at = perf_counter()
        try:
            reset_inventory()
            run = runner.run_with_trace(case["question"])
            result = evaluate_case(
                case,
                run,
                duration_ms=(perf_counter() - started_at) * 1000,
                model=settings.llm_model,
            )
        except Exception as error:
            result = CaseResult(
                case["id"],
                case["category"],
                False,
                {},
                "",
                [],
                str(error),
                duration_ms=round((perf_counter() - started_at) * 1000, 2),
            )
        results.append(result)
        print(f"[{index:02}/{len(cases)}] {'PASS' if result.passed else 'FAIL'} {case['id']}")
    passed, total = sum(r.passed for r in results), len(results)
    score = passed / total
    total_model_calls = sum(r.model_calls for r in results)
    total_cost_usd = sum(r.estimated_cost_usd for r in results)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "score": score,
            "duration_ms": round(sum(r.duration_ms for r in results), 2),
            "average_duration_ms": round(
                sum(r.duration_ms for r in results) / total, 2
            ),
            "model_calls": total_model_calls,
            "tool_calls": sum(r.tool_calls for r in results),
            "tool_errors": sum(r.tool_errors for r in results),
            "input_tokens": sum(r.input_tokens for r in results),
            "cached_input_tokens": sum(r.cached_input_tokens for r in results),
            "output_tokens": sum(r.output_tokens for r in results),
            "estimated_cost_usd": round(total_cost_usd, 10),
            "average_cost_per_model_call_usd": round(
                total_cost_usd / total_model_calls, 10
            )
            if total_model_calls
            else 0.0,
            "average_cost_per_case_usd": round(total_cost_usd / total, 10),
        },
        "results": [asdict(r) for r in results],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nScore: {score:.1%} ({passed}/{total}). Relatorio: {output_path}")
    return 0 if score >= args.fail_under else 1

if __name__ == "__main__":
    raise SystemExit(main())
