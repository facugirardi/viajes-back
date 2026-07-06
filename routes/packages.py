import json
import uuid

from flask import jsonify, request
from werkzeug.utils import secure_filename

import storage
from db import get_db
from routes import bp
from routes.helpers import PACKAGE_SELECT, get_or_create_destino, login_required, serialize_package


@bp.route('/packages', methods=['GET'])
def get_packages():
    """Obtener todos los paquetes turísticos con su destino e imágenes."""
    try:
        db = get_db()

        packages = db.run(PACKAGE_SELECT + " ORDER BY p.id DESC")

        packages_list = []
        for package in packages:
            package_data = serialize_package(package)
            images = db.run("SELECT image_url FROM package_images WHERE package_id = :package_id", package_id=package_data["id"])
            package_data["images"] = [img[0] for img in images]
            packages_list.append(package_data)

        return jsonify(packages_list), 200

    except Exception as e:
        print(f"Error al obtener paquetes turísticos: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500


@bp.route('/api/create_package', methods=['POST'])
@login_required
def create_package():
    """Crear un paquete con imágenes y secciones."""
    try:
        db = get_db()
        data = request.form
        files = request.files.getlist("images")

        print("Recibiendo imágenes:", [file.filename for file in files])
        if not files:
            print("⚠️ No llegaron archivos en la solicitud.")

        destino_id = get_or_create_destino(
            db, data.get("destino_id"), data.get("destino_name"), data.get("category")
        )
        includes = json.dumps(request.form.getlist("includes[]"))

        result = db.run(
            """
            INSERT INTO packages (
                name, description, destino_id, duration_days, price_amount, price_currency,
                accommodation, includes, start_date, end_date
            )
            VALUES (
                :name, :description, :destino_id, :duration_days, :price_amount, :price_currency,
                :accommodation, :includes, :start_date, :end_date
            )
            RETURNING id
            """,
            name=data.get("title"), description=data.get("description"), destino_id=destino_id,
            duration_days=data.get("duration_days") or None,
            price_amount=data.get("price_amount") or None,
            price_currency=data.get("price_currency", "USD"),
            accommodation=data.get("accommodation"),
            includes=includes,
            start_date=data.get("departureDate") or None, end_date=data.get("returnDate") or None
        )

        if not result:
            return jsonify({"error": "Error al insertar el paquete"}), 500

        package_id = result[0][0]

        index = 0
        while f"sections[{index}][title]" in data:
            db.run(
                """
                INSERT INTO package_sections (package_id, title, description, icon, type)
                VALUES (:package_id, :title, :description, :icon, 'package')
                """,
                package_id=package_id,
                title=data.get(f"sections[{index}][title]"),
                description=data.get(f"sections[{index}][description]"),
                icon=data.get(f"sections[{index}][icon]", "")
            )
            index += 1

        index = 0
        while f"destinationSections[{index}][title]" in data:
            db.run(
                """
                INSERT INTO package_sections (package_id, title, description, icon, type)
                VALUES (:package_id, :title, :description, :icon, 'destination')
                """,
                package_id=package_id,
                title=data.get(f"destinationSections[{index}][title]"),
                description=data.get(f"destinationSections[{index}][description]"),
                icon=data.get(f"destinationSections[{index}][icon]", "")
            )
            index += 1

        image_urls = []
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_extension = filename.split('.')[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"

                file_path = f"packages/{package_id}/{unique_filename}"

                print(f"Subiendo archivo: {filename} como {file_path}")

                try:
                    image_url = storage.upload_file(file, file_path)
                    print(f"✅ Imagen subida correctamente: {file_path}")
                except Exception as e:
                    print(f"❌ Error al subir la imagen {filename}: {e}")
                    continue

                image_urls.append((package_id, image_url))

        print("Lista de imágenes a guardar en la BD:", image_urls)

        for pkg_id, image_url in image_urls:
            try:
                db.run(
                    "INSERT INTO package_images (package_id, image_url) VALUES (:package_id, :image_url)",
                    package_id=pkg_id, image_url=image_url
                )
            except Exception as e:
                print(f"❌ Error al insertar imagen en la BD: {e}")

        if image_urls:
            print("✅ URLs de imágenes insertadas en la base de datos correctamente")

        return jsonify({"message": "Paquete creado exitosamente", "package_id": package_id, "images": image_urls}), 201

    except Exception as e:
        print(f"Error al crear el paquete: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@bp.route('/api/delete_package/<int:package_id>', methods=['DELETE'])
@login_required
def delete_package(package_id):
    """Eliminar un paquete, sus imágenes, secciones y archivos en Cloudflare R2."""
    try:
        db = get_db()

        images = db.run("SELECT image_url FROM package_images WHERE package_id = :package_id", package_id=package_id)
        image_urls = [img[0] for img in images]

        for image_url in image_urls:
            file_path = storage.path_from_public_url(image_url)
            if file_path:
                try:
                    storage.delete_file(file_path)
                    print(f"✅ Imagen eliminada de Storage: {file_path}")
                except Exception as e:
                    print(f"❌ Error al eliminar la imagen {file_path} de Storage: {e}")

        db.run("DELETE FROM package_images WHERE package_id = :package_id", package_id=package_id)
        db.run("DELETE FROM package_sections WHERE package_id = :package_id", package_id=package_id)
        db.run("DELETE FROM packages WHERE id = :package_id", package_id=package_id)

        print(f"✅ Paquete {package_id} eliminado correctamente")
        return jsonify({"message": f"Paquete {package_id} eliminado correctamente"}), 200

    except Exception as e:
        print(f"❌ Error al eliminar el paquete {package_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@bp.route('/api/packages/<int:package_id>', methods=['GET'])
def get_package_by_id(package_id):
    """Obtener un paquete específico con su destino e imágenes."""
    try:
        db = get_db()

        package_result = db.run(PACKAGE_SELECT + " WHERE p.id = :package_id", package_id=package_id)

        if not package_result:
            return jsonify({"error": "Paquete no encontrado"}), 404

        package_data = serialize_package(package_result[0])

        images_result = db.run(
            "SELECT image_url FROM package_images WHERE package_id = :package_id",
            package_id=package_id
        )
        package_data["images"] = [img[0] for img in images_result]

        return jsonify(package_data), 200

    except Exception as e:
        print(f"❌ Error al obtener el paquete {package_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@bp.route('/api/packages/<int:package_id>', methods=['PUT'])
@login_required
def update_package(package_id):
    """Actualizar los datos de un paquete y sus imágenes."""
    try:
        db = get_db()
        data = request.form
        files = request.files.getlist("images")
        delete_images = request.form.getlist("deleteImages")

        existing = db.run("SELECT id FROM packages WHERE id = :package_id", package_id=package_id)
        if not existing:
            return jsonify({"error": "Paquete no encontrado"}), 404

        destino_id = get_or_create_destino(
            db, data.get("destino_id"), data.get("destino_name"), data.get("category")
        )
        includes = json.dumps(request.form.getlist("includes[]"))

        db.run(
            """
            UPDATE packages
            SET name = :name, description = :description, destino_id = :destino_id,
                duration_days = :duration_days, price_amount = :price_amount,
                price_currency = :price_currency, accommodation = :accommodation,
                includes = :includes, start_date = :start_date, end_date = :end_date,
                updated_at = now()
            WHERE id = :package_id
            """,
            name=data.get("title"), description=data.get("description"), destino_id=destino_id,
            duration_days=data.get("duration_days") or None,
            price_amount=data.get("price_amount") or None,
            price_currency=data.get("price_currency", "USD"),
            accommodation=data.get("accommodation"),
            includes=includes,
            start_date=data.get("departureDate") or None, end_date=data.get("returnDate") or None,
            package_id=package_id
        )

        for image_url in delete_images:
            file_path = storage.path_from_public_url(image_url)
            if file_path:
                try:
                    storage.delete_file(file_path)
                except Exception as e:
                    print(f"❌ Error al eliminar la imagen {file_path} de Storage: {e}")
            db.run(
                "DELETE FROM package_images WHERE image_url = :image_url AND package_id = :package_id",
                image_url=image_url, package_id=package_id
            )

        image_urls = []
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_extension = filename.split('.')[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                file_path = f"packages/{package_id}/{unique_filename}"

                image_url = storage.upload_file(file, file_path)
                db.run(
                    "INSERT INTO package_images (package_id, image_url) VALUES (:package_id, :image_url)",
                    package_id=package_id, image_url=image_url
                )
                image_urls.append(image_url)

        return jsonify({"message": "Paquete actualizado correctamente", "new_images": image_urls}), 200

    except Exception as e:
        print(f"❌ Error al actualizar paquete {package_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
