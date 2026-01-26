import secrets

from settings import DISCOUNT30, FREEFRIEND, FREESELF


PREFIXES = {
    DISCOUNT30: "SALE30",
    FREEFRIEND: "FRIEND",
    FREESELF: "FREE",
}


def generate_promo_code(prize_type: str) -> str:
    suffix = secrets.token_hex(3).upper()
    return f"{PREFIXES[prize_type]}-{suffix}"
