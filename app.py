from flask import Flask
from routes.inicio import inicio  # Importar usuarios_activos también
from routes.Turnos import Dashboard

app = Flask(__name__)

app.register_blueprint(inicio)
app.register_blueprint(Dashboard)



if __name__ == "__main__":
    app.run(debug=True)

