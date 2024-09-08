from flask import request, jsonify, g
import jwt
from functools import wraps
from app.utils.db import get_db_connection
from config import Config

# Function Authorization
def authenticate():
    exempt_routes = ['/auth']
    if request.path not in exempt_routes:
        token = request.headers.get('Authorization')
        if token and token.startswith("Bearer "):
            token = token[7:]
            try:
                decoded_token = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
                if 'role' in decoded_token and 'id' in decoded_token:
                    g.user = decoded_token

                    # Cek apakah user disuspend
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute('SELECT suspended FROM "user" WHERE id = %s;', (g.user['id'],))
                    user = cur.fetchone()
                    cur.close()
                    conn.close()

                    if user and user[0]:  # Jika user disuspend
                        return jsonify({'error': 'Akun Anda disuspend'}), 403
                else:
                    return jsonify({'error': 'Token tidak valid, atribut hilang'}), 401
            except jwt.InvalidTokenError as e:
                return jsonify({'error': f'salah token!!: {str(e)}'}), 401
        else:
            return jsonify({'error': 'Hak akses tidak ada'}), 401

def admin_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if not hasattr(g, 'user') or g.user.get('role') != 'ADMIN':
            return jsonify({'error': 'Admin only'}), 403
        return f(*args, **kwargs)
    return decorator

def user_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if not hasattr(g, 'user') or g.user.get('role') != 'USER':
            return jsonify({'error': 'User only'}), 403
        return f(*args, **kwargs)
    return decorator

def user_or_admin_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        try:
            if not hasattr(g, 'user') or g.user.get('role') not in ['USER', 'ADMIN']:
                print(f"g.user: {g.user}") #debugging
                return jsonify({'error': 'User or Admin only'}), 403
        except AttributeError as e:
            print(f"AttributeError: {e}") #debugging
            return jsonify({'error': 'Hak akses tidak ada, user tidak valid'}), 403
        return f(*args, **kwargs)
    return decorator

def admin_or_owner_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        user_id = request.view_args.get('user_id')
        if not hasattr(g, 'user') or (g.user.get('role') != 'ADMIN' and g.user.get('id') != int(user_id)):
            return jsonify({'error': 'Anda tidak diizinkan untuk mengakses atau mengubah UMKM ini'}), 403
        return f(*args, **kwargs)
    return decorator