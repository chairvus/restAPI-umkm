from flask import jsonify, g, request
from functools import wraps
from app.utils.db import get_db_connection
from psycopg2.extras import RealDictCursor

def umkm_action_allowed(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        umkm_id = request.form.get('id_umkm') or request.view_args.get('umkm_id') or request.args.get('umkm_id')
        
        if umkm_id:
            try:
                umkm_id = int(umkm_id)  # Convert to int if needed
            except ValueError:
                return jsonify({'error': 'Invalid UMKM ID'}), 400

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('SELECT id_user, status_umkm FROM umkm WHERE id = %s;', (umkm_id,))
                    umkm = cur.fetchone()

            if not umkm:
                return jsonify({'error': 'UMKM tidak ditemukan'}), 404

            # Cek jika UMKM tidak aktif dan pengguna bukan admin
            if not umkm['status_umkm'] and g.user['role'] != 'ADMIN':
                return jsonify({'error': 'UMKM tidak aktif, Anda tidak diizinkan untuk melakukan operasi ini'}), 403

        return f(*args, **kwargs)
    return decorator

def umkm_suspended_check(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        umkm_id = request.view_args.get('umkm_id') or request.form.get('id') or request.args.get('id')

        if umkm_id:
            try:
                umkm_id = int(umkm_id)
            except ValueError:
                return jsonify({'error': 'Invalid UMKM ID'}), 400

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT status_umkm FROM umkm WHERE id = %s;", (umkm_id,))
                    umkm = cur.fetchone()

            if not umkm:
                return jsonify({'error': 'UMKM tidak ditemukan'}), 404

            # Cek jika UMKM sedang ditangguhkan dan pengguna bukan admin
            if not umkm['status_umkm'] and g.user['role'] != 'ADMIN':
                return jsonify({"error": "Access denied. UMKM is suspended."}), 403

        return f(*args, **kwargs)
    return decorator

def umkm_nonaktif_allowed(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        user_id = request.view_args.get('user_id')
        if user_id:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('SELECT id, id_user FROM umkm WHERE id_user = %s AND status_umkm = FALSE;', (user_id,))
                    umkms = cur.fetchall()

            if not umkms:
                return jsonify({'error': 'Tidak ada UMKM nonaktif ditemukan untuk user ini'}), 404

            if g.user['role'] != 'ADMIN' and g.user['id'] != int(user_id):
                return jsonify({'error': 'Anda tidak diizinkan untuk mengakses UMKM ini'}), 403

        return f(*args, **kwargs)
    return decorator

# Middleware baru untuk memeriksa status suspended UMKM
def umkm_suspended_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        umkm_id = request.form.get('id_umkm') or request.view_args.get('umkm_id') or request.args.get('umkm_id')

        if umkm_id:
            try:
                umkm_id = int(umkm_id)
            except ValueError:
                return jsonify({'error': 'Invalid UMKM ID'}), 400

            conn = get_db_connection()
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT status_umkm FROM umkm WHERE id = %s;", (umkm_id,))
                umkm = cur.fetchone()
            finally:
                cur.close()
                conn.close()

            if not umkm:
                return jsonify({'error': 'UMKM ID tidak ditemukan'}), 404

            # Cek jika UMKM sedang ditangguhkan dan pengguna bukan admin
            if not umkm['status_umkm'] and g.user['role'] != 'ADMIN':
                return jsonify({"error": "Access denied. UMKM is suspended."}), 403

        return f(*args, **kwargs)
    return decorated_function