"""Token budget management - Backend logic."""


class TokenBudgetManager:
  """Manages token usage tracking and budget limits."""

  def __init__(self, max_token_limit: int = 0):
    """
    Initialize the Token Budget Manager.

    Args:
        max_token_limit: Maximum token limit for the budget (default: 0, will be set by LLM)
    """
    self._total_tokens_used: int = 0
    self._max_token_limit: int = max_token_limit

  @property
  def total_tokens_used(self) -> int:
    """Get the total tokens used."""
    return self._total_tokens_used

  @property
  def max_token_limit(self) -> int:
    """Get the maximum token limit."""
    return self._max_token_limit

  @max_token_limit.setter
  def max_token_limit(self, value: int) -> None:
    """Set the maximum token limit."""
    self._max_token_limit = value

  def update_from_llm_response(
    self, tokens_used: int, max_content_length: int
  ) -> None:
    """
    Update token budget from LLM response payload.

    Args:
        tokens_used: Number of tokens used in the response (0 if streaming)
        max_content_length: Maximum context length from the LLM
    """
    # Update max token limit
    self.max_token_limit = max_content_length

    # Only update total tokens when the stream is completed
    if tokens_used > 0:
      self._total_tokens_used = tokens_used

  def reset(self) -> None:
    """Reset the token usage counter."""
    self._total_tokens_used = 0

  def get_budget_stats(self) -> dict:
    """
    Get current budget statistics.

    Returns:
        Dictionary with budget_spent, total_budget, and remaining_budget
    """
    return {
      "budget_spent": self._total_tokens_used,
      "total_budget": self._max_token_limit,
      "remaining_budget": max(
        0, self._max_token_limit - self._total_tokens_used
      ),
    }
