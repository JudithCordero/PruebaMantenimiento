from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from flask import Flask
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

#inicializar la instancia de la aplicacion--------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///agencia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#inicializar la base de datos
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#crear el modelo de la base de datos
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Product {self.name} - available {self.quantity}>'

#rutas-------------------------------------

#pagina principal
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)







# Otras rutas...

# Ruta para mostrar el formulario de inicio de sesión
@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

# Ruta para manejar el inicio de sesión
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    # Verificar si el nombre de usuario y la contraseña son correctos (aquí debes agregar tu lógica de autenticación)
    if username == 'usuario' and password == 'contraseña':
        # Aquí podrías agregar la lógica para iniciar sesión, como establecer una cookie de sesión
        # Por ahora, redireccionaremos al usuario a la página de inicio
        return redirect(url_for('index'))
    else:
        # Si las credenciales son incorrectas, volver al formulario de inicio de sesión con un mensaje de error
        return render_template('login.html', error='Credenciales incorrectas. Inténtalo de nuevo.')

# Otras rutas...







# Ruta para mostrar el formulario de inicio de sesión como administrador
@app.route('/login/admin', methods=['GET'])
def login_admin():
    return render_template('login_admin.html')

# Ruta para manejar el inicio de sesión como administrador
@app.route('/login/admin', methods=['POST'])
def login_admin_post():
    username = request.form.get('username')
    password = request.form.get('password')

    # Verificar si el nombre de usuario y la contraseña son correctos (aquí debes agregar tu lógica de autenticación para administradores)
    if username == 'admin' and password == 'contraseña_admin':
        # Aquí podrías agregar la lógica para iniciar sesión como administrador, como establecer una cookie de sesión
        # Por ahora, redireccionaremos al usuario a la página de inicio
        return redirect(url_for('index'))
    else:
        # Si las credenciales son incorrectas, volver al formulario de inicio de sesión de administrador con un mensaje de error
        return render_template('login_admin.html', error='Credenciales incorrectas. Inténtalo de nuevo.')


# Ruta para mostrar el formulario de inicio de sesión como cliente
@app.route('/login/client', methods=['GET'])
def login_client():
    return render_template('login_client.html')

# Ruta para manejar el inicio de sesión como cliente
@app.route('/login/client', methods=['POST'])
def login_client_post():
    username = request.form.get('username')
    password = request.form.get('password')

    # Verificar si el nombre de usuario y la contraseña son correctos (aquí debes agregar tu lógica de autenticación para clientes)
    if username == 'cliente' and password == 'contraseña_cliente':
        # Aquí podrías agregar la lógica para iniciar sesión como cliente, como establecer una cookie de sesión
        # Por ahora, redireccionaremos al usuario a la página de inicio
        return redirect(url_for('index'))
    else:
        # Si las credenciales son incorrectas, volver al formulario de inicio de sesión de cliente con un mensaje de error
        return render_template('login_client.html', error='Credenciales incorrectas. Inténtalo de nuevo.')








#create
@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        quantity = request.form['quantity']
        new_product = Product(name=name, price=price, quantity=quantity)
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('list_products'))
    return render_template('add_products.html')

#read
@app.route('/catalog')
def list_products():
    products = Product.query.all()
    return render_template('list_products.html', products=products)

#update
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = request.form['price']
        product.quantity = request.form['quantity']
        db.session.commit()
        return redirect(url_for('list_products'))
    return render_template('update_product.html', product=product)

#delete
@app.route('/delete/<int:id>')
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('list_products'))

#client view
@app.route('/client')
def client():
    products = Product.query.all()
    return render_template('client.html', products=products)

#correr la aplicacion
if __name__=='__main__':
    app.run(debug=True)