from flask import Blueprint, request, jsonify, g, current_app
from app.services.auth_service import add_user, authenticate_user
from app.middlewares.auth_middleware import user_or_admin_required, admin_required
import jwt
from config import Config
from app.services.user_service import get_user_by_id, get_all_users, get_first_empty_id
from app.services.umkm_service import get_umkms
from app.services.produk_service import get_all_produks
from psycopg2.extras import RealDictCursor
from app.utils.db import get_db_connection

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/auth', methods=['POST'])
def auth():
    no_hp = request.form.get('no_hp')
    password = request.form.get('password')
    role = request.form.get('role')

    # Dapat register jika sudah dapat role
    if role:
        current_app.logger.info(f"Attempting to register user with no_hp: {no_hp}, role: {role}")

        if not no_hp:
            return jsonify({'error': 'Nomor HP harus diisi'}), 400
        if not password:
            return jsonify({'error': 'Password harus diisi'}), 400
        if len(password) < 6:
            return jsonify({'error': 'Password harus minimal 6 karakter'}), 400

        valid_roles = ['USER', 'ADMIN']
        if role not in valid_roles:
            return jsonify({'error': f"Role tidak valid: {role}. Role harus salah satu dari {valid_roles}"}), 400

        try:
            # penggunaan id kosong
            empty_id = get_first_empty_id()
            if empty_id:
                user = add_user(no_hp, password, role, empty_id)
            else:
                return jsonify({'error': 'Tidak ada ID yang tersedia untuk digunakan'}), 500
            
            token = jwt.encode({'id': user['id'], 'no_hp': no_hp, 'role': role}, current_app.config['SECRET_KEY'], algorithm='HS256')
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'error': f"Gagal menghasilkan token: {str(e)}"}), 500

        return jsonify({
            'id': user['id'],
            'no_hp': user['no_hp'],
            'password': user['password'],
            'role': user['role'],
            'suspended': user.get('suspended'),
            'log': user['log'],
            'timestamp': user['timestamp'],
            'token': token
        }), 201

    # Jika role tidak diberikan, tidak dapat login
    else:
        current_app.logger.info(f"Attempting to login user with no_hp: {no_hp}")

        if not password:
            return {"error": "Password harus diisi"}, 400

        user = authenticate_user(no_hp, password)
        if user:
            try:

                token = jwt.encode({'id': user['id'], 'no_hp': no_hp, 'role': user['role']}, current_app.config['SECRET_KEY'], algorithm='HS256')
            except Exception as e:
                return jsonify({'error': f"Gagal menghasilkan token: {str(e)}"}), 500

            return jsonify({
                'message': 'Login successful',
                'token': token,
                'log': user['log'],
                'timestamp': user['timestamp']
            }), 200
        else:
            return jsonify({'error': 'Gagal mengenali!'}), 401

# endpoint /user
@user_bp.route('/user', methods=['GET', 'POST', 'PUT', 'DELETE'])
@user_or_admin_required
def manage_user():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        no_hp = request.form.get('no_hp')
        password = request.form.get('password')
        role = request.form.get('role')

        user = add_user(no_hp, password, role)
        return jsonify(user), 201

    elif request.method == 'GET':
        if g.user['role'] == 'ADMIN':
            cur.execute('SELECT * FROM "user";')
            users = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(users), 200
        else:
            user_id = g.user['id']
            cur.execute('SELECT * FROM "user" WHERE id = %s;', (user_id,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if not user:
                return jsonify({'error': 'User tidak ditemukan'}), 404
            return jsonify(user), 200

    elif request.method == 'PUT':
        # Gunakan ID dari form-data (khusus untuk admin)
        if g.user['role'] == 'ADMIN':
            user_id = request.form.get('id')
        else:
            user_id = g.user['id']

        # Ambil semua field yang mungkin ingin diperbarui
        no_hp = request.form.get('no_hp')
        password = request.form.get('password')
        role = request.form.get('role')

        # Pastikan id tidak dapat diubah
        if not user_id:
            return jsonify({'error': 'ID pengguna tidak boleh diubah'}), 400

        # Cek apakah no_hp sudah digunakan oleh pengguna lain
        if no_hp:
            cur.execute('SELECT id FROM "user" WHERE no_hp = %s AND id != %s;', (no_hp, user_id))
            existing_user = cur.fetchone()
            if existing_user:
                return jsonify({'error': 'Nomor HP sudah digunakan oleh pengguna lain'}), 409

        # query untuk update nilai
        update_fields = []
        update_values = []

        if no_hp:
            update_fields.append('no_hp = %s')
            update_values.append(no_hp)
        
        # Validasi password
        if password:
            if len(password) < 6:
                return jsonify({'error': 'Password harus minimal 6 karakter'}), 400
            update_fields.append('password = %s')
            update_values.append(password)

        # Validasi role
        if role:
            if role not in ['USER', 'ADMIN']:
                return jsonify({'error': 'Role harus diisi dengan "USER" atau "ADMIN"'}), 400
            if g.user['role'] == 'ADMIN':  # Hanya admin yang bisa mengubah role
                update_fields.append('role = %s')
                update_values.append(role)
            elif g.user['role'] == 'USER':  # User biasa tidak bisa mengubah role
                return jsonify({'error': 'Anda tidak memiliki izin untuk mengubah role'}), 403

        update_values.append(user_id)

        if update_fields:
            cur.execute(f'''
                UPDATE "user"
                SET {', '.join(update_fields)}
                WHERE id = %s RETURNING *;
            ''', tuple(update_values))

            updated_user = cur.fetchone()
            conn.commit()

            if updated_user:
                return jsonify(updated_user), 200
            else:
                return jsonify({'error': 'User tidak ditemukan atau gagal diperbarui'}), 404
        else:
            return jsonify({'error': 'Tidak ada data yang diperbarui'}), 400

    elif request.method == 'DELETE':
        user_id = request.form.get('id')

        # Validasi jika ID tidak diisi
        if not user_id:
            return jsonify({'error': 'ID pengguna harus diisi untuk menghapus'}), 400

        cur.execute('DELETE FROM "user" WHERE id = %s RETURNING *;', (user_id,))
        deleted_user = cur.fetchone()
        conn.commit()

        if deleted_user:
            return jsonify({'message': 'User deleted'}), 200
        else:
            return jsonify({'error': 'User tidak ditemukan'}), 404

    cur.close()
    conn.close()

# Endpoint /user/role
@user_bp.route('/user/role', methods=['PUT'])
@user_or_admin_required
def change_user_role():
    user_id = request.form.get('id')
    new_role = request.form.get('role')

    if not user_id or not new_role:
        return jsonify({'error': 'ID dan role baru diperlukan!'}), 400

    # Update role user menggunakan layanan yang sesuai
    return jsonify({'message': 'Role berhasil diubah!'})

# Endpoint /user/suspend
@user_bp.route('/user/suspend', methods=['PUT'])
@admin_required
def suspend_user():
    user_id = request.form.get('id')
    suspend_status = request.form.get('suspend')

    if not user_id or suspend_status not in ['true', 'false']:
        return jsonify({'error': 'ID dan status suspend yang valid diperlukan!'}), 400

    suspend_status_bool = True if suspend_status == 'true' else False

    conn = get_db_connection()
    cur = conn.cursor()

    # Update suspend status in the database
    cur.execute('''
        UPDATE "user" 
        SET suspended = %s 
        WHERE id = %s RETURNING *;
    ''', (suspend_status_bool, user_id))

    updated_user = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if updated_user:
        return jsonify({'message': f"User {'suspended' if suspend_status_bool else 'unsuspended'} successfully"}), 200
    else:
        return jsonify({'error': 'User tidak ditemukan atau gagal diperbarui'}), 404

# Endpoint /admin/add_user
@user_bp.route('/admin/add_user', methods=['POST'])
@admin_required
def admin_add_user():
    no_hp = request.form.get('no_hp')
    password = request.form.get('password')
    role = request.form.get('role', 'USER')

    # Validasi panjang password
    if len(password) < 6:
        return jsonify({'error': 'Password harus minimal 6 karakter'}), 400

    # Validasi role
    if role not in ['USER', 'ADMIN']:
        return jsonify({'error': 'Role tidak valid. Role yang diperbolehkan hanya "USER" atau "ADMIN".'}), 400

    user = add_user(no_hp, password, role)
    return jsonify(user), 201

# Endpoint /dashboard
@user_bp.route('/dashboard', methods=['GET'])
@user_or_admin_required
def get_dashboard():
    # Mengambil data UMKM
    umkms = get_umkms()

    # Mengambil data produk
    produks = get_all_produks()

    # Mengambil data user
    users = get_all_users()

    # Menghitung statistik UMKM
    umkm_statistik = []
    for umkm in umkms:
        produk_all = sum(1 for p in produks if p['id_umkm'] == umkm['id'])
        produk_publish = sum(1 for p in produks if p['id_umkm'] == umkm['id'] and p['is_publik'])
        produk_unpublish = produk_all - produk_publish
        
        umkm_statistik.append({
            "id": umkm['id'],
            "nama": umkm['nama'],
            "produk_all": produk_all,
            "produk_publish": produk_publish,
            "produk_unpublish": produk_unpublish
        })

    # Menyusun response JSON
    response = {
        "produks": [],
        "total_produk": len(produks),
        "total_publish": sum(1 for p in produks if p['is_publik']),
        "total_umkm": len(umkms),
        "total_unpublish": len(produks) - sum(1 for p in produks if p['is_publik']),
        "umkm_statistik": umkm_statistik,
        "umkms": umkm_statistik,
        "users": users
    }

    return jsonify(response)
