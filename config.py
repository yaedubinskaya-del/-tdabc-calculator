"""
config.py — Исходные данные для TDABC-калькулятора вспомогательного персонала
Частная клиника, 2026 г.

KPI поддерживает два режима:
  • "revenue"       — % от выручки подразделения за месяц
  • "per_procedure" — фиксированная сумма за каждую выполненную процедуру

Редактируйте только этот файл, остальные менять не нужно.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


# ═══════════════════════════════════════════════════════════
# КОНСТАНТЫ — СТРАХОВЫЕ ВЗНОСЫ МСП (2025)
# 30,2% с суммы до МРОТ (88 000 руб.), 15,1% — с остатка
# Используются как дефолтные значения, если InsuranceRates не задан
# ═══════════════════════════════════════════════════════════
MSP_BOUNDARY  = 88_000
MSP_RATE_LOW  = 0.302
MSP_RATE_HIGH = 0.151

# Среднее число недель в месяце
WEEKS_PER_MONTH = 4.333


# ═══════════════════════════════════════════════════════════
# НАСТРОЙКИ СТРАХОВЫХ ВЗНОСОВ (на сотрудника)
# ═══════════════════════════════════════════════════════════
@dataclass
class InsuranceRates:
    """
    Ставки страховых взносов для конкретного сотрудника.
    По умолчанию used MSP-схема (льготные ставки для МСП).

    Режимы:
      "msp"      — льготная ставка МСП: rate_low до boundary, rate_high сверху
      "standard" — единая общая ставка rate_standard со всей суммы оклада
      "fixed"    — фиксированная сумма взносов в рублях (fixed_amount)

    Примеры:
      InsuranceRates()                        # МСП по умолчанию (30,2% / 15,1%)
      InsuranceRates(mode="standard",
                     rate_standard=0.302)     # 30,2% со всего оклада (не МСП)
      InsuranceRates(mode="fixed",
                     fixed_amount=20_000)     # фиксированные 20 000 руб./мес.
    """
    mode: Literal["msp", "standard", "fixed"] = "msp"

    # Параметры режима "msp"
    boundary:  float = MSP_BOUNDARY   # МРОТ-порог, руб. (менять при смене МРОТ)
    rate_low:  float = MSP_RATE_LOW   # ставка до boundary (0.302 = 30,2%)
    rate_high: float = MSP_RATE_HIGH  # ставка свыше boundary (0.151 = 15,1%)

    # Параметры режима "standard"
    rate_standard: float = 0.302      # единая ставка со всей суммы

    # Параметры режима "fixed"
    fixed_amount: float = 0.0         # фиксированная сумма взносов, руб./мес.


# ═══════════════════════════════════════════════════════════
# ПРОЦЕДУРА
# ═══════════════════════════════════════════════════════════
@dataclass
class Procedure:
    """Одна медицинская процедура/услуга."""
    name: str              # название
    minutes: float         # время участия ассистента (мин)
    monthly_volume: int = 0  # плановый объём в месяц (для проверки загрузки)


# ═══════════════════════════════════════════════════════════
# МОДЕЛИ KPI
# ═══════════════════════════════════════════════════════════
@dataclass
class KpiRevenue:
    """KPI рассчитывается как процент от выручки подразделения."""
    type: Literal["revenue"] = "revenue"
    # Формула: kpi_gross = revenue × pct_of_revenue
    # Пример: 0.6% × 1% = 0.00006 → pct_of_revenue = 0.00006
    pct_of_revenue: float = 0.00006
    revenue_per_month: float = 4_750_000  # руб./мес. — выручка подразделения


@dataclass
class KpiPerProcedure:
    """KPI рассчитывается как фиксированная сумма за процедуру."""
    type: Literal["per_procedure"] = "per_procedure"
    amount_per_procedure: float = 500.0   # руб. за одну выполненную процедуру
    procedures_per_month: int   = 100     # плановое кол-во процедур в месяц


# ═══════════════════════════════════════════════════════════
# СОТРУДНИК
# ═══════════════════════════════════════════════════════════
@dataclass
class AssistantConfig:
    """Полное описание одного сотрудника вспомогательного персонала."""

    # --- Кто ---
    name: str                        # ФИО или код сотрудника
    role: str                        # "ассистент", "медсестра", "санитар" и т.д.

    # --- Оклад ---
    salary: float                    # оклад gross, руб./мес.

    # --- Страховые взносы (None = дефолтная схема МСП из констант) ---
    insurance: Optional[InsuranceRates] = None
    # Примеры:
    #   insurance = None                              → МСП (30,2%/15,1%)
    #   insurance = InsuranceRates()                  → МСП явно
    #   insurance = InsuranceRates(mode="standard",
    #                              rate_standard=0.302) → 30,2% со всего оклада
    #   insurance = InsuranceRates(mode="fixed",
    #                              fixed_amount=25_000)  → фиксированные 25 000 руб.

    # --- График (изменяется свободно) ---
    days_per_week: float = 5.0       # рабочих дней в неделю
    hours_per_day: float = 8.0       # часов в смене
    non_patient_min_per_day: float = 45.0  # непациентское время (мин/смену):
                                           # обед + подготовка + уборка + документация

    # --- KPI --- выберите один или оба варианта (None = не используется)
    kpi_revenue: Optional[KpiRevenue] = None
    kpi_per_procedure: Optional[KpiPerProcedure] = None

    # --- Список процедур ---
    procedures: list = field(default_factory=list)  # список объектов Procedure


# ═══════════════════════════════════════════════════════════
# ПРИМЕР ДАННЫХ — редактируйте под свою клинику
# ═══════════════════════════════════════════════════════════

PROCEDURES_EXAMPLE = [
    Procedure("Гистероскопия",                  minutes=20, monthly_volume=50),
    Procedure("Большая операция",               minutes=60, monthly_volume=10),
    Procedure("Пункция / малая манипуляция",    minutes=20, monthly_volume=40),
    Procedure("Первичный приём (ассистент)",    minutes=10, monthly_volume=80),
    Procedure("Перевязка",                      minutes=15, monthly_volume=30),
]

# --- Сотрудник 1: медсестра операционного блока, KPI от выручки ---
NURSE_REVENUE_KPI = AssistantConfig(
    name        = "Иванова А.А.",
    role        = "Операционная медсестра",
    salary      = 115_000,
    days_per_week = 3,
    hours_per_day = 7,
    non_patient_min_per_day = 45,
    kpi_revenue = KpiRevenue(
        pct_of_revenue  = 0.00006,       # 0,6% от 1% от выручки
        revenue_per_month = 4_750_000,
    ),
    procedures  = PROCEDURES_EXAMPLE,
)

# --- Сотрудник 2: ассистент на приёме, KPI за процедуру ---
ASSISTANT_PER_PROC_KPI = AssistantConfig(
    name        = "Петрова Б.Б.",
    role        = "Ассистент врача",
    salary      = 80_000,
    days_per_week = 5,
    hours_per_day = 8,
    non_patient_min_per_day = 45,
    kpi_per_procedure = KpiPerProcedure(
        amount_per_procedure = 300,      # 300 руб. за процедуру
        procedures_per_month = 100,
    ),
    procedures  = PROCEDURES_EXAMPLE,
)

# --- Сотрудник 3: медсестра с обоими видами KPI ---
NURSE_BOTH_KPI = AssistantConfig(
    name        = "Сидорова В.В.",
    role        = "Медсестра процедурного кабинета",
    salary      = 70_000,
    days_per_week = 5,
    hours_per_day = 8,
    non_patient_min_per_day = 50,
    kpi_revenue = KpiRevenue(
        pct_of_revenue    = 0.00004,
        revenue_per_month = 3_000_000,
    ),
    kpi_per_procedure = KpiPerProcedure(
        amount_per_procedure = 150,
        procedures_per_month = 80,
    ),
    procedures  = PROCEDURES_EXAMPLE,
)

# Список всех сотрудников для расчёта
ALL_STAFF = [
    NURSE_REVENUE_KPI,
    ASSISTANT_PER_PROC_KPI,
    NURSE_BOTH_KPI,
]
