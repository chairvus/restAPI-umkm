from app.utils.db import get_db_connection

# Function for get user by id
def get_user_by_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM "user" WHERE id = %s;', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    return user

# Function to get all users
def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, log, no_hp, role, suspended FROM "user"')
    users = cur.fetchall()
    cur.close()
    conn.close()
    
    return [{"id": u[0], "log": u[1], "no_hp": u[2], "role": u[3], "suspended": u[4]} for u in users]

# New Function to find the first available empty ID
def get_first_empty_id():
    conn = get_db_connection()
    cur = conn.cursor()

    # Cari ID yang kosong di tabel user
    cur.execute('''
        SELECT id + 1 AS next_id
        FROM "user" u
        WHERE NOT EXISTS (
            SELECT 1
            FROM "user" u2
            WHERE u2.id = u.id + 1
        )
        ORDER BY id
        LIMIT 1;
    ''')

    result = cur.fetchone()
    cur.close()
    conn.close()

    if result:
        return result[0]
    else:
        return None