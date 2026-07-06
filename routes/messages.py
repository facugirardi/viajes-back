from flask import jsonify

from db import get_db
from routes import bp
from routes.helpers import login_required


@bp.route('/messages', methods=['GET'])
@login_required
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
@login_required
def get_contact_message_by_id(message_id):
    """Obtener un mensaje de contacto por su ID."""
    try:
        db = get_db()
        query = "SELECT id, name, email, message, category, created_at, leido FROM contact_messages WHERE id = :message_id"
        result = db.run(query, message_id=message_id)

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
@login_required
def mark_message_as_read(message_id):
    """Marcar un mensaje como leído."""
    try:
        db = get_db()
        query = "UPDATE contact_messages SET leido = TRUE WHERE id = :message_id RETURNING id"
        result = db.run(query, message_id=message_id)

        if not result:
            return jsonify({"error": "Mensaje no encontrado"}), 404

        return jsonify({"message": "Mensaje marcado como leído"}), 200

    except Exception as e:
        print(f"Error al marcar el mensaje como leído: {e}")
        return jsonify({"error": "Ocurrió un error al actualizar el mensaje"}), 500
