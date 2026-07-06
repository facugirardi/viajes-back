from flask import jsonify, request

from db import get_db
from routes import bp
from routes.helpers import PACKAGE_SELECT, login_required, serialize_package


@bp.route('/home/destinos', methods=['GET'])
def get_home_destinos():
    """Destinos destacados para la home, en el orden elegido desde el admin."""
    try:
        db = get_db()
        destinos = db.run(
            """
            SELECT id, name, slug, category, image_url
            FROM destinos
            WHERE featured = TRUE
            ORDER BY featured_order ASC NULLS LAST, id ASC
            """
        )
        destinos_list = [
            {"id": d[0], "name": d[1], "slug": d[2], "category": d[3], "image": d[4]}
            for d in destinos
        ]
        return jsonify(destinos_list), 200

    except Exception as e:
        print(f"Error al obtener destinos destacados: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500


@bp.route('/home/packages', methods=['GET'])
def get_home_packages():
    """Paquetes destacados para la home, en el orden elegido desde el admin."""
    try:
        db = get_db()
        packages = db.run(
            PACKAGE_SELECT + " WHERE p.featured = TRUE ORDER BY p.featured_order ASC NULLS LAST, p.id ASC"
        )

        packages_list = []
        for package in packages:
            package_data = serialize_package(package)
            images = db.run("SELECT image_url FROM package_images WHERE package_id = :package_id", package_id=package_data["id"])
            package_data["images"] = [img[0] for img in images]
            packages_list.append(package_data)

        return jsonify(packages_list), 200

    except Exception as e:
        print(f"Error al obtener paquetes destacados: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500


@bp.route('/api/home/destinos', methods=['PUT'])
@login_required
def set_home_destinos():
    """Definir, en orden, qué destinos se muestran destacados en la home."""
    try:
        db = get_db()
        data = request.get_json(silent=True) or {}
        destino_ids = data.get("destino_ids")

        if not isinstance(destino_ids, list):
            return jsonify({"error": "destino_ids debe ser una lista de ids"}), 400

        db.run("UPDATE destinos SET featured = FALSE, featured_order = NULL WHERE featured = TRUE")
        for order, destino_id in enumerate(destino_ids):
            db.run(
                "UPDATE destinos SET featured = TRUE, featured_order = :order WHERE id = :destino_id",
                order=order, destino_id=int(destino_id)
            )

        return jsonify({"message": "Destinos destacados actualizados correctamente"}), 200

    except Exception as e:
        print(f"Error al actualizar destinos destacados: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@bp.route('/api/home/packages', methods=['PUT'])
@login_required
def set_home_packages():
    """Definir, en orden, qué paquetes se muestran destacados en la home."""
    try:
        db = get_db()
        data = request.get_json(silent=True) or {}
        package_ids = data.get("package_ids")

        if not isinstance(package_ids, list):
            return jsonify({"error": "package_ids debe ser una lista de ids"}), 400

        db.run("UPDATE packages SET featured = FALSE, featured_order = NULL WHERE featured = TRUE")
        for order, package_id in enumerate(package_ids):
            db.run(
                "UPDATE packages SET featured = TRUE, featured_order = :order WHERE id = :package_id",
                order=order, package_id=int(package_id)
            )

        return jsonify({"message": "Paquetes destacados actualizados correctamente"}), 200

    except Exception as e:
        print(f"Error al actualizar paquetes destacados: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
