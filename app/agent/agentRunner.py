"""Loop explícito de tool calling do agente."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.agent.prompts import AGENT_PROMPT
from app.tools.inventory import baixar_estoque, consultar_estoque


class AgentRunner:
    def __init__(self, llm: BaseChatModel) -> None:
        self.tools: list[BaseTool] = [consultar_estoque, baixar_estoque]
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = llm.bind_tools(self.tools)

    def run(self, question: str) -> str:
        messages: list[BaseMessage] = AGENT_PROMPT.format_messages(question=question)
        executed_decreases: set[tuple[str, object]] = set()
        print("-------[run] messages: ", messages)

        while True:
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return response.text

            for tool_call in response.tool_calls:
                tool = self.tools_by_name.get(tool_call["name"])
                print(f"------- tool: {tool_call['name']} com argumentos: {tool_call['args']}")

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
            print("------ resultado da ferramenta: ", result)
            return result
        except Exception as error:
            return f"Erro ao executar {tool.name}: {error}"
