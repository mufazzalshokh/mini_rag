def estimate_costs(
    prompt_tokens: int,
    completion_tokens: int,
    prompt_rate_per_1k: float = 0.0015,
    completion_rate_per_1k: float = 0.002
) -> float:
    """
    Estimate cost in USD using OpenAI pricing:
      – prompt: $0.0015 per 1K tokens
      – completion: $0.002 per 1K tokens
    """
    return (prompt_tokens * prompt_rate_per_1k + completion_tokens * completion_rate_per_1k) / 1000
