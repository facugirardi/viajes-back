from flask import Blueprint, jsonify, request
from db import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import boto3
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint('routes', __name__)
SECRET_KEY = 'vayafgav' 

# Configuración de Cloudflare R2
R2_ACCESS_KEY_ID = "ecd477a832e8f08a572ff8b6d179fc3c"
R2_SECRET_ACCESS_KEY = "1f5834c6a8ca4fbc154ec934c29cdc5cdec6df3352c13e4bb4fd7606d485d58d"
R2_BUCKET_NAME = "viajes"
R2_ENDPOINT_URL = "https://93f9401a1ebc8cccebfa063f9a24056a.r2.cloudflarestorage.com"

s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY
)

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
    """Obtener todos los paquetes turísticos con sus secciones e imágenes."""
    try:
        db = get_db()

        # 1️⃣ Obtener los paquetes
        query = f"SELECT id, name, destination, start_date, end_date FROM packages ORDER BY id DESC"
        packages = db.run(query)

        packages_list = []
        for package in packages:
            package_id = package[0]
            package_data = {
                "id": package_id,
                "name": package[1],
                "destination": package[2],
                "start_date": package[3],
                "end_date": package[4],
                "sections": [],
                "images": []
            }

            # 2️⃣ Obtener las secciones del paquete
            sections_query = f"""
                SELECT title, description, icon
                FROM package_sections
                WHERE package_id = {package_id}
            """
            sections = db.run(sections_query)
            package_data["sections"] = [{"title": s[0], "description": s[1], "icon": s[2]} for s in sections]

            # 3️⃣ Obtener las imágenes del paquete
            images_query = f"SELECT image_url FROM package_images WHERE package_id = {package_id}"
            images = db.run(images_query)
            package_data["images"] = [img[0] for img in images]

            packages_list.append(package_data)

        return jsonify(packages_list), 200

    except Exception as e:
        print(f"Error al obtener paquetes turísticos: {e}")
        return jsonify({"error": "Ocurrió un error al procesar tu solicitud"}), 500


@bp.route('/api/create_package', methods=['POST'])
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


        # 1️⃣ Insertar el paquete en la BD
        query = f"""
            INSERT INTO packages (name, destination, start_date, end_date)
            VALUES ('{data.get("title")}', '{data.get("destination")}', '{data.get("departureDate")}', '{data.get("returnDate")}')
            RETURNING id
        """
        result = db.run(query)

        if not result:
            return jsonify({"error": "Error al insertar el paquete"}), 500

        package_id = result[0][0]  # Obtener el ID del paquete recién insertado

        # 2️⃣ Insertar las secciones del paquete en `package_sections`
        sections = []
        index = 0
        while f"sections[{index}][title]" in data:
            section_title = data.get(f"sections[{index}][title]")
            section_description = data.get(f"sections[{index}][description]")
            section_icon = data.get(f"sections[{index}][icon]", "")
            section_type = "package"  # Tipo de sección

            sections.append(f"({package_id}, '{section_title}', '{section_description}', '{section_icon}', '{section_type}')")
            index += 1
            
        destination_sections = []
        index = 0
        while f"destinationSections[{index}][title]" in data:
            section_title = data.get(f"destinationSections[{index}][title]")
            section_description = data.get(f"destinationSections[{index}][description]")
            section_icon = data.get(f"destinationSections[{index}][icon]", "")  # Nombre del icono
            section_type = "destination"  # Tipo de sección

            destination_sections.append(f"({package_id}, '{section_title}', '{section_description}', '{section_icon}', '{section_type}')")
            index += 1

        if sections or destination_sections:
            sections_query = f"""
                INSERT INTO package_sections (package_id, title, description, icon, type)
                VALUES {', '.join(sections + destination_sections)}
            """
            db.run(sections_query)

        # 3️⃣ Subir imágenes a Cloudflare R2 y guardar las URLs
        image_urls = []
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_extension = filename.split('.')[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"  # Nombre único para evitar colisiones
                
                file_path = f"packages/{package_id}/{unique_filename}"  # Ruta en R2
                
                # **Depuración**
                print(f"Subiendo archivo: {filename} como {file_path}")

                # Subir la imagen a Cloudflare R2
                try:
                    s3_client.upload_fileobj(file, R2_BUCKET_NAME, file_path)
                    print(f"✅ Imagen subida correctamente: {file_path}")
                except Exception as e:
                    print(f"❌ Error al subir la imagen {filename}: {e}")
                    continue  # Saltar a la siguiente imagen si hay un error

                # Generar URL pública
                image_url = f"https://pub-35ca4370eb7e499595a069cecaff5fab.r2.dev/{file_path}"
                image_urls.append((package_id, image_url))

        # **Depuración**
        print("Lista de imágenes a guardar en la BD:", image_urls)

        # 4️⃣ Insertar URLs de imágenes en la base de datos
        if image_urls:
            try:
                # Construir la consulta con F-string
                values = ", ".join([f"({package_id}, '{image_url}')" for package_id, image_url in image_urls])
                query = f"INSERT INTO package_images (package_id, image_url) VALUES {values};"

                print("🔹 Ejecutando consulta SQL:", query)  # Para depuración

                db.run(query)  # Ejecutar la consulta con tu método `db.run()`

                print("✅ URLs de imágenes insertadas en la base de datos correctamente")
            except Exception as e:
                print(f"❌ Error al insertar imágenes en la BD: {e}")
                
        return jsonify({"message": "Paquete creado exitosamente", "package_id": package_id, "images": image_urls}), 201

    except Exception as e:
        print(f"Error al crear el paquete: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@bp.route('/api/delete_package/<int:package_id>', methods=['DELETE'])
def delete_package(package_id):
    """Eliminar un paquete, sus imágenes, secciones y archivos en Cloudflare R2."""
    try:
        db = get_db()

        # 1️⃣ Obtener las imágenes asociadas al paquete
        images_query = f"SELECT image_url FROM package_images WHERE package_id = {package_id}"
        images = db.run(images_query)
        image_urls = [img[0] for img in images]

        # 2️⃣ Borrar archivos del Cloudflare R2
        for image_url in image_urls:
            if "r2.dev/" in image_url:
                file_key = image_url.split("r2.dev/")[-1]  # Extraer solo la ruta del archivo
                try:
                    s3_client.delete_object(Bucket=R2_BUCKET_NAME, Key=file_key)
                    print(f"✅ Imagen eliminada de R2: {file_key}")
                except Exception as e:
                    print(f"❌ Error al eliminar la imagen {file_key} de R2: {e}")

        # 3️⃣ Borrar imágenes del paquete en la base de datos
        delete_images_query = f"DELETE FROM package_images WHERE package_id = {package_id}"
        db.run(delete_images_query)

        # 4️⃣ Borrar secciones del paquete en la base de datos
        delete_sections_query = f"DELETE FROM package_sections WHERE package_id = {package_id}"
        db.run(delete_sections_query)

        # 5️⃣ Borrar el paquete en la base de datos
        delete_package_query = f"DELETE FROM packages WHERE id = {package_id}"
        db.run(delete_package_query)

        print(f"✅ Paquete {package_id} eliminado correctamente")
        return jsonify({"message": f"Paquete {package_id} eliminado correctamente"}), 200

    except Exception as e:
        print(f"❌ Error al eliminar el paquete {package_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
    
@bp.route('/api/packages/<int:package_id>', methods=['GET'])
def get_package_by_id(package_id):
    """Obtener un paquete específico con sus secciones e imágenes."""
    try:
        db = get_db()

        # 1️⃣ Obtener la información del paquete
        package_query = f"""
            SELECT id, name, destination, start_date, end_date
            FROM packages
            WHERE id = {package_id}
        """
        package_result = db.run(package_query)

        if not package_result:
            return jsonify({"error": "Paquete no encontrado"}), 404

        package = package_result[0]
        package_data = {
            "id": package[0],
            "title": package[1],
            "destination": package[2],
            "departureDate": package[3],
            "returnDate": package[4],
            "sections": [],
            "destinationSections": [],
            "images": []
        }

        # 2️⃣ Obtener las secciones del paquete con `type` y `icon`
        sections_query = f"""
            SELECT id, title, description, icon, type
            FROM package_sections
            WHERE package_id = {package_id}
        """
        sections_result = db.run(sections_query)

        for sec in sections_result:
            section = {
                "id": sec[0],
                "title": sec[1],
                "description": sec[2],
                "iconType": sec[3],  # Aquí el nombre del icono
            }
            if sec[4] == "package":
                package_data["sections"].append(section)
            else:
                package_data["destinationSections"].append(section)

        # 3️⃣ Obtener las imágenes del paquete
        images_query = f"""
            SELECT image_url
            FROM package_images
            WHERE package_id = {package_id}
        """
        images_result = db.run(images_query)
        package_data["images"] = [img[0] for img in images_result]

        return jsonify(package_data), 200

    except Exception as e:
        print(f"❌ Error al obtener el paquete {package_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@bp.route('/api/packages/<int:package_id>', methods=['PUT'])
def update_package(package_id):
    """Actualizar un paquete con nuevas imágenes y secciones sin duplicarlas y actualizando correctamente."""
    try:
        db = get_db()
        data = request.form
        files = request.files.getlist("images")
        delete_images = request.form.getlist("deleteImages")
        delete_sections = request.form.getlist("deleteSections")
        delete_destination_sections = request.form.getlist("deleteDestinationSections")

        # 1️⃣ Obtener la información actual del paquete
        package_info = db.run(f"SELECT name, destination, start_date, end_date FROM packages WHERE id = {package_id}")
        if not package_info:
            return jsonify({"error": "Paquete no encontrado"}), 404

        package_info = package_info[0]
        new_title = data.get("title")
        new_destination = data.get("destination")
        new_start_date = data.get("departureDate")
        new_end_date = data.get("returnDate")

        # 2️⃣ **Actualizar solo si cambió algún dato**
        if (new_title != package_info[0] or new_destination != package_info[1] or 
            new_start_date != package_info[2] or new_end_date != package_info[3]):
            update_query = f"""
                UPDATE packages 
                SET name = '{new_title}', 
                    destination = '{new_destination}', 
                    start_date = '{new_start_date}', 
                    end_date = '{new_end_date}'
                WHERE id = {package_id}
            """
            db.run(update_query)

        # 3️⃣ **Eliminar imágenes y secciones marcadas**
        if delete_images:
            db.run(f"DELETE FROM package_images WHERE image_url IN ({', '.join([f"'{img}'" for img in delete_images])}) AND package_id = {package_id}")

        if delete_sections:
            db.run(f"DELETE FROM package_sections WHERE id IN ({', '.join(delete_sections)}) AND package_id = {package_id}")

        if delete_destination_sections:
            db.run(f"DELETE FROM package_sections WHERE id IN ({', '.join(delete_destination_sections)}) AND package_id = {package_id}")

        # 4️⃣ **Obtener secciones actuales**
        existing_sections = {row[0]: {"title": row[1], "description": row[2], "iconType": row[3]} for row in 
                             db.run(f"SELECT id, title, description, icon FROM package_sections WHERE package_id = {package_id} AND type = 'package'")}

        existing_destination_sections = {row[0]: {"title": row[1], "description": row[2], "iconType": row[3]} for row in 
                                         db.run(f"SELECT id, title, description, icon FROM package_sections WHERE package_id = {package_id} AND type = 'destination'")}

        # 5️⃣ **Actualizar o insertar secciones (según corresponda)**
        index = 0
        while f"sections[{index}][title]" in data:
            section_id = data.get(f"sections[{index}][id]")
            section_title = data.get(f"sections[{index}][title]")
            section_description = data.get(f"sections[{index}][description]")
            section_icon = data.get(f"sections[{index}][icon]", "")
            section_type = "package"

            if section_id and section_id.isdigit():  # Si el ID es válido, actualizar
                db.run(f"""
                    UPDATE package_sections 
                    SET title = '{section_title}', description = '{section_description}', icon = '{section_icon}' 
                    WHERE id = {section_id} AND package_id = {package_id}
                """)
            elif any(sec["title"] == section_title for sec in existing_sections.values()):  
                # Si la sección existe por título (riesgoso si los títulos cambian), actualizar
                existing_id = next(key for key, val in existing_sections.items() if val["title"] == section_title)
                db.run(f"""
                    UPDATE package_sections 
                    SET description = '{section_description}', icon = '{section_icon}' 
                    WHERE id = {existing_id} AND package_id = {package_id}
                """)
            else:
                # Insertar nueva sección si no existe
                db.run(f"""
                    INSERT INTO package_sections (package_id, title, description, icon, type)
                    VALUES ({package_id}, '{section_title}', '{section_description}', '{section_icon}', '{section_type}')
                """)

            index += 1

        # 6️⃣ **Actualizar o insertar secciones de destino (según corresponda)**
        index = 0
        while f"destinationSections[{index}][title]" in data:
            section_id = data.get(f"destinationSections[{index}][id]")
            section_title = data.get(f"destinationSections[{index}][title]")
            section_description = data.get(f"destinationSections[{index}][description]")
            section_icon = data.get(f"destinationSections[{index}][icon]", "")
            section_type = "destination"

            if section_id and section_id.isdigit():
                db.run(f"""
                    UPDATE package_sections 
                    SET title = '{section_title}', description = '{section_description}', icon = '{section_icon}' 
                    WHERE id = {section_id} AND package_id = {package_id}
                """)
            elif any(sec["title"] == section_title for sec in existing_destination_sections.values()):  
                existing_id = next(key for key, val in existing_destination_sections.items() if val["title"] == section_title)
                db.run(f"""
                    UPDATE package_sections 
                    SET description = '{section_description}', icon = '{section_icon}' 
                    WHERE id = {existing_id} AND package_id = {package_id}
                """)
            else:
                db.run(f"""
                    INSERT INTO package_sections (package_id, title, description, icon, type)
                    VALUES ({package_id}, '{section_title}', '{section_description}', '{section_icon}', '{section_type}')
                """)

            index += 1

        # 7️⃣ **Agregar nuevas imágenes si hay**
        image_urls = []
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_extension = filename.split('.')[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                file_path = f"packages/{package_id}/{unique_filename}"

                s3_client.upload_fileobj(file, "viajes", file_path)
                image_url = f"https://pub-35ca4370eb7e499595a069cecaff5fab.r2.dev/{file_path}"
                db.run(f"INSERT INTO package_images (package_id, image_url) VALUES ({package_id}, '{image_url}')")
                image_urls.append(image_url)

        return jsonify({"message": "Paquete actualizado correctamente", "new_images": image_urls}), 200

    except Exception as e:
        print(f"❌ Error al actualizar paquete {package_id}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
