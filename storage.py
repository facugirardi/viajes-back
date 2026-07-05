import os
import requests

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "viajes")

_HEADERS = {
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
}


def upload_file(file_storage, path):
    """Sube un archivo (werkzeug FileStorage) a Supabase Storage y devuelve su URL pública."""
    content_type = file_storage.content_type or "application/octet-stream"
    response = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{path}",
        headers={**_HEADERS, "Content-Type": content_type},
        data=file_storage.read(),
    )
    response.raise_for_status()
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{path}"


def delete_file(path):
    """Borra un archivo de Supabase Storage a partir de su path dentro del bucket."""
    response = requests.delete(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{path}",
        headers=_HEADERS,
    )
    response.raise_for_status()


def path_from_public_url(image_url):
    """Extrae el path dentro del bucket a partir de una URL pública de Supabase Storage."""
    marker = f"/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/"
    if marker not in image_url:
        return None
    return image_url.split(marker, 1)[1]
