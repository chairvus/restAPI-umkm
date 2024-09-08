from flask import Blueprint, request, jsonify
from app.middlewares.auth_middleware import user_or_admin_required
from app.middlewares.produk_middleware import umkm_action_allowed, umkm_suspended_check
from app.services.produk_service import add_produk

produk_bp = Blueprint('produk_bp', __name__)

@produk_bp.route('/produk', methods=['GET', 'POST', 'PUT', 'DELETE'])
@user_or_admin_required
@umkm_action_allowed
@umkm_suspended_check
def manage_produk():
    if request.method == 'POST':
        id_umkm = request.form.get('id_umkm')
        
        # Tambahkan log untuk memeriksa apakah id_umkm diterima
        print(f"Received id_umkm in POST request: {id_umkm}")
        
        kode_produk = request.form.get('kode_produk')
        nama_produk = request.form.get('nama_produk')
        deskripsi = request.form.get('deskripsi')
        harga = request.form.get('harga')
        masa_berlaku = request.form.get('masa_berlaku')
        foto_produk = request.files.get('foto_produk')
        is_publik = request.form.get('is_publik', 'FALSE')

        produk_data = {
            'id_umkm': id_umkm,
            'kode_produk': kode_produk,
            'nama_produk': nama_produk,
            'deskripsi': deskripsi,
            'harga': harga,
            'masa_berlaku': masa_berlaku,
            'foto_produk': foto_produk.filename if foto_produk else None,
            'is_publik': is_publik
        }
        # Call service to add produk here
        # Misalnya:
        result = add_produk(produk_data)
        if "error" in result:
            return jsonify(result), 404
        return jsonify(result), 201

    elif request.method == 'PUT':
        produk_id = request.form.get('id')
        is_publik = request.form.get('is_publik')

        produk_data = {
            'id': produk_id,
            'is_publik': is_publik
        }
        # Call service to update produk here
        return jsonify(produk_data)

    elif request.method == 'DELETE':
        produk_id = request.form.get('id')
        # Call service to delete produk here
        return jsonify({'message': 'Produk deleted'})

    elif request.method == 'GET':
        # Ambil parameter dari form-data atau query parameters
        nama_produk = request.args.get('nama_produk') or request.form.get('nama_produk')
        kategori = request.args.get('kategori') or request.form.get('kategori')

        # Contoh data produk
        produk_data = [
            {"id": 1, "nama": "Produk A", "harga": 10000, "kategori": "elektronik"},
            {"id": 2, "nama": "Produk B", "harga": 15000, "kategori": "fashion"},
            {"id": 3, "nama": "Produk C", "harga": 20000, "kategori": "elektronik"},
        ]

        # Filter produk berdasarkan query parameters atau form-data jika ada
        if nama_produk:
            produk_data = [produk for produk in produk_data if nama_produk.lower() in produk['nama'].lower()]
        if kategori:
            produk_data = [produk for produk in produk_data if kategori.lower() == produk['kategori'].lower()]

        # Call service to get produk here
        return jsonify(produk_data)

    return jsonify({"error": "Method not allowed"}), 405

@produk_bp.route('/produk/publish', methods=['PUT'])
@user_or_admin_required
def publish_produk():
    produk_id = request.form.get('id')
    is_publik = request.form.get('is_publik')

    # Call service to publish produk here
    return jsonify({'message': 'Produk publish status updated'})
