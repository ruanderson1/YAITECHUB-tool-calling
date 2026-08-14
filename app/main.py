"""Interacao do agente pelo terminal."""

from app.agent.agentRunner import AgentRunner
from app.core.config import get_settings
from app.core.llm_factory import create_llm
from app.db.seed import seed_database


def main() -> None:
    seed_database()
    settings = get_settings()
    llm = create_llm(settings.llm_provider, settings.llm_model)
    runner = AgentRunner(llm)

    while True:
        try:
            question = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        if question.lower() in {"sair"}:
            print("Encerrando.")
            break
        
        if not question:
            continue

        answer = runner.run(question)
        print(f"Agente: {answer}")


if __name__ == "__main__":
    main()
