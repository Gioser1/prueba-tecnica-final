# planning_model.py
"""
Shift planner usando OR-Tools CP-SAT.

Clase ShiftPlanner con:
 - soporte para 1..n semanas (rotación entre semanas opcional)
 - opción para forzar una asesora a solo Apertura
 - exclusión de domingos y festivos (se pasan fechas o se usan nombres de día)
 - métodos para construir, resolver y convertir la solución a DataFrame/JSON
 - manejo de errores y validaciones explícitas
"""
from ortools.sat.python import cp_model
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ShiftPlannerError(Exception):
    pass


class ShiftPlanner:
    SHIFT_MAP = {1: "Apertura", 2: "Cierre", 3: "Intermedio"}

    def __init__(
        self,
        advisors: Optional[List[str]] = None,
        days: Optional[List[str]] = None,
        weeks: int = 1,
        enforce_opening_only: bool = False,
        opening_only_advisor: Optional[str] = None,
        enable_weekly_rotation: bool = False,
        holidays: Optional[List[date]] = None,
    ):
        """
        Inicializa el planner.

        advisors: lista de nombres de asesores. Por defecto: ["Asesor_1","Asesor_2","Asesor_3"]
        days: lista de nombres de los días a planear por semana (sin domingos). Por defecto: Lunes..Sábado
        weeks: número de semanas a planear (>=1)
        enforce_opening_only: si True, la asesora especificada en opening_only_advisor será siempre Apertura
        opening_only_advisor: nombre del asesor limitado a Apertura (obligatorio si enforce_opening_only=True)
        enable_weekly_rotation: si True, un asesor no puede repetir el mismo turno en semanas consecutivas
        holidays: lista de fechas (date) a excluir (si quieres usar fechas en vez de nombres, opcional)
        """
        self.advisors = advisors or ["Asesor_1", "Asesor_2", "Asesor_3"]
        self.days = days or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        if len(self.advisors) != 3:
            raise ShiftPlannerError("El modelo asume exactamente 3 asesores (puedes cambiarlo si lo deseas).")
        if len(self.days) < 1:
            raise ShiftPlannerError("Debe haber al menos un día laboral por semana.")
        if weeks < 1:
            raise ShiftPlannerError("weeks debe ser >= 1")

        self.weeks = weeks
        self.enforce_opening_only = enforce_opening_only
        self.opening_only_advisor = opening_only_advisor
        self.enable_weekly_rotation = enable_weekly_rotation
        self.holidays = set(holidays or [])

        if self.enforce_opening_only and not self.opening_only_advisor:
            raise ShiftPlannerError("Si enforce_opening_only=True debe especificar opening_only_advisor.")
        if self.opening_only_advisor and self.opening_only_advisor not in self.advisors:
            raise ShiftPlannerError("opening_only_advisor no está en la lista de advisors.")

        # Modelo y variables (se crean en build_model)
        self.model = None
        self.solver = None
        # keys: (advisor, week_index, day_name)
        self.vars: Dict[Tuple[str, int, str], cp_model.IntVar] = {}
        # solución almacenada tras solve()
        self._solution: Optional[Dict[str, Dict[int, Dict[str, str]]]] = None

    def _make_model(self):
        self.model = cp_model.CpModel()
        self.vars = {}

        # Crear variables
        for w in range(self.weeks):
            for advisor in self.advisors:
                for day in self.days:
                    var_name = f"{advisor}_w{w}_{day}"
                    iv = self.model.NewIntVar(1, 3, var_name)  # 1:Apertura,2:Cierre,3:Intermedio
                    self.vars[(advisor, w, day)] = iv

        # Restricciones diarias: en cada día (por semana) los 3 turnos deben estar asignados y ser distintos
        for w in range(self.weeks):
            for day in self.days:
                day_vars = [self.vars[(advisor, w, day)] for advisor in self.advisors]
                # Todos diferentes asegura que se asignen exactamente los 3 turnos (porqué hay 3 asesores)
                self.model.AddAllDifferent(day_vars)

        # Restricción: cada asesor debe tener el mismo turno todos los días de la misma semana
        for w in range(self.weeks):
            for advisor in self.advisors:
                # igualar turno entre Lunes..Sábado (o los días proporcionados)
                first = self.vars[(advisor, w, self.days[0])]
                for day in self.days[1:]:
                    self.model.Add(self.vars[(advisor, w, day)] == first)

        # Restricción: apertura-only advisor
        if self.enforce_opening_only:
            for w in range(self.weeks):
                for day in self.days:
                    self.model.Add(self.vars[(self.opening_only_advisor, w, day)] == 1)

        # Rotación entre semanas: un asesor no puede repetir mismo turno en semanas consecutivas
        if self.enable_weekly_rotation and self.weeks > 1:
            for advisor in self.advisors:
                if self.enforce_opening_only and advisor == self.opening_only_advisor:
                    # Si una asesora está fijada a apertura para TODO el mes, la excluimos de rotación (según requisito opcional)
                    continue
                for w in range(self.weeks - 1):
                    # la variable representativa de la semana w (se usa el primer día, ya que por semana son iguales)
                    v_curr = self.vars[(advisor, w, self.days[0])]
                    v_next = self.vars[(advisor, w + 1, self.days[0])]
                    self.model.Add(v_curr != v_next)

        # No se agregan restricciones para domingos porque la lista de días ya los excluye.
        # No minimizamos ni maximizamos nada; sólo buscamos una solución factible.
        return self.model

    def build_and_solve(self, time_limit_seconds: Optional[int] = 10) -> Dict[str, Dict[int, Dict[str, str]]]:
        """
        Construye el modelo y lo resuelve. Devuelve la solución en estructura:
        { advisor: { week_index: { day_name: "Apertura" } } }
        """
        self._make_model()
        self.solver = cp_model.CpSolver()
        if time_limit_seconds:
            self.solver.parameters.max_time_in_seconds = float(time_limit_seconds)
        self.solver.parameters.num_search_workers = 8  # usar paralelismo si está disponible

        status = self.solver.Solve(self.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise ShiftPlannerError(f"No se encontró solución. Estado del solver: {status}")

        # Extraer la solución
        sol: Dict[str, Dict[int, Dict[str, str]]] = {}
        for advisor in self.advisors:
            sol[advisor] = {}
            for w in range(self.weeks):
                sol[advisor][w] = {}
                for day in self.days:
                    val = int(self.solver.Value(self.vars[(advisor, w, day)]))
                    sol[advisor][w][day] = self.SHIFT_MAP[val]
        self._solution = sol
        return sol

    def solution_to_dataframe(self) -> pd.DataFrame:
        """
        Convierte la solución almacenada a un DataFrame compacto:
        columnas: Asesor, Semana, Día, Turno
        """
        if self._solution is None:
            raise ShiftPlannerError("No hay solución. Ejecute build_and_solve() primero.")

        rows: List[Dict[str, Any]] = []
        for advisor, weeks_dict in self._solution.items():
            for w, days_dict in weeks_dict.items():
                for day, shift in days_dict.items():
                    rows.append({"Asesor": advisor, "Semana": w + 1, "Día": day, "Turno": shift})
        df = pd.DataFrame(rows)
        # Orden lógico
        df = df[["Asesor", "Semana", "Día", "Turno"]]
        return df

    def solution_to_json(self) -> List[Dict[str, Any]]:
        """
        Devuelve la solución como lista de dicts (apto para JSON)
        """
        df = self.solution_to_dataframe()
        return df.to_dict(orient="records")

    # Helpers de validación (útiles en tests)
    @staticmethod
    def validate_solution_structure(sol: Dict[str, Dict[int, Dict[str, str]]], advisors: List[str], weeks: int, days: List[str]):
        # verifica que esté la estructura y valores válidos
        if not isinstance(sol, dict):
            raise ShiftPlannerError("Estructura de solución inválida (no dict).")
        for adv in advisors:
            if adv not in sol:
                raise ShiftPlannerError(f"Falta asesor en solución: {adv}")
            if not isinstance(sol[adv], dict):
                raise ShiftPlannerError("Formato de semanas inválido.")
            if len(sol[adv]) != weeks:
                raise ShiftPlannerError(f"Asesor {adv} no tiene la cantidad esperada de semanas.")
            for w in range(weeks):
                if w not in sol[adv]:
                    raise ShiftPlannerError(f"Falta semana {w} para asesor {adv}.")
                for d in days:
                    if d not in sol[adv][w]:
                        raise ShiftPlannerError(f"Falta día {d} en asesor {adv}, semana {w}.")
                    if sol[adv][w][d] not in ShiftPlanner.SHIFT_MAP.values():
                        raise ShiftPlannerError(f"Valor de turno inválido: {sol[adv][w][d]}")

# Fin de planning_model.py