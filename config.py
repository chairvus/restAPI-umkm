import os
import logging

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    DATABASE = {
        'dbname': 'umkm',
        'user': 'postgres',
        'password': 'artha',
        'host': 'localhost'
    }
    
    # Logging configuration
    LOG_LEVEL = logging.DEBUG
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
