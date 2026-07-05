import os
import re
import json
import unicodedata
from functools import wraps
from flask import Blueprint, jsonify, request
from db import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import storage
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint('routes', __name__)
SECRET_KEY = os.environ["JWT_SECRET_KEY"]


def slugify(text):
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def get_or_create_destino(db, destino_id, destino_name, category):
    """Devuelve el id de un destino existente, o crea uno nuevo a partir del nombre+categoría."""
    if destino_id:
        return int(destino_id)

    if not destino_name or not category:
        return None

    slug = slugify(destino_name)
    existing = db.run("SELECT id FROM destinos WHERE slug = :slug", slug=slug)
    if existing:
        return existing[0][0]

    result = db.run(
        "INSERT INTO destinos (name, slug, category) VALUES (:name, :slug, :category) RETURNING id",
        name=destino_name, slug=slug, category=category
    )
    return result[0][0]


def serialize_package(row):
    """row: (id, name, description, duration_days, price_amount, price_currency,
             accommodation, includes, start_date, end_date, status,
             destino_id, destino_name, destino_category, destino_image_url)"""
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "duration_days": row[3],
        "price_amount": float(row[4]) if row[4] is not None else None,
        "price_currency": row[5],
        "accommodation": row[6],
        "includes": row[7] or [],
        "departureDate": row[8],
        "returnDate": row[9],
        "status": row[10],
        "destino": {
            "id": row[11],
            "name": row[12],
            "category": row[13],
            "image_url": row[14],
        } if row[11] else None,
    }


PACKAGE_SELECT = """
    SELECT p.id, p.name, p.description, p.duration_days, p.price_amount, p.price_currency,
           p.accommodation, p.includes, p.start_date, p.end_date, p.status,
           d.id, d.name, d.category, d.image_url
    FROM packages p
    LEFT JOIN destinos d ON d.id = p.destino_id
"""


def login_required(f):
    """Exige un JWT válido en el header Authorization: Bearer <token>."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "No autorizado"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Sesión expirada"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401

        return f(*args, **kwargs)
    return wrapper


@bp.route('/users', methods=['POST'])
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

        result = db.run(
            """
            INSERT INTO contact_messages (name, email, message, category)
            VALUES (:name, :email, :message, :category)
            RETURNING id
            """,
            name=data['name'], email=data['email'], message=data['message'], category=data['category']
        )
        print(result)
        return jsonify({"id": result[0][0]}), 201

    except Exception as e:
        print(f"Error al insertar mensaje de contacto: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500


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


@bp.route('/destinos', methods=['GET'])
def get_destinos():
    """Obtener todos los destinos con sus paquetes anidados (para el sitio público)."""
    try:
        db = get_db()

        destinos = db.run("SELECT id, name, slug, category, image_url FROM destinos ORDER BY name")
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


@bp.route('/api/create_package', methods=['POST'])
@login_required
def create_package():
    """Crear un paquete con imágenes y secciones."""
    try:
        db = get_db()
        data = request.form
        files = request.files.getlist("images")

        # Depuración
        print("Recibiendo imágenes:", [file.filename for file in files])  # Debería imprimir la lista de archivos
        if not files:
            print("⚠️ No llegaron archivos en la solicitud.")


        # 1️⃣ Resolver el destino (existente o nuevo) e insertar el paquete
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

        package_id = result[0][0]  # Obtener el ID del paquete recién insertado

        # 2️⃣ Insertar las secciones del paquete en `package_sections`
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

        # 3️⃣ Subir imágenes a Supabase Storage y guardar las URLs
        image_urls = []
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_extension = filename.split('.')[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"  # Nombre único para evitar colisiones

                file_path = f"packages/{package_id}/{unique_filename}"

                # **Depuración**
                print(f"Subiendo archivo: {filename} como {file_path}")

                try:
                    image_url = storage.upload_file(file, file_path)
                    print(f"✅ Imagen subida correctamente: {file_path}")
                except Exception as e:
                    print(f"❌ Error al subir la imagen {filename}: {e}")
                    continue  # Saltar a la siguiente imagen si hay un error

                image_urls.append((package_id, image_url))

        # **Depuración**
        print("Lista de imágenes a guardar en la BD:", image_urls)

        # 4️⃣ Insertar URLs de imágenes en la base de datos
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

        # 1️⃣ Obtener las imágenes asociadas al paquete
        images = db.run("SELECT image_url FROM package_images WHERE package_id = :package_id", package_id=package_id)
        image_urls = [img[0] for img in images]

        # 2️⃣ Borrar archivos de Supabase Storage
        for image_url in image_urls:
            file_path = storage.path_from_public_url(image_url)
            if file_path:
                try:
                    storage.delete_file(file_path)
                    print(f"✅ Imagen eliminada de Storage: {file_path}")
                except Exception as e:
                    print(f"❌ Error al eliminar la imagen {file_path} de Storage: {e}")

        # 3️⃣ Borrar imágenes del paquete en la base de datos
        db.run("DELETE FROM package_images WHERE package_id = :package_id", package_id=package_id)

        # 4️⃣ Borrar secciones del paquete en la base de datos
        db.run("DELETE FROM package_sections WHERE package_id = :package_id", package_id=package_id)

        # 5️⃣ Borrar el paquete en la base de datos
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

        # Eliminar imágenes marcadas (Storage + DB)
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

        # Agregar nuevas imágenes
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
