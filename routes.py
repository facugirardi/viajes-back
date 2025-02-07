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

@bp.route('/contact_messages', methods=['POST'])
def create_contact_message():
    """Crear un mensaje de contacto."""
    try:
        # Obtener datos del cliente
        data = request.get_json()

        # Validar datos
        if not data.get('name') or not data.get('email') or not data.get('message') or not data.get('category'):
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        # Conectar a la base de datos
        db = get_db()

        # Consulta SQL
        query = f"""
            INSERT INTO contact_messages (name, email, message, category)
            VALUES ('{data['name']}', '{data['email']}', '{data['message']}', '{data['category']}')
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
        query = "SELECT id, name, email, message, category, created_at, leido  FROM contact_messages ORDER BY id DESC"
        result = db.run(query)

        messages = [
            {"id": row[0], "name": row[1], "email": row[2], "message": row[3], "category": row[4], "created_at": row[5], "leido": row[6]}
            for row in result
        ]
        return jsonify(messages), 200

    except Exception as e:
        print(f"Error al obtener mensajes de contacto: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500

@bp.route('/messages/<int:message_id>', methods=['GET'])
def get_contact_message_by_id(message_id):
    """Obtener un mensaje de contacto por su ID."""
    try:
        db = get_db()
        query = f"SELECT id, name, email, message, category, created_at, leido FROM contact_messages WHERE id = {message_id}"
        result = db.run(query)

        if not result:
            return jsonify({"error": "Mensaje no encontrado"}), 404

        message = {
            "id": result[0][0],
            "name": result[0][1],
            "email": result[0][2],
            "message": result[0][3],
            "category": result[0][4],
            "created_at": result[0][5],
            "leido": result[0][6]
        }

        return jsonify(message), 200

    except Exception as e:
        print(f"Error al obtener el mensaje: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500

@bp.route('/messages/<int:message_id>/mark_as_read', methods=['PUT'])
def mark_message_as_read(message_id):
    """Marcar un mensaje como leído."""
    try:
        db = get_db()
        query = f"UPDATE contact_messages SET leido = TRUE WHERE id = {message_id} RETURNING id"
        result = db.run(query)

        if not result:
            return jsonify({"error": "Mensaje no encontrado"}), 404

        return jsonify({"message": "Mensaje marcado como leído"}), 200

    except Exception as e:
        print(f"Error al marcar el mensaje como leído: {e}")
        return jsonify({"error": "Ocurrió un error al actualizar el mensaje"}), 500


@bp.route('/packages', methods=['GET'])
def get_packages():
    """Obtener todos los paquetes turísticos con detalles completos."""
    try:
        db = get_db()
        query = """
            SELECT id, name, description, duration, category, start_date, end_date, availability, 
                   booking_deadline, discounts, accommodation, meals, transportation, tours, 
                   insurance, guides, additional_services, excluded_items, photos, videos, 
                   departure_location, return_location, meeting_points, itinerary, status, 
                   customizations, group_size, travel_restrictions, created_at, updated_at
            FROM packages ORDER BY id DESC
        """
        result = db.run(query)

        if not result:
            return jsonify({"message": "No hay paquetes disponibles"}), 200

        packages = [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "duration": row[3],
                "category": row[4],
                "start_date": row[5],
                "end_date": row[6],
                "availability": row[7],
                "booking_deadline": row[8],
                "discounts": row[9],
                "accommodation": row[10],
                "meals": row[11],
                "transportation": row[12],
                "tours": row[13],
                "insurance": row[14],
                "guides": row[15],
                "additional_services": row[16],
                "excluded_items": row[17],
                "photos": row[18],
                "videos": row[19],
                "departure_location": row[20],
                "return_location": row[21],
                "meeting_points": row[22],
                "itinerary": row[23],
                "status": row[24],
                "customizations": row[25],
                "group_size": row[26],
                "travel_restrictions": row[27],
                "created_at": row[28],
                "updated_at": row[29],
            }
            for row in result
        ]
        
        return jsonify(packages), 200

    except Exception as e:
        print(f"Error al obtener paquetes turísticos: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500
