from typing import Any

from app.knowledge.recovery_policies import RECOVERY_POLICIES


def _tokenize(text: str) -> set[str]:
    """
    Convert text into a simple set of searchable tokens.
    """
    return {
        word.strip(".,:;!?()[]{}\"'")
        for word in text.lower().split()
        if len(word.strip(".,:;!?()[]{}\"'")) > 2
    }


def retrieve_policies(
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant recovery policies.

    This is intentionally deterministic for the initial backend.
    The retrieval interface can later be replaced by vector search
    without changing the agent architecture.
    """

    query_tokens = _tokenize(query)

    scored_policies = []

    for policy in RECOVERY_POLICIES:
        policy_text = (
            f"{policy['title']} "
            f"{policy['category']} "
            f"{policy['content']}"
        )

        policy_tokens = _tokenize(policy_text)

        overlap = query_tokens.intersection(policy_tokens)

        score = len(overlap)

        if score > 0:
            scored_policies.append(
                {
                    "policy": policy,
                    "score": score,
                }
            )

    scored_policies.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return [
        item["policy"]
        for item in scored_policies[:top_k]
    ]