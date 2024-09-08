from flask import request, jsonify, g
from functools import wraps
from app.utils.db import get_db_connection
from psycopg2.extras import RealDictCursor

def produk_owner_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        produk_id = request.view_args.get('produk_id')
        if not produk_id:
            return jsonify({'error': 'Produk ID tidak ditemukan'}), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT p.id, p.id_umkm, u.id_user FROM produk p
            JOIN umkm u ON p.id_umkm = u.id
            WHERE p.id = %s;
        ''', (produk_id,))
        produk = cur.fetchone()
        cur.close()
        conn.close()

        if not produk or produk['id_user'] != g.user['id']:
            return jsonify({'error': 'Anda tidak diizinkan untuk mengakses atau mengubah produk ini'}), 403

        return f(*args, **kwargs)
    return decorator

def umkm_action_allowed(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        # Mengambil umkm_id dari request.form atau request.args
        umkm_id = request.form.get('id_umkm') or request.args.get('umkm_id')
        if not umkm_id:
            return jsonify({'error': 'UMKM ID tidak ditemukan'}), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Hapus kolom suspended jika tidak ada di tabel umkm
        cur.execute('SELECT id_user, status_umkm FROM umkm WHERE id = %s;', (umkm_id,))
        umkm = cur.fetchone()
        cur.close()
        conn.close()

        if not umkm:
            return jsonify({'error': 'UMKM tidak ditemukan'}), 404

        # Update kondisi untuk menyesuaikan dengan kolom yang tersedia
        if not umkm['status_umkm'] and g.user['role'] != 'ADMIN' and g.user['id'] != umkm['id_user']:
            return jsonify({'error': 'UMKM tidak aktif, Anda tidak diizinkan untuk melakukan operasi ini'}), 403

        return f(*args, **kwargs)
    return decorator

def umkm_suspended_check(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        umkm_id = request.form.get('id_umkm') or request.view_args.get('umkm_id') or request.args.get('umkm_id')

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

            # Cek jika UMKM tidak aktif dan pengguna bukan admin
            if not umkm['status_umkm'] and g.user['role'] != 'ADMIN':
                return jsonify({"error": "Access denied. UMKM is suspended."}), 403

        return f(*args, **kwargs)
    return decorator
