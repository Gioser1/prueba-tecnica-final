# tests/test_planning.py
import pytest
from planning_model import ShiftPlanner, ShiftPlannerError

def test_basic_week_plan():
    planner = ShiftPlanner(weeks=1)
    sol = planner.build_and_solve(time_limit_seconds=5)
    # estructura válida
    planner.validate_solution_structure(sol, planner.advisors, planner.weeks, planner.days)

    # cada día debe tener exactamente los 3 turnos diferentes
    for w in range(planner.weeks):
        for day in planner.days:
            shifts = {sol[adv][w][day] for adv in planner.advisors}
            assert shifts == set(ShiftPlanner.SHIFT_MAP.values()), "En un día deben aparecer los 3 turnos distintos"

    # cada asesor tiene mismo turno toda la semana
    for adv in planner.advisors:
        week0_shifts = [sol[adv][0][d] for d in planner.days]
        assert len(set(week0_shifts)) == 1

def test_opening_only_enforced():
    opening_advisor = "Asesor_2"
    planner = ShiftPlanner(weeks=1, enforce_opening_only=True, opening_only_advisor=opening_advisor)
    sol = planner.build_and_solve()
    # Asesor_2 siempre Apertura
    for d in planner.days:
        assert sol[opening_advisor][0][d] == "Apertura"

def test_weekly_rotation_two_weeks():
    planner = ShiftPlanner(weeks=2, enable_weekly_rotation=True)
    sol = planner.build_and_solve()
    # validar que los asesores no repiten turno entre semana 0 y 1
    for adv in planner.advisors:
        shift_w0 = sol[adv][0][planner.days[0]]
        shift_w1 = sol[adv][1][planner.days[0]]
        assert shift_w0 != shift_w1

def test_opening_only_with_rotation():
    # si opening_only está activado y rotation activado, la asesor que es apertura no debe romper la rotación
    opening_advisor = "Asesor_1"
    planner = ShiftPlanner(weeks=2, enforce_opening_only=True, opening_only_advisor=opening_advisor, enable_weekly_rotation=True)
    sol = planner.build_and_solve()
    # la asesora de apertura debe ser Apertura ambas semanas
    for w in range(planner.weeks):
        for d in planner.days:
            assert sol[opening_advisor][w][d] == "Apertura"
    # los otros 2 asesores deben rotar entre semanas (no repetir)
    for adv in planner.advisors:
        if adv == opening_advisor:
            continue
        assert sol[adv][0][planner.days[0]] != sol[adv][1][planner.days[0]]
