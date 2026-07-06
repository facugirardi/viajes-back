import datetime

import jwt
from flask import jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db
from routes import bp
from routes.helpers import SECRET_KEY, login_required


@bp.route('/users', methods=['POST'])
@login_required
def create_user():
    """Crear un nuevo usuario."""
    try:
        data = request.get_json()
        if not data.get('name') or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

        db = get_db()
        db.run(
            "INSERT INTO users (name, email, password) VALUES (:name, :email, :password)",
            name=data['name'], email=data['email'], password=hashed_password
        )

        return jsonify({"message": "Usuario creado exitosamente"}), 201
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        return jsonify({"error": "Error al crear el usuario"}), 500


@bp.route('/login', methods=['POST'])
def login():
    """Iniciar sesión."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email y contraseña son obligatorios"}), 400

        db = get_db()
        users = db.run("SELECT id, name, email, password FROM users WHERE email = :email", email=email)
        if not users:
            return jsonify({"error": "Usuario no encontrado"}), 404

        user = users[0]

        user_dict = {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "password": user[3],
        }
        if not check_password_hash(user_dict['password'], password):
            return jsonify({"error": "Contraseña incorrecta"}), 401

        token = jwt.encode(
            {"id": user_dict['id'], "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
            SECRET_KEY,
            algorithm="HS256"
        )
        return jsonify({
            "token": token,
            "user": {
                "id": user_dict['id'],
                "name": user_dict['name'],
                "email": user_dict['email']
            }
        }), 200
    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        return jsonify({"error": "Error al procesar la solicitud"}), 500
