from investigation_engine.copilot.context_builder import (
    get_account_context
)

from investigation_engine.copilot.prompt_builder import (
    build_prompt
)

from investigation_engine.copilot.ollama_client import (
    generate
)

from investigation_engine.rag.retriever import (
    retrieve
)

from investigation_engine.rag.store_case import (
    store_case
)


def generate_report(
    account_id: str
):

    context = get_account_context(
        account_id
    )

    if not context:
        return {
            "error": "Account not found"
        }

    history = retrieve(
        account_id
    )

    prompt = build_prompt(
        context
    )

    if history:

        prompt += "\n\nPREVIOUS CASES\n\n"

        for case in history:
            prompt += case["report"]
            prompt += "\n\n"

    report = generate(
        prompt
    )

    store_case(
        account_id,
        report
    )

    return {
        "account": account_id,
        "context": context,
        "report": report
    }
