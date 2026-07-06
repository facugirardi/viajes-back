import uuid

from flask import jsonify, request
from werkzeug.utils import secure_filename

import storage
from db import get_db
from routes import bp
from routes.helpers import PACKAGE_SELECT, login_required, serialize_package, slugify


@bp.route('/destinos', methods=['GET'])
def get_destinos():
    """Obtener todos los destinos con sus paquetes anidados (para el sitio público)."""
    try:
        db = get_db()

        destinos = db.run("SELECT id, name, slug, category, image_url, featured, featured_order FROM destinos ORDER BY name")
        destinos_list = []

        for destino in destinos:
            destino_id = destino[0]
            packages = db.run(PACKAGE_SELECT + " WHERE p.destino_id = :destino_id ORDER BY p.id", destino_id=destino_id)

            paquetes = []
            for package in packages:
                package_data = serialize_package(package)
                images = db.run("SELECT image_url FROM package_images WHERE package_id = :package_id", package_id=package_data["id"])
                package_data["images"] = [img[0] for img in images]
                paquetes.append(package_data)

            destinos_list.append({
                "id": destino_id,
                "name": destino[1],
                "slug": destino[2],
                "category": destino[3],
                "image": destino[4],
                "featured": destino[5],
                "featured_order": destino[6],
                "paquetes": paquetes,
            })

        return jsonify(destinos_list), 200

    except Exception as e:
        print(f"Error al obtener destinos: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500


@bp.route('/api/destinos', methods=['POST'])
@login_required
def create_destino():
    """Crear un destino nuevo con imagen opcional."""
    try:
        db = get_db()
        data = request.form
        name = data.get("name")
        category = data.get("category")

        if not name or not category:
            return jsonify({"error": "Nombre y categoría son obligatorios"}), 400

        slug = slugify(name)
        existing = db.run("SELECT id FROM destinos WHERE slug = :slug", slug=slug)
        if existing:
            return jsonify({"error": "Ya existe un destino con ese nombre"}), 409

        image_url = None
        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_extension = filename.split('.')[-1]
            file_path = f"destinos/{slug}/{uuid.uuid4()}.{file_extension}"
            image_url = storage.upload_file(file, file_path)

        result = db.run(
            "INSERT INTO destinos (name, slug, category, image_url) VALUES (:name, :slug, :category, :image_url) RETURNING id",
            name=name, slug=slug, category=category, image_url=image_url
        )

        return jsonify({"message": "Destino creado exitosamente", "id": result[0][0]}), 201

    except Exception as e:
        print(f"Error al crear destino: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@bp.route('/api/destinos/<int:destino_id>', methods=['GET'])
def get_destino_by_id(destino_id):
    """Obtener un destino específico."""
    try:
        db = get_db()
        result = db.run(
            "SELECT id, name, slug, category, image_url FROM destinos WHERE id = :destino_id",
            destino_id=destino_id
        )

        if not result:
            return jsonify({"error": "Destino no encontrado"}), 404

        destino = result[0]
        return jsonify({
            "id": destino[0], "name": destino[1], "slug": destino[2],
            "category": destino[3], "image": destino[4],
        }), 200

    except Exception as e:
        print(f"Error al obtener destino {destino_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@bp.route('/api/destinos/<int:destino_id>', methods=['PUT'])
@login_required
def update_destino(destino_id):
    """Actualizar un destino existente."""
    try:
        db = get_db()
        data = request.form

        existing = db.run("SELECT id, image_url FROM destinos WHERE id = :destino_id", destino_id=destino_id)
        if not existing:
            return jsonify({"error": "Destino no encontrado"}), 404

        name = data.get("name")
        category = data.get("category")
        slug = slugify(name)
        image_url = existing[0][1]

        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_extension = filename.split('.')[-1]
            file_path = f"destinos/{slug}/{uuid.uuid4()}.{file_extension}"
            image_url = storage.upload_file(file, file_path)

        db.run(
            """
            UPDATE destinos SET name = :name, slug = :slug, category = :category,
                                 image_url = :image_url, updated_at = now()
            WHERE id = :destino_id
            """,
            name=name, slug=slug, category=category, image_url=image_url, destino_id=destino_id
        )

        return jsonify({"message": "Destino actualizado correctamente"}), 200

    except Exception as e:
        print(f"Error al actualizar destino {destino_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@bp.route('/api/destinos/<int:destino_id>', methods=['DELETE'])
@login_required
def delete_destino(destino_id):
    """Eliminar un destino, solo si no tiene paquetes asociados."""
    try:
        db = get_db()

        packages = db.run("SELECT id FROM packages WHERE destino_id = :destino_id", destino_id=destino_id)
        if packages:
            return jsonify({"error": "No se puede eliminar un destino con paquetes asociados"}), 409

        db.run("DELETE FROM destinos WHERE id = :destino_id", destino_id=destino_id)
        return jsonify({"message": "Destino eliminado correctamente"}), 200

    except Exception as e:
        print(f"Error al eliminar destino {destino_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
