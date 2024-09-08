from flask import Blueprint, request, jsonify, g, current_app
from app.middlewares.auth_middleware import admin_required, user_or_admin_required, user_required
from app.middlewares.umkm_middleware import umkm_action_allowed, umkm_suspended_check
from app.services.umkm_service import get_missing_id, update_umkm_by_id
from psycopg2.extras import RealDictCursor
from app.utils.db import get_db_connection
import os
from app.services.umkm_service import get_umkm_detail, get_umkms, fetch_all_umkm, fetch_umkm_by_user_id
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

umkm_bp = Blueprint('umkm_bp', __name__)

@umkm_bp.route('/umkm', methods=['POST', 'PUT', 'DELETE'])
@user_or_admin_required
@umkm_action_allowed
@umkm_suspended_check
def manage_umkm():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        id_user = g.user['id']

        nama = request.form.get('nama')
        kategori = request.form.get('kategori')
        deskripsi = request.form.get('deskripsi')
        alamat = request.form.get('alamat')
        no_kontak = request.form.get('no_kontak')
        npwp = request.form.get('npwp')
        jam_buka = request.form.get('jam_buka')
        foto_umkm = request.files.get('foto_umkm')
        dokumen = request.files.get('dokumen')

        # Validasi field wajib
        if not nama:
            return jsonify({"error": "Field 'nama' harus diisi."}), 400
        if not kategori:
            return jsonify({"error": "Field 'kategori' harus diisi."}), 400
        if not deskripsi:
            return jsonify({"error": "Field 'deskripsi' harus diisi."}), 400
        if not alamat:
            return jsonify({"error": "Field 'alamat' harus diisi."}), 400
        if not no_kontak:
            return jsonify({"error": "Field 'no_kontak' harus diisi."}), 400

        # Atur status_umkm ke True secara default jika tidak ada dalam permintaan
        status_umkm = request.form.get('status_umkm', 'true').lower() == 'true'

        uploads_dir = os.path.join(current_app.root_path, 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)

        foto_umkm_path = None
        dokumen_path = None

        if foto_umkm:
            foto_umkm_path = os.path.join(uploads_dir, secure_filename(foto_umkm.filename))
            foto_umkm.save(foto_umkm_path)

        if dokumen:
            dokumen_path = os.path.join(uploads_dir, secure_filename(dokumen.filename))
            dokumen.save(dokumen_path)

        umkm_data = {
            'id_user': id_user,
            'nama': nama,
            'kategori': kategori,
            'deskripsi': deskripsi,
            'alamat': alamat,
            'no_kontak': no_kontak,
            'npwp': npwp,
            'jam_buka': jam_buka,
            'foto_umkm': foto_umkm_path,
            'dokumen': dokumen_path,
            'status_umkm': status_umkm
        }

        # Ambil missing ID dari tabel umkm jika ada
        cur.execute('SELECT COALESCE(MAX(id), 0) + 1 AS new_id FROM umkm')
        umkm_row = cur.fetchone()
        umkm_id = umkm_row['new_id'] if umkm_row else 1

        cur.execute('''
            INSERT INTO umkm (id, id_user, nama, kategori, deskripsi, alamat, no_kontak, npwp, jam_buka, foto_umkm, dokumen, status_umkm)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
        ''', (
            umkm_id, id_user, nama, kategori, deskripsi, alamat, no_kontak, npwp, jam_buka, 
            foto_umkm.filename if foto_umkm else None, dokumen.filename if dokumen else None, status_umkm
        ))
        umkm = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        umkm['foto_umkm'] = foto_umkm_path
        umkm['dokumen'] = dokumen_path

        return jsonify(umkm), 201

    elif request.method == 'PUT':
        umkm_id = request.form.get('id')
        id_user = g.user['id']
        user_role = g.user['role']

        if not umkm_id:
            return jsonify({"error": "Field 'id' harus diisi."}), 400

        cur.execute('SELECT id_user FROM umkm WHERE id = %s;', (umkm_id,))
        umkm = cur.fetchone()

        if not umkm:
            return jsonify({"error": "UMKM tidak ditemukan."}), 404

        if user_role != 'ADMIN' and umkm['id_user'] != id_user:
            return jsonify({"error": "You can only update your own UMKM."}), 403

        # Mendapatkan data form dari request
        data = {
            'nama': request.form.get('nama'),
            'kategori': request.form.get('kategori'),
            'deskripsi': request.form.get('deskripsi'),
            'alamat': request.form.get('alamat'),
            'no_kontak': request.form.get('no_kontak'),
            'npwp': request.form.get('npwp'),
            'jam_buka': request.form.get('jam_buka'),
        }

        # Validasi field wajib
        if not data['nama']:
            return jsonify({"error": "Field 'nama' harus diisi."}), 400
        if not data['kategori']:
            return jsonify({"error": "Field 'kategori' harus diisi."}), 400
        if not data['deskripsi']:
            return jsonify({"error": "Field 'deskripsi' harus diisi."}), 400
        if not data['alamat']:
            return jsonify({"error": "Field 'alamat' harus diisi."}), 400
        if not data['no_kontak']:
            return jsonify({"error": "Field 'no_kontak' harus diisi."}), 400

        # Menangani file unggahan
        uploads_dir = os.path.join(current_app.root_path, 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)

        foto_umkm = request.files.get('foto_umkm')
        dokumen = request.files.get('dokumen')

        if foto_umkm:
            foto_umkm_path = os.path.join(uploads_dir, secure_filename(foto_umkm.filename))
            foto_umkm.save(foto_umkm_path)
            data['foto_umkm'] = foto_umkm_path

        if dokumen:
            dokumen_path = os.path.join(uploads_dir, secure_filename(dokumen.filename))
            dokumen.save(dokumen_path)
            data['dokumen'] = dokumen_path

        # Hanya admin yang bisa mengubah status_umkm
        if user_role == 'ADMIN' and request.form.get('status_umkm') is not None:
            data['status_umkm'] = request.form.get('status_umkm').lower() == 'true'

        # Memanggil fungsi update untuk memperbarui UMKM dengan data yang diperoleh
        response, status_code = update_umkm_by_id(umkm_id, data, user_role, id_user)
        return jsonify(response), status_code

    elif request.method == 'DELETE':
        umkm_id = request.form.get('id')
        if not umkm_id:
            return jsonify({"error": "Field 'id' harus diisi untuk menghapus UMKM."}), 400

        id_user = g.user['id']
        cur.execute('SELECT id_user FROM umkm WHERE id = %s;', (umkm_id,))
        umkm = cur.fetchone()

        if not umkm or umkm['id_user'] != id_user:
            return jsonify({"error": "You can only delete your own UMKM."}), 403

        cur.execute('DELETE FROM umkm WHERE id = %s RETURNING *;', (umkm_id,))
        umkm = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if umkm:
            return jsonify(umkm)
        else:
            return jsonify({'error': 'UMKM tidak ditemukan atau gagal dihapus'}), 404

    return jsonify({'error': 'Invalid method'}), 405

@umkm_bp.route('/umkm/<int:umkm_id>', methods=['GET'])
@user_or_admin_required
@umkm_suspended_check
def get_umkm_detail_route(umkm_id):
    umkm_detail = get_umkm_detail(umkm_id, g.user['role'])
    if not umkm_detail:
        return jsonify({'error': 'UMKM tidak ditemukan'}), 404
    return jsonify(umkm_detail)

@umkm_bp.route('/umkm', methods=['GET'])
def get_umkms_route():
    umkms = fetch_all_umkm()
    
    response = []
    for umkm in umkms:
        if umkm.get('status_umkm'):  # Menyaring UMKM yang aktif
            response.append({
                "id": umkm['id'],
                "nama": umkm['nama']
            })
        else:
            # Menggunakan dict untuk memastikan JSON serializable
            response.append({
                "message": f"data umkm dengan id: {umkm['id']} telah di suspended"
            })
    
    return jsonify(response), 200

# Endpoint untuk /umkm/user/<int:user_id>
@umkm_bp.route('/umkm/user/<int:user_id>', methods=['GET'])
def get_umkms_by_user(user_id):
    umkms = fetch_umkm_by_user_id(user_id)

    response = []
    for umkm in umkms:
        if umkm.get('status_umkm'):  # Menyaring UMKM yang aktif
            response.append({
                "id": umkm['id'],
                "nama": umkm['nama'],
                "alamat": umkm['alamat'],
                "deskripsi": umkm['deskripsi'],
                "dokumen": umkm.get('dokumen'),  # Memastikan dokumen ada
                "foto_umkm": umkm.get('foto_umkm'),  # Memastikan foto_umkm ada
                "jam_buka": umkm['jam_buka'],
                "kategori": umkm['kategori'],
                "no_kontak": umkm['no_kontak'],
                "npwp": umkm['npwp'],
                "products": umkm.get('products', []),  # Memastikan products ada dan default ke list kosong
                "status_umkm": umkm['status_umkm']
            })
        else:
            # Menggunakan dict untuk memastikan JSON serializable
            response.append({
                "message": f"data umkm dengan id: {umkm['id']} telah di suspended"
            })
    
    return jsonify(response), 200

@umkm_bp.route('/umkm/nonaktif', methods=['GET'])
@admin_required
def get_nonaktif_umkm():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if g.user['role'] == 'ADMIN':
        cur.execute('SELECT * FROM umkm WHERE status_umkm = FALSE;')
    else:
        cur.execute('SELECT * FROM umkm WHERE status_umkm = FALSE AND id_user = %s;', (g.user['id'],))

    umkms = cur.fetchall()
    umkm_data = []

    for umkm in umkms:
        cur.execute('SELECT * FROM produk WHERE id_umkm = %s;', (umkm['id'],))
        products = cur.fetchall()
        umkm['products'] = products
        umkm_data.append(umkm)

    cur.close()
    conn.close()

    return jsonify(umkm_data)

@umkm_bp.route('/umkm/nonaktif/<int:user_id>', methods=['GET', 'DELETE'])
@admin_required
def manage_nonaktif_umkm_by_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'GET':
        cur.execute('SELECT * FROM umkm WHERE id_user = %s AND status_umkm = FALSE;', (user_id,))
        umkms = cur.fetchall()
        if not umkms:
            cur.close()
            conn.close()
            return jsonify({'error': 'Tidak ada UMKM nonaktif ditemukan untuk user ini'}), 404

        umkm_data = []
        for umkm in umkms:
            cur.execute('SELECT * FROM produk WHERE id_umkm = %s;', (umkm['id'],))
            products = cur.fetchall()
            umkm['products'] = products
            umkm_data.append(umkm)
        
        cur.close()
        conn.close()
        return jsonify(umkm_data)

    elif request.method == 'DELETE':
        umkm_id = request.form.get('id')

        # Periksa apakah field id diisi
        if not umkm_id:
            cur.close()
            conn.close()
            return jsonify({"error": "Field 'id' wajib diisi untuk melakukan delete."}), 400

        cur.execute('SELECT * FROM umkm WHERE id = %s AND id_user = %s AND status_umkm = FALSE;', (umkm_id, user_id))
        umkm = cur.fetchone()
        if not umkm:
            cur.close()
            conn.close()
            return jsonify({'error': 'UMKM tidak ditemukan atau tidak nonaktif'}), 404

        cur.execute('DELETE FROM umkm WHERE id = %s AND id_user = %s AND status_umkm = FALSE RETURNING *;', (umkm_id, user_id))
        deleted_umkm = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(deleted_umkm)

    return jsonify({'error': 'Invalid method'}), 405

@umkm_bp.route('/umkm/status', methods=['PUT'])
@admin_required
def change_umkm_status():
    umkm_id = request.form.get('id')
    status = request.form.get('status')

    # Periksa apakah field 'id' dan 'status' diisi
    if not umkm_id:
        return jsonify({"error": "Field 'id' wajib diisi untuk mengubah status UMKM."}), 400
    if not status:
        return jsonify({"error": "Field 'status' wajib diisi untuk mengubah status UMKM."}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute('SELECT id_user FROM umkm WHERE id = %s;', (umkm_id,))
    umkm = cur.fetchone()

    if not umkm:
        cur.close()
        conn.close()
        return jsonify({'error': 'UMKM tidak ditemukan'}), 404

    cur.execute('''
        UPDATE umkm
        SET status_umkm = %s
        WHERE id = %s RETURNING *;
    ''', (status, umkm_id))
    umkm = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(umkm)

@umkm_bp.route('/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    return jsonify({"message": "Welcome to Admin lobby"})
