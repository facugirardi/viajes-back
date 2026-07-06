import os
import re
import unicodedata
from functools import wraps

import jwt
from flask import jsonify, request

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
             destino_id, destino_name, destino_category, destino_image_url, destino_slug,
             featured, featured_order)"""
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
            "slug": row[15],
        } if row[11] else None,
        "featured": row[16],
        "featured_order": row[17],
    }


PACKAGE_SELECT = """
    SELECT p.id, p.name, p.description, p.duration_days, p.price_amount, p.price_currency,
           p.accommodation, p.includes, p.start_date, p.end_date, p.status,
           d.id, d.name, d.category, d.image_url, d.slug,
           p.featured, p.featured_order
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
