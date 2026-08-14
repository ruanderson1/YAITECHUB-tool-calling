# Project rules

* Use Python 3.12 and the OpenAI SDK directly.
* Keep the architecture modular: `agent -> tools -> schemas/services`.
* `tools/` only exposes capabilities to the LLM; do not put business logic there.
* `schemas/` validates all LLM-provided arguments with Pydantic.
* `services/` contains inventory business rules and must not depend on the OpenAI SDK.
* The agent supports two tools: `consultar_estoque` and `baixar_estoque`.
* Never allow invalid quantities, nonexistent products, or negative stock.
* LLM calls must use timeout, bounded retries, and exponential backoff.
* Tool failures must be returned explicitly; never report success after a failed action.
* Tracing is mandatory. Record the execution flow needed to debug agent behavior, including model calls, tool calls, tool arguments, tool results, retries and errors.
* Never include secrets or API keys in logs or traces.
* Keep secrets in environment variables and never commit `.env`.
* Prefer simple, typed Python and avoid unnecessary frameworks or abstractions.
* Run relevant tests before considering a change complete.
* Use LangChain for LLM and tool orchestration.

