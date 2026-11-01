from app.schemas.top_matches import TopMatches


def get_current_top_matches() -> TopMatches:
    """Current week's TOP 5.

    Chat 01 only fixes the contract. Until the TOP 5 policy (P-06) is decided and chat 04
    adds `weekly_top_matches`, this always returns no period and no items, so the strip
    shows its empty state and never presents a past week as this week's ranking (TOP-003).
    """
    return TopMatches(period=None, items=[])
