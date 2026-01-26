from zoneinfo import ZoneInfo

WORK_START = "09:00"
WORK_END = "18:00"

SERVICE_DURATION_MIN = 60

TIMEZONE = ZoneInfo("Asia/Yekaterinburg")

PRICE = 1500

RETENTION_DAYS = 14

LOSE = "lose"
DISCOUNT30 = "discount_30"
FREEFRIEND = "free_friend"
FREESELF = "free_self"

PRIZES = [
    (LOSE, "❌ Ничего", 10),
    (DISCOUNT30, "💸 Скидка 30%", 40),
    (FREEFRIEND, "🎁 Бесплатная стрижка другу", 40),
    (FREESELF, "👑 Бесплатная стрижка для вас", 10),
]
