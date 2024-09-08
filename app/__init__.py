from flask import Flask
from config import Config
import logging
from app.middlewares.auth_middleware import authenticate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Set up logging
    logging.basicConfig(level=app.config['LOG_LEVEL'], format=app.config['LOG_FORMAT'])
    app.logger = logging.getLogger(__name__)

    # Daftarkan middleware untuk menjalankan sebelum setiap request
    app.before_request(authenticate)

    from .routes.user_routes import user_bp
    from .routes.umkm_routes import umkm_bp
    from .routes.produk_routes import produk_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(umkm_bp)
    app.register_blueprint(produk_bp)

    return app