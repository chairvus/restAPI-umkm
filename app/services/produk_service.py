from app.utils.db import get_db_connection

def add_produk(produk_data):
    conn = get_db_connection()
    cur = conn.cursor()

    # Log untuk mengecek id_umkm sebelum query
    print(f"Checking existence of UMKM ID: {produk_data['id_umkm']}")
    
    # Validasi id_umkm sebelum insert produk
    cur.execute('SELECT * FROM umkm WHERE id = %s;', (produk_data['id_umkm'],))
    if cur.fetchone() is None:
        conn.close()
        return {"error": "UMKM ID tidak ditemukan"}, 404

    cur.execute('''
        INSERT INTO produk (id_umkm, kode_produk, nama_produk, deskripsi, harga, masa_berlaku, foto_produk, is_publik)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
    ''', (
        produk_data['id_umkm'], produk_data['kode_produk'], produk_data['nama_produk'], produk_data['deskripsi'], 
        produk_data['harga'], produk_data['masa_berlaku'], produk_data['foto_produk'], produk_data['is_publik']
    ))
    produk = cur.fetchone()
    umkm_result = cur.fetchone()
    print(f"Query Result for UMKM: {umkm_result}")
    if umkm_result is None:
        conn.close()
        return {"error": "UMKM ID tidak ditemukan"}, 404

    conn.commit()
    cur.close()
    conn.close()

    return produk

def get_all_produks():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, id_umkm, is_publik FROM produk')
    produks = cur.fetchall()
    cur.close()
    conn.close()
    
    return [{"id": p[0], "id_umkm": p[1], "is_publik": p[2]} for p in produks]
