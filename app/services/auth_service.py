import jwt
from flask import current_app as app
from app.utils.db import get_db_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime

def add_user(no_hp, password, role, user_id):
    # Validasi role
    valid_roles = ['USER', 'ADMIN']
    if role not in valid_roles:
        raise ValueError(f"Role tidak valid: {role}. Role harus salah satu dari {valid_roles}")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    timestamp = datetime.now()

    cur.execute('''
        INSERT INTO "user" (id, no_hp, log, password, role, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING *;
    ''', (user_id, no_hp, f'Registration log: {timestamp}', password, role, timestamp))
    
    user = cur.fetchone()
    conn.commit()

    token = jwt.encode({'id': user['id'], 'no_hp': no_hp, 'role': role}, app.config['SECRET_KEY'], algorithm='HS256')

    # Update token di database
    cur.execute('''
        UPDATE "user" SET token = %s WHERE id = %s;
    ''', (token, user['id']))
    conn.commit()

    # Memasukkan token ke dalam objek user
    user['token'] = token

    cur.close()
    conn.close()
    return user

def authenticate_user(no_hp, password):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute('SELECT * FROM "user" WHERE no_hp = %s;', (no_hp,))
    user = cur.fetchone()

    if user and user['password'] == password:
        # Mencatat login dengan timestamp
        timestamp = datetime.now()
        log = f"Login successful: {timestamp}"
        
        # Memperbarui log di database
        cur.execute('''
            UPDATE "user" SET log = %s, timestamp = %s WHERE id = %s;
        ''', (log, timestamp, user['id']))
        conn.commit()

        # Menambahkan log dan timestamp ke dalam objek user
        user['log'] = log
        user['timestamp'] = timestamp

        cur.close()
        conn.close()
        return user
    else:
        cur.close()
        conn.close()
        return None
