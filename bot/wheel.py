import random
from settings import PRIZES


def choose_prize() -> str:
    """
    Выбирает приз по весам из settings.PRIZES.
    Веса могут быть любыми положительными числами — не обязательно в сумме 100.
    """
    if not PRIZES:
        raise ValueError("PRIZES в settings не заданы")

    keys = [p[0] for p in PRIZES]
    weights_list = [p[2] for p in PRIZES]

    return random.choices(keys, weights=weights_list, k=1)[0]
