"""
run.py — Запуск калькулятора и вывод результатов

Использование:
    python run.py             # текстовый отчёт в терминал
    python run.py --csv       # сохранить результаты в results.csv
    python run.py --gui       # открыть электронную форму ввода
    python run.py --web       # открыть веб-форму (локально)
    python run.py --web --share  # веб-форма + публичная ссылка

Редактировать нужно только config.py — список сотрудников и процедур.
"""

import sys
import csv
import os
from calculator import calculate_all, AssistantResult
from config import ALL_STAFF

SEP = "─" * 72


def print_result(r: AssistantResult) -> None:
    """Красивый текстовый отчёт по одному сотруднику."""
    print(f"\n{'═' * 72}")
    print(f"  {r.role}: {r.name}")
    print(f"{'═' * 72}")

    # Затраты
    b = r.cost_breakdown
    print(f"\n  ЗАТРАТЫ (руб./мес.)")
    print(f"  {SEP}")
    print(f"  {'Оклад (gross)':<40} {b.salary_gross:>12,.0f}")
    print(f"  {'Страховые взносы':<40} {b.insurance_on_salary:>12,.0f}")
    print(f"    → Режим: {b.insurance_label}")
    print(f"  {'KPI — gross':<40} {b.kpi_gross:>12,.2f}")
    print(f"    → {r.kpi_mode}")
    print(f"  {'Взносы на KPI':<40} {b.insurance_on_kpi:>12,.2f}")
    print(f"  {SEP}")
    print(f"  {'ИТОГО для работодателя':<40} {b.total_monthly:>12,.2f}")

    # Мощность
    c = r.capacity
    print(f"\n  ПРАКТИЧЕСКАЯ МОЩНОСТЬ")
    print(f"  {SEP}")
    print(f"  {'Рабочих дней/мес.':<40} {c.days_per_month:>12.1f}")
    print(f"  {'Часов в смене':<40} {c.hours_per_day:>12.1f}")
    print(f"  {'Непациентское время (мин/смену)':<40} {c.non_patient_min_per_day:>12.0f}")
    print(f"  {'Доступно пациентских мин/смену':<40} {c.patient_min_per_day:>12.1f}")
    print(f"  {'Итого доступных мин/мес.':<40} {c.total_patient_min:>12.0f}")

    # CCR
    print(f"\n  CCR (ставка стоимости мощности)")
    print(f"  {SEP}")
    print(f"  {'CCR = стоимость / мощность':<40} {r.ccr:>11.4f} руб./мин")

    # Процедуры
    print(f"\n  СТОИМОСТЬ ПРОЦЕДУР")
    print(f"  {SEP}")
    header = f"  {'Процедура':<32} {'Мин':>5}  {'Стоим.':>9}  {'Объём':>6}  {'Итого/мес.':>12}"
    print(header)
    print(f"  {SEP}")
    for p in r.procedures:
        print(
            f"  {p.name:<32} {p.minutes:>5.0f}  "
            f"{p.cost_rub:>8.2f}р  {p.monthly_volume:>6}  "
            f"{p.monthly_total_rub:>11,.2f}р"
        )
    print(f"  {SEP}")

    # Загрузка
    print(f"\n  АНАЛИЗ ЗАГРУЗКИ")
    print(f"  {SEP}")
    print(f"  {'Суммарно мин/мес. на процедуры':<40} {r.monthly_procedure_minutes:>12.0f}")
    print(f"  {'Практическая мощность (мин/мес.)':<40} {c.total_patient_min:>12.0f}")
    if c.utilization_pct is not None:
        flag = "  ⚠️  НЕДОЗАГРУЗКА" if c.utilization_pct < 50 else ""
        print(f"  {'Использование мощности (%)':<40} {c.utilization_pct:>11.1f}%{flag}")
    print()


def save_csv(results: list, path: str = "results.csv") -> None:
    """Сохранить стоимость процедур в CSV для вставки в техкарту."""
    rows = []
    for r in results:
        for p in r.procedures:
            rows.append({
                "Сотрудник":            r.name,
                "Должность":            r.role,
                "Оклад":                r.cost_breakdown.salary_gross,
                "Взносы":               r.cost_breakdown.insurance_on_salary,
                "KPI":                  r.cost_breakdown.kpi_gross,
                "Итого фот/мес":        r.cost_breakdown.total_monthly,
                "Мощность мин/мес":     r.capacity.total_patient_min,
                "CCR руб/мин":          r.ccr,
                "Процедура":            p.name,
                "Время мин":            p.minutes,
                "Стоимость руб":        p.cost_rub,
                "Объём/мес":            p.monthly_volume,
                "Сумма/мес":            p.monthly_total_rub,
            })

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ Результаты сохранены: {os.path.abspath(path)}")


def main():
    if "--web" in sys.argv:
        from web_app import launch_web

        launch_web(share="--share" in sys.argv)
        return

    if "--gui" in sys.argv:
        from web_app import launch_web

        launch_web(share=False)
        return

    results = calculate_all(ALL_STAFF)

    for r in results:
        print_result(r)

    if "--csv" in sys.argv:
        save_csv(results)


if __name__ == "__main__":
    main()
