from flask import Flask
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt

mysql = MySQL()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    
    app.config.from_object('config.Config')
    
    mysql.init_app(app)
    bcrypt.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    return app