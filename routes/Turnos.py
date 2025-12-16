from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify
from datetime import datetime
from usuarios import usuarios
import sessions

Dashboard = Blueprint("Dashboard", __name__)

def resolver_user_id(form):
    """
    Prioriza user_id si se envió directamente (hidden input).
    Si no, intenta resolver usando temp_id.
    """
    user_id_raw = form.get("user_id")
    if user_id_raw:
        try:
            return int(user_id_raw)
        except ValueError:
            return None

    temp_id = form.get("temp_id") or session.get('temp_id')
    if temp_id:
        return sessions.obtener_user_id(temp_id)
    
    return session.get('user_id')

@Dashboard.route("/verTabla", methods=["GET"])
def ver_tabla():
    temp_id = request.args.get("temp_id", "")
    user_id = sessions.obtener_user_id(temp_id)

    if not temp_id or not user_id:
        return redirect(url_for("inicio.login_page"))

    # Aquí podrías agregar lógica para mostrar la tabla de turnos
    return redirect(url_for("inicio.perfil", temp_id=temp_id))

@Dashboard.route("/VerturnosTable", methods=["GET"])
def ver_turnos_table():
    """Mostrar tabla de turnos - requiere autenticación"""
    temp_id = request.args.get("temp_id") or session.get('temp_id')
    user_id = sessions.obtener_user_id(temp_id) if temp_id else session.get('user_id')
    
    if not user_id or user_id not in usuarios:
        return redirect(url_for("inicio.login_page"))
    
    usuario = usuarios[user_id]
    
    return render_template(
        "VerTurnosTable.html",
        usuario=usuario,
        user_id=user_id,
        temp_id=temp_id
    )

@Dashboard.route("/hora_inicio_trabajo", methods=["POST"])
def hora_inicio_trabajo():
    # resolver id usando el formulario
    user_id = resolver_user_id(request.form)
    temp_id = request.form.get("temp_id", "") or session.get('temp_id', "")

    if not user_id or user_id not in usuarios:
        return redirect(url_for("inicio.login_page"))

    usuario = usuarios[user_id]

    if usuario.get("hora_inicio"):
        return render_template(
            "VerTurnosTable.html",
            usuario=usuario,
            user_id=user_id,
            temp_id=temp_id,
            mensaje="⚠️ Hora de inicio ya registrada",
            error=True
        )

    # Registrar hora de inicio
    usuario["hora_inicio"] = datetime.now()
    usuario["hora_inicio_str"] = usuario["hora_inicio"].strftime("%H:%M:%S")
    
    return render_template(
        "VerTurnosTable.html",
        usuario=usuario,
        user_id=user_id,
        temp_id=temp_id,
        mensaje=f"✓ Hora de inicio registrada: {usuario['hora_inicio_str']}",
        error=False
    )

@Dashboard.route("/hora_fin_trabajo", methods=["POST"])
def hora_fin_trabajo():
    user_id = resolver_user_id(request.form)
    temp_id = request.form.get("temp_id", "") or session.get('temp_id', "")

    if not user_id or user_id not in usuarios:
        return redirect(url_for("inicio.login_page"))

    usuario = usuarios[user_id]

    if not usuario.get("hora_inicio"):
        return render_template(
            "VerTurnosTable.html",
            usuario=usuario,
            user_id=user_id,
            temp_id=temp_id,
            mensaje="⚠️ Primero registre la hora de inicio",
            error=True
        )

    if usuario.get("hora_fin"):
        return render_template(
            "VerTurnosTable.html",
            usuario=usuario,
            user_id=user_id,
            temp_id=temp_id,
            mensaje="⚠️ Hora de fin ya registrada",
            error=True
        )

    # Registrar hora de fin
    usuario["hora_fin"] = datetime.now()
    usuario["hora_fin_str"] = usuario["hora_fin"].strftime("%H:%M:%S")
    
    # Calcular horas trabajadas
    delta = usuario["hora_fin"] - usuario["hora_inicio"]
    horas_trabajadas = round(delta.total_seconds() / 3600, 2)
    usuario["horas_trabajadas"] = usuario.get("horas_trabajadas", 0.0) + horas_trabajadas

    return render_template(
        "VerTurnosTable.html",
        usuario=usuario,
        user_id=user_id,
        temp_id=temp_id,
        mensaje=f"✓ Hora de fin registrada. Trabajaste {horas_trabajadas} horas",
        error=False
    )

@Dashboard.route("/reiniciar_jornada", methods=["POST"])
def reiniciar_jornada():
    """Reiniciar jornada para permitir nuevo registro"""
    user_id = resolver_user_id(request.form)
    temp_id = request.form.get("temp_id", "") or session.get('temp_id', "")

    if not user_id or user_id not in usuarios:
        return redirect(url_for("inicio.login_page"))

    usuario = usuarios[user_id]
    
    # Limpiar horas de inicio y fin
    usuario.pop("hora_inicio", None)
    usuario.pop("hora_fin", None)
    usuario.pop("hora_inicio_str", None)
    usuario.pop("hora_fin_str", None)

    return render_template(
        "VerTurnosTable.html",
        usuario=usuario,
        user_id=user_id,
        temp_id=temp_id,
        mensaje="✓ Jornada reiniciada. Puedes registrar nueva hora de inicio",
        error=False
    )

# Endpoint de API para planificación
@Dashboard.route("/plan", methods=["GET"])
def plan():
    """
    Genera una planeación y devuelve JSON con la lista de filas.
    Parámetros GET:
        - weeks (int, por defecto 4)
        - opening_only (true|false)
        - opening_advisor (string, nombre exacto)
        - rotation (true|false)
        - time_limit (int, segundos, por defecto 10)
    """
    try:
        from planning_model import ShiftPlanner, ShiftPlannerError
        
        def _parse_bool_param(value, default=False):
            if value is None:
                return default
            return str(value).strip().lower() in ("1", "true", "yes", "y", "on")
        
        # Parsear parámetros
        weeks_raw = request.args.get("weeks", "4")
        try:
            weeks = int(weeks_raw)
        except ValueError:
            raise ShiftPlannerError("Parámetro 'weeks' debe ser un entero.")

        opening_only = _parse_bool_param(request.args.get("opening_only", "false"))
        opening_advisor = request.args.get("opening_advisor") or None
        rotation = _parse_bool_param(request.args.get("rotation", "true"))
        time_limit_raw = request.args.get("time_limit", "10")
        
        try:
            time_limit = int(time_limit_raw)
        except ValueError:
            time_limit = 10

        # Construir planner
        planner = ShiftPlanner(
            weeks=weeks,
            enforce_opening_only=opening_only,
            opening_only_advisor=opening_advisor,
            enable_weekly_rotation=rotation,
        )

        sol = planner.build_and_solve(time_limit_seconds=time_limit)
        payload = planner.solution_to_json()
        
        return jsonify({"status": "ok", "plan": payload}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==================== RUTAS ADICIONALES ====================

@Dashboard.route("/", methods=["GET"])
def dashboard_index():
    """Ruta principal del Dashboard"""
    return render_template("Dashboard.html")

@Dashboard.route("/Dashboard", methods=["GET"])
def dashboard_page():
    """Página del Dashboard principal"""
    return render_template("Dashboard.html")

@Dashboard.route("/api/usuarios", methods=["GET"])
def get_usuarios():
    """API para obtener lista de usuarios (sin contraseñas)"""
    usuarios_safe = {}
    for uid, data in usuarios.items():
        usuarios_safe[uid] = {
            "nombre": data.get("nombre"),
            "correo": data.get("correo"),
            "rol": data.get("rol", "Asesor"),
            "horas_trabajadas": data.get("horas_trabajadas", 0.0)
        }
    return jsonify({"status": "ok", "usuarios": usuarios_safe})

@Dashboard.route("/api/mi_info", methods=["GET"])
def get_mi_info():
    """API para obtener información del usuario actual"""
    user_id = session.get('user_id')
    
    if not user_id or user_id not in usuarios:
        return jsonify({"status": "error", "message": "No autenticado"}), 401
    
    usuario = usuarios[user_id]
    return jsonify({
        "status": "ok",
        "usuario": {
            "id": user_id,
            "nombre": usuario.get("nombre"),
            "correo": usuario.get("correo"),
            "rol": usuario.get("rol", "Asesor"),
            "horas_trabajadas": usuario.get("horas_trabajadas", 0.0),
            "hora_inicio": usuario.get("hora_inicio_str"),
            "hora_fin": usuario.get("hora_fin_str")
        }
    })

@Dashboard.route("/export/turnos_csv", methods=["GET"])
def export_turnos_csv():
    """Exportar planificación a CSV"""
    from flask import Response
    import io
    
    # Generar planificación
    try:
        from planning_model import ShiftPlanner
        
        weeks = int(request.args.get("weeks", "4"))
        opening_only = request.args.get("opening_only", "false").lower() == "true"
        opening_advisor = request.args.get("opening_advisor")
        rotation = request.args.get("rotation", "true").lower() == "true"
        
        planner = ShiftPlanner(
            weeks=weeks,
            enforce_opening_only=opening_only,
            opening_only_advisor=opening_advisor,
            enable_weekly_rotation=rotation,
        )
        
        planner.build_and_solve(time_limit_seconds=10)
        df = planner.solution_to_dataframe()
        
        # Convertir a CSV
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=planificacion_turnos.csv"}
        )
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500