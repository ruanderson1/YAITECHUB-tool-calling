"""Criacao da LLM configurada para a aplicacao."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


def create_llm(provider: str, model: str) -> BaseChatModel:
    # Integração para agente openai
    if provider.lower() == "openai":
        return ChatOpenAI(model=model,
                          timeout=30,
                          max_retries=2,
                          )


    # Adicionar outros provedores de LLM, se necessario, (não vou adicionar porque não tenho apikey do gemini mas fica de exemplo),
    # obs: pessoa do futuro (provavelmente eu), lembre-se de se adicionar um novo provedor aqui tudo o que tem que fazer é mudar provedor e modelo no .env, adicionar apikey dele e por fim adicionar ao requiriments. Vai ser suficiente para adicionar um novo provedor de LLM funcional no projeto e substituir o que estava em uso.
    #  ex:
    # if provider == "google":
    #         return ChatGoogleGenerativeAI(
    #             model=model,
    #             timeout=30,
    #             max_retries=2,
            # )

    raise ValueError(f"Provedor de LLM nao suportado: {provider}")
