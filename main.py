from flask import Flask
from db import close_db
from routes import bp
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["https://vayaturismo.com", "http://vayaturismo.com", "http://localhost:3000"])  # Permitir solicitudes desde el cliente

    # Registrar las rutas
    app.register_blueprint(bp)

    # Cerrar la conexión a la base de datos al terminar la solicitud
    app.teardown_appcontext(close_db)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
