from flask import Blueprint, request, render_template, redirect, url_for
from usuarios import usuarios
import sessions

inicio = Blueprint("inicio", __name__)

def verificar_usuario(correo: str, contraseña: str):
    for uid, usuario in usuarios.items():
        if (
            usuario["correo"] == correo
            and usuario["contraseña"] == contraseña
            and usuario["activo"]
        ):
            return uid
    return None

@inicio.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@inicio.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@inicio.route("/LoginVerify", methods=["POST"])
def login_verify():
    correo = request.form.get("correo", "").strip()
    contraseña = request.form.get("contraseña", "").strip()

    if not correo or not contraseña:
        # volver a la página de login con mensaje
        return render_template("login.html", error="Todos los campos son obligatorios")

    user_id = verificar_usuario(correo, contraseña)
    if not user_id:
        return render_template("login.html", error="Credenciales inválidas")

    temp_id = sessions.crear_temp_id(user_id)
    # redirigir a perfil incluyendo temp_id en querystring
    return redirect(url_for("inicio.perfil", temp_id=temp_id))

@inicio.route("/perfil", methods=["GET"])
def perfil():
    temp_id = request.args.get("temp_id", "")
    user_id = sessions.obtener_user_id(temp_id)

    if not temp_id or not user_id:
        # no autorizado -> login
        return redirect(url_for("inicio.login_page"))

    usuario = usuarios.get(user_id)
    if not usuario:
        return redirect(url_for("inicio.login_page"))

    mensaje = request.args.get("mensaje")
    error = request.args.get("error", "0") == "1"

    # pasar también user_id en el template para meterlo como hidden input
    return render_template(
        "perfil.html",
        usuario=usuario,
        temp_id=temp_id,
        user_id=user_id,
        mensaje=mensaje,
        error=error
    )

@inicio.route("/logout", methods=["GET"])
def logout():
    temp_id = request.args.get("temp_id")
    if temp_id:
        sessions.borrar_temp_id(temp_id)
    return redirect(url_for("inicio.home"))

# función de utilidad exportada para otros módulos (si hace falta)
def obtener_usuarios_activos():
    return sessions.obtener_todos()
