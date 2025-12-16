Prueba Técnica – Planeación de Turnos
Descripción

Este proyecto implementa un sistema de planificación de turnos usando Python y OR-Tools CP-SAT.
Permite asignar turnos a tres asesores en un punto de venta cumpliendo las siguientes reglas:

Cada asesor tiene un turno único por día: Apertura, Cierre o Intermedio.

Todos los asesores tienen asignación de turno.

El mismo turno se mantiene durante toda la semana.

Domingos y festivos no se planifican.

Se puede activar rotación semanal opcional y/o forzar a una asesora a solo Apertura.

La aplicación incluye una interfaz web en Flask para visualizar la planificación.

Requisitos

Python 3.9+

OR-Tools

Flask

Pandas

Instalar dependencias:

pip install -r requirements.txt

Cómo ejecutar

Activar el entorno virtual (recomendado):

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate


Ejecutar la aplicación:

python app.py


Abrir el navegador en:

http://127.0.0.1:5000/


Usar el botón para generar y visualizar la planificación de turnos.

Estructura del proyecto
├─ app.py                # Entrada principal de la aplicación Flask
├─ planning_model.py     # Clase ShiftPlanner con modelo CP-SAT
├─ routes/
│   ├─ inicio.py         # Rutas de inicio
│   └─ Turnos.py         # Rutas para mostrar planificación
├─ templates/            # HTML para la app Flask
└─ requirements.txt

Uso de la clase ShiftPlanner
from planning_model import ShiftPlanner

planner = ShiftPlanner(weeks=2, enforce_opening_only=True, opening_only_advisor="Asesor_1")
planner.build_and_solve()
df = planner.solution_to_dataframe()
print(df)

Licencia

Proyecto para fines de prueba técnica.
