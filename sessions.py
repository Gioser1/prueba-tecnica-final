import time

# Diccionario privado que mapea temp_id -> user_id
_usuarios_activos = {}

def crear_temp_id(user_id: int) -> str:
    temp_id = f"temp_{user_id}_{int(time.time())}"
    _usuarios_activos[temp_id] = user_id
    return temp_id

def obtener_user_id(temp_id: str):
    return _usuarios_activos.get(temp_id)

def borrar_temp_id(temp_id: str):
    _usuarios_activos.pop(temp_id, None)

def obtener_todos():
    # devolver copia para no exponer el dict interno directamente
    return dict(_usuarios_activos)
