import random
from settings import LOSE, DISCOUNT30, FREEFRIEND, FREESELF


def choose_prize() -> str:
    """
    Выбирает приз с учетом редкости.
    По возрастанию редкости:
    1. Проигрыш (самый частый)
    2. Скидка 30%
    3. Бесплатная стрижка другу
    4. Бесплатная стрижка (самая редкая)
    """
    weights = {
        LOSE: 40,
        DISCOUNT30: 40,
        FREEFRIEND: 10,
        FREESELF: 10,
    }

    prizes = list(weights.keys())
    weights_list = [weights[p] for p in prizes]

    return random.choices(prizes, weights=weights_list, k=1)[0]
