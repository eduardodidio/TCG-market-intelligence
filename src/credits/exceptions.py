"""Credit system exceptions."""


class InsufficientCreditsError(Exception):
    """Raised when a user does not have enough credits for an operation."""

    def __init__(self, balance: int, cost: int) -> None:
        self.balance = balance
        self.cost = cost
        super().__init__(f"Insufficient credits: have {balance}, need {cost}")
