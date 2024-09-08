from app.utils.db import get_db_connection
from functools import wraps
from psycopg2.extras import RealDictCursor
from flask import g, jsonify

def get_missing_id(table_name, id_column):
    conn = get_db_connection()
    cur = conn.cursor()
    query = f"""
    SELECT t1.{id_column} + 1 as missing_id
    FROM {table_name} t1
    LEFT JOIN {table_name} t2 ON t1.{id_column} + 1 = t2.{id_column}
    WHERE t2.{id_column} IS NULL
    ORDER BY t1.{id_column}
    LIMIT 1;
    """
    cur.execute(query)
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    else:
        return None

def get_umkms():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, nama, status_umkm FROM umkm')
    umkms = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for umkm in umkms:
        if umkm[2]:  # status_umkm adalah True
            result.append({"id": umkm[0], "nama": umkm[1]})
        else:  # status_umkm adalah False
            result.append({"data umkm dengan id: {} telah di suspended".format(umkm[0])})
    
    return result

def get_umkm_detail(umkm_id, user_role):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM umkm WHERE id = %s;', (umkm_id,))
    umkm = cur.fetchone()

    if not umkm:
        cur.close()
        conn.close()
        return {"error": "UMKM not found"}, 404

    # Periksa status UMKM
    status_umkm = umkm[11]
    if not status_umkm and user_role != 'ADMIN':
        cur.close()
        conn.close()
        return {"error": "This UMKM is suspended and cannot be accessed by users."}, 403

    cur.execute('SELECT * FROM produk WHERE id_umkm = %s;', (umkm_id,))
    products = cur.fetchall()

    umkm_detail = {
        "id": umkm[0],
        "id_user": umkm[1],
        "nama": umkm[2],
        "kategori": umkm[3],
        "deskripsi": umkm[4],
        "alamat": umkm[5],
        "no_kontak": umkm[6],
        "npwp": umkm[7],
        "jam_buka": umkm[8],
        "foto_umkm": umkm[9],
        "dokumen": umkm[10],
        "status_umkm": umkm[11],
        "products": [{"id": product[0], "nama_produk": product[1], "harga": product[2]} for product in products]
    }

    cur.close()
    conn.close()
    return umkm_detail

def update_umkm_by_id(umkm_id, data, user_role, user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT id_user, status_umkm FROM umkm WHERE id = %s;', (umkm_id,))
    umkm = cur.fetchone()

    if not umkm:
        cur.close()
        conn.close()
        return {"error": "UMKM not found"}, 404

    if umkm[0] != user_id and user_role != 'ADMIN':
        cur.close()
        conn.close()
        return {"error": "You can only update your own UMKM."}, 403

    if not umkm[1] and user_role != 'ADMIN':
        cur.close()
        conn.close()
        return {"error": "This UMKM is suspended and cannot be updated by users."}, 403

    # Set status_umkm ke True by default jika user bukan admin
    if 'status_umkm' not in data or user_role == 'pemilik':
        data['status_umkm'] = True

    query = '''
        UPDATE umkm 
        SET nama = %s, kategori = %s, deskripsi = %s, alamat = %s, no_kontak = %s, npwp = %s, jam_buka = %s, 
            foto_umkm = %s, dokumen = %s, status_umkm = %s
        WHERE id = %s;
    '''
    cur.execute(query, (
        data['nama'], data['kategori'], data['deskripsi'], data['alamat'], data['no_kontak'],
        data['npwp'], data['jam_buka'], data.get('foto_umkm'), data.get('dokumen'), data['status_umkm'], umkm_id
    ))
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "UMKM updated successfully."}, 200

def delete_umkm_by_id(umkm_id, user_role, user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT id_user, status_umkm FROM umkm WHERE id = %s;', (umkm_id,))
    umkm = cur.fetchone()

    if not umkm:
        cur.close()
        conn.close()
        return {"error": "UMKM not found"}, 404

    if umkm[0] != user_id and user_role != 'ADMIN':
        cur.close()
        conn.close()
        return {"error": "You can only delete your own UMKM."}, 403

    if not umkm[1] and user_role != 'ADMIN':
        cur.close()
        conn.close()
        return {"error": "This UMKM is suspended and cannot be deleted by users."}, 403

    cur.execute('DELETE FROM umkm WHERE id = %s;', (umkm_id,))
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "UMKM deleted successfully."}, 200

def create_umkm(data, user_id):
    if data['id_user'] != user_id:
        return {"error": "You can only create UMKM for yourself."}, 403

    conn = get_db_connection()
    cur = conn.cursor()

    query = '''
        INSERT INTO umkm (id_user, nama, kategori, deskripsi, alamat, no_kontak, npwp, jam_buka, foto_umkm, dokumen)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
    '''
    cur.execute(query, (
        user_id, data['nama'], data['kategori'], data['deskripsi'], data['alamat'], data['no_kontak'],
        data['npwp'], data['jam_buka'], data.get('foto_umkm'), data.get('dokumen')
    ))

    umkm = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return umkm, 201

def umkm_suspended_check(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if g.user['role'] == 'admin':
            return func(*args, **kwargs)

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        umkm_id = kwargs.get('umkm_id')
        if umkm_id:
            cur.execute('SELECT status_umkm FROM umkm WHERE id = %s;', (umkm_id,))
            umkm = cur.fetchone()
            
            if umkm and not umkm['status_umkm']:
                cur.close()
                conn.close()
                return jsonify({"error": "Akses ditolak. UMKM sedang di suspend."}), 403
        
        cur.close()
        conn.close()
        return func(*args, **kwargs)
    
    return decorated_function

def fetch_all_umkm():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM umkm;')
    umkms = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return umkms

def fetch_umkm_by_user_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM umkm WHERE id_user = %s;', (user_id,))
    umkms = cur.fetchall()
    
    cur.close()
    conn.close()

    return umkms