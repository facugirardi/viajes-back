from flask import Blueprint, jsonify, request
from db import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime

bp = Blueprint('routes', __name__)
SECRET_KEY = 'vayafgav' 

@bp.route('/users', methods=['POST'])
def create_user():
    """Crear un nuevo usuario."""
    try:
        data = request.get_json()
        if not data.get('name') or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

        db = get_db()
        query = f"""
            INSERT INTO users (name, email, password)
            VALUES ('{data['name']}', '{data['email']}', '{hashed_password}')
        """
        db.run(query)

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
        query = f"SELECT id, name, email, password FROM users WHERE email = '{email}'"

        users = db.run(query)
        if not users:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Tomar el primer usuario de la lista
        user = users[0]  # Esto devuelve una tupla como (id, name, email, password)

        # Convertir la tupla en un diccionario
        user_dict = {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "password": user[3],
        }
        # Verificar la contraseña
        if not check_password_hash(user_dict['password'], password):
            return jsonify({"error": "Contraseña incorrecta"}), 401

        # Generar JWT
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

@bp.route('/packages', methods=['GET'])
def get_packages():
    """Obtener todos los paquetes turísticos."""
    db = get_db()
    query = "SELECT * FROM packages"
    results = db.run(query)
    return jsonify(results)

@bp.route('/contact_messages', methods=['POST'])
def create_contact_message():
    """Crear un mensaje de contacto."""
    try:
        # Obtener datos del cliente
        data = request.get_json()

        # Validar datos
        if not data.get('name') or not data.get('email') or not data.get('message'):
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        # Conectar a la base de datos
        db = get_db()

        # Consulta SQL
        query = f"""
            INSERT INTO contact_messages (name, email, message)
            VALUES ('{data['name']}', '{data['email']}', '{data['message']}')
            RETURNING id
        """

        result = db.run(query)
        print(result)
        return jsonify({"id": result[0][0]}), 201

    except Exception as e:
        print(f"Error al insertar mensaje de contacto: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500

 
@bp.route('/messages', methods=['GET'])
def get_contact_messages():
    """Obtener todos los mensajes de contacto."""
    try:
        db = get_db()
        query = "SELECT id, name, email, message, category FROM contact_messages ORDER BY id DESC"
        result = db.run(query)

        messages = [
            {"id": row[0], "name": row[1], "email": row[2], "message": row[3], "category": row[4]}
            for row in result
        ]
        return jsonify(messages), 200

    except Exception as e:
        print(f"Error al obtener mensajes de contacto: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500
