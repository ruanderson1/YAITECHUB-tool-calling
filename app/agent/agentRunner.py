"""Loop explícito de tool calling do agente."""

from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.agent.prompts import AGENT_PROMPT
from app.tools.inventory import baixar_estoque, consultar_estoque


MAX_TOOL_CALLS = 5


@dataclass(frozen=True)
class AgentRun:
    answer: str
    trace: list[dict[str, Any]]


class AgentRunner:
    def __init__(self, llm: BaseChatModel) -> None:
        self.tools: list[BaseTool] = [consultar_estoque, baixar_estoque]
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = llm.bind_tools(self.tools)

    def run(self, question: str) -> str:
        return self.run_with_trace(question).answer

    def run_with_trace(self, question: str) -> AgentRun:
        messages: list[BaseMessage] = AGENT_PROMPT.format_messages(question=question)
        executed_decreases: set[tuple[str, object]] = set()
        model_call_count = 0
        tool_call_count = 0
        trace: list[dict[str, Any]] = []

        while True:
            model_call_count += 1
            model_event: dict[str, Any] = {
                "event": "model_call",
                "sequence": model_call_count,
            }
            trace.append(model_event)
            response = self.llm_with_tools.invoke(messages)
            usage = response.usage_metadata or {}
            input_details = usage.get("input_token_details") or {}
            model_event.update(
                {
                    "input_tokens": usage.get("input_tokens", 0),
                    "cached_input_tokens": input_details.get("cache_read", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                }
            )
            messages.append(response)

            if not response.tool_calls:
                answer = response.text
                trace.append({"event": "model_answer", "content": answer})
                return AgentRun(answer=answer, trace=trace)

            for tool_call in response.tool_calls:
                if tool_call_count >= MAX_TOOL_CALLS:
                    answer = (
                        "Não foi possível concluir a solicitação com segurança: "
                        "o limite de chamadas de ferramentas foi atingido."
                    )
                    trace.append(
                        {
                            "event": "tool_limit_reached",
                            "limit": MAX_TOOL_CALLS,
                            "blocked_tool": tool_call["name"],
                            "blocked_arguments": tool_call["args"],
                        }
                    )
                    trace.append({"event": "model_answer", "content": answer})
                    return AgentRun(answer=answer, trace=trace)

                tool_call_count += 1
                tool = self.tools_by_name.get(tool_call["name"])
                trace.append(
                    {
                        "event": "tool_call",
                        "tool": tool_call["name"],
                        "arguments": tool_call["args"],
                    }
                )

                if tool is None:
                    result = f"Erro: ferramenta desconhecida: {tool_call['name']}"
                elif tool.name == "baixar_estoque":
                    decrease_key = (
                        str(tool_call["args"].get("name")).strip().lower(),
                        tool_call["args"].get("quantity"),
                    )
                    if decrease_key in executed_decreases:
                        result = "Operação não repetida: esta baixa já foi executada."
                    else:
                        executed_decreases.add(decrease_key)
                        result = self._invoke_tool(tool, tool_call["args"])
                else:
                    result = self._invoke_tool(tool, tool_call["args"])

                trace.append(
                    {
                        "event": "tool_result",
                        "tool": tool_call["name"],
                        "result": result,
                    }
                )

                messages.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"],
                    )
                )

    @staticmethod
    def _invoke_tool(tool: BaseTool, arguments: dict[str, object]) -> str:
        try:
            result = str(tool.invoke(arguments))
            return result
        except Exception as error:
            return f"Erro ao executar {tool.name}: {error}"
