"""
calculator.py — Расчётный движок TDABC для вспомогательного персонала

Логика:
  1. Полная стоимость сотрудника = оклад + взносы + KPI + взносы на KPI
  2. Практическая мощность = доступные минуты/мес. (график минус непациентское время)
  3. CCR = стоимость / мощность  (руб./мин)
  4. Стоимость процедуры = CCR × время процедуры

Возвращает структурированные dataclass-результаты — удобно для экспорта в CSV/Excel.
"""

from dataclasses import dataclass, field
from typing import Optional

from config import (
    AssistantConfig, Procedure,
    KpiRevenue, KpiPerProcedure, InsuranceRates,
    MSP_BOUNDARY, MSP_RATE_LOW, MSP_RATE_HIGH,
    WEEKS_PER_MONTH,
)


# ═══════════════════════════════════════════════════════════
# РЕЗУЛЬТАТЫ
# ═══════════════════════════════════════════════════════════

@dataclass
class ProcedureCost:
    """Стоимость одной процедуры."""
    name: str
    minutes: float
    cost_rub: float              # CCR × minutes
    monthly_volume: int
    monthly_total_rub: float     # cost_rub × monthly_volume


@dataclass
class CapacityInfo:
    """Данные о практической мощности."""
    days_per_month: float
    hours_per_day: float
    non_patient_min_per_day: float
    patient_min_per_day: float   # hours_per_day×60 − non_patient_min
    total_patient_min: float     # patient_min_per_day × days_per_month
    utilization_pct: Optional[float]  # % использования мощности (если задан объём)


@dataclass
class CostBreakdown:
    """Разбивка затрат по статьям."""
    salary_gross: float
    insurance_on_salary: float
    insurance_label: str          # описание режима взносов
    kpi_gross: float
    insurance_on_kpi: float
    total_monthly: float


@dataclass
class AssistantResult:
    """Итоговый результат расчёта по одному сотруднику."""
    name: str
    role: str
    cost_breakdown: CostBreakdown
    capacity: CapacityInfo
    ccr: float                        # руб./мин
    procedures: list                  # list[ProcedureCost]
    monthly_procedure_minutes: float  # суммарное время по плану
    kpi_mode: str                     # описание режима KPI


# ═══════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════

def _insurance(amount: float, rates: InsuranceRates = None) -> float:
    """
    Страховые взносы на заданную сумму.
    Если rates не задан — используется дефолтная МСП-схема из констант.
    """
    if amount <= 0:
        return 0.0
    if rates is None:
        rates = InsuranceRates()  # дефолт: МСП

    if rates.mode == "fixed":
        return rates.fixed_amount
    if rates.mode == "standard":
        return amount * rates.rate_standard
    # mode == "msp"
    if amount <= rates.boundary:
        return amount * rates.rate_low
    return rates.boundary * rates.rate_low + (amount - rates.boundary) * rates.rate_high


def _insurance_label(rates) -> str:
    """Краткое описание режима взносов для отчёта."""
    if rates is None or rates.mode == "msp":
        r = rates or __import__('config').InsuranceRates()
        return f"МСП: {r.rate_low*100:.1f}% до {r.boundary:,.0f} руб. + {r.rate_high*100:.1f}% сверху"
    if rates.mode == "standard":
        return f"Стандарт: {rates.rate_standard*100:.1f}% со всей суммы"
    if rates.mode == "fixed":
        return f"Фиксированные: {rates.fixed_amount:,.0f} руб./мес."
    return "Неизвестный режим"


def _kpi_gross(staff: AssistantConfig) -> tuple[float, str]:
    """
    Рассчитывает суммарный KPI gross и возвращает описание режима.
    Если заданы оба варианта — складываются.
    """
    total = 0.0
    modes = []

    if staff.kpi_revenue is not None:
        k = staff.kpi_revenue
        value = k.revenue_per_month * k.pct_of_revenue
        total += value
        modes.append(
            f"% от выручки: {k.pct_of_revenue*100:.4f}% × {k.revenue_per_month:,.0f} руб. = {value:,.0f} руб."
        )

    if staff.kpi_per_procedure is not None:
        k = staff.kpi_per_procedure
        value = k.amount_per_procedure * k.procedures_per_month
        total += value
        modes.append(
            f"За процедуру: {k.amount_per_procedure:,.0f} руб. × {k.procedures_per_month} проц. = {value:,.0f} руб."
        )

    if not modes:
        modes.append("KPI не задан")

    return total, " | ".join(modes)


def _capacity(staff: AssistantConfig) -> CapacityInfo:
    """Практическая мощность в минутах/месяц."""
    days_per_month = staff.days_per_week * WEEKS_PER_MONTH
    patient_min_per_day = staff.hours_per_day * 60 - staff.non_patient_min_per_day
    patient_min_per_day = max(patient_min_per_day, 0)
    total_patient_min = patient_min_per_day * days_per_month

    # Суммарное плановое время по процедурам
    monthly_proc_min = sum(
        p.minutes * p.monthly_volume
        for p in staff.procedures
        if p.monthly_volume > 0
    )
    utilization = (monthly_proc_min / total_patient_min * 100) if total_patient_min > 0 else None

    return CapacityInfo(
        days_per_month          = round(days_per_month, 1),
        hours_per_day           = staff.hours_per_day,
        non_patient_min_per_day = staff.non_patient_min_per_day,
        patient_min_per_day     = round(patient_min_per_day, 1),
        total_patient_min       = round(total_patient_min, 0),
        utilization_pct         = round(utilization, 1) if utilization is not None else None,
    )


# ═══════════════════════════════════════════════════════════
# ОСНОВНАЯ ФУНКЦИЯ РАСЧЁТА
# ═══════════════════════════════════════════════════════════

def calculate(staff: AssistantConfig) -> AssistantResult:
    """
    Полный TDABC-расчёт для одного сотрудника.

    Параметры
    ---------
    staff : AssistantConfig
        Конфиг сотрудника из config.py

    Возвращает
    ----------
    AssistantResult с CCR, стоимостью каждой процедуры и анализом загрузки.
    """
    # 1. Затраты
    ins_salary    = _insurance(staff.salary, staff.insurance)
    kpi_gross, kpi_mode = _kpi_gross(staff)
    ins_kpi       = _insurance(kpi_gross, staff.insurance)
    total_monthly = staff.salary + ins_salary + kpi_gross + ins_kpi

    breakdown = CostBreakdown(
        salary_gross        = staff.salary,
        insurance_on_salary = round(ins_salary, 2),
        insurance_label     = _insurance_label(staff.insurance),
        kpi_gross           = round(kpi_gross, 2),
        insurance_on_kpi    = round(ins_kpi, 2),
        total_monthly       = round(total_monthly, 2),
    )

    # 2. Мощность
    cap = _capacity(staff)

    # 3. CCR
    if cap.total_patient_min <= 0:
        raise ValueError(f"[{staff.name}] Практическая мощность = 0 мин. Проверьте график.")
    ccr = total_monthly / cap.total_patient_min

    # 4. Стоимость процедур
    procedure_results = []
    monthly_proc_min = 0.0
    for proc in staff.procedures:
        cost = ccr * proc.minutes
        monthly_total = cost * proc.monthly_volume
        monthly_proc_min += proc.minutes * proc.monthly_volume
        procedure_results.append(ProcedureCost(
            name              = proc.name,
            minutes           = proc.minutes,
            cost_rub          = round(cost, 2),
            monthly_volume    = proc.monthly_volume,
            monthly_total_rub = round(monthly_total, 2),
        ))

    return AssistantResult(
        name                    = staff.name,
        role                    = staff.role,
        cost_breakdown          = breakdown,
        capacity                = cap,
        ccr                     = round(ccr, 4),
        procedures              = procedure_results,
        monthly_procedure_minutes = round(monthly_proc_min, 0),
        kpi_mode                = kpi_mode,
    )


def calculate_all(staff_list: list) -> list:
    """Рассчитать список сотрудников. Возвращает list[AssistantResult]."""
    return [calculate(s) for s in staff_list]
