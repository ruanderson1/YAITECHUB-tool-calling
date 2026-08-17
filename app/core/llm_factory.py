"""Construção do modelo de linguagem usado pelo agente."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


def create_llm(provider: str, model: str) -> BaseChatModel:
    """Cria um chat model com timeout e número de tentativas controlados.

    Args:
        provider: Identificador do provedor configurado no ambiente.
        model: Nome do modelo disponibilizado pelo provedor.

    Returns:
        Modelo compatível com a interface de chat e tool calling do LangChain.

    Raises:
        ValueError: Se o provedor informado não possuir integração.
    """
    if provider.lower() == "openai":
        return ChatOpenAI(
            model=model,
            timeout=30,
            max_retries=2,
        )

    raise ValueError(f"Provedor de LLM nao suportado: {provider}")
