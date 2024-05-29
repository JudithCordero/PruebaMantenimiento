from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_sqlalchemy import SQLAlchemy
# Importar Enum para usar en el modelo
from sqlalchemy import Enum, func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, timedelta

from flask_socketio import SocketIO, emit

from reportlab.pdfgen import canvas
from io import BytesIO

import uuid

# Inicializar la instancia de la aplicación
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agencia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Añadir la configuración de la clave secreta para las sesiones
app.config['SECRET_KEY'] = 'your_secret_key'

#verificacion de la persistencia de la sesion
app.config['SESSION_TYPE'] = 'filesystem'


# Inicializar la base de datos
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)

# Crear el modelo de la base de datos
# Clase Producto
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    type = db.Column(Enum('refacciones', 'servicios', name='product_type'), nullable=False)

    def __repr__(self):
        return f'<Product {self.name} - available {self.quantity}>'

# Clase Usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name_p = db.Column(db.String(100), nullable=False)
    last_name_m = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    cars = db.relationship('Car', backref='client', lazy=True)

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    type = db.Column(Enum('car', 'truck', name='car_type'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)


class CashPaymentSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, nullable=False)
    car_id = db.Column(db.Integer, nullable=True)  # Puede ser nulo si no se selecciona un coche específico
    total = db.Column(db.Float, nullable=False)
    payment_datetime = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f'<CashPaymentSummary(client_id={self.client_id}, total={self.total}, payment_datetime={self.payment_datetime})>'
        



# Modelo para las órdenes de servicio
class ServiceOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    service_datetime = db.Column(db.DateTime, nullable=False)
    address = db.Column(db.String(200))
    status = db.Column(db.String(50), nullable=False, default='Pending')  # Agregar la columna status con valor predeterminado

    client = db.relationship('Client', backref=db.backref('service_orders', lazy=True))
    car = db.relationship('Car', backref=db.backref('service_orders', lazy=True))

def create_order(client_id, car_id, service_type, service_datetime, address, status='Pending'):
    new_order = ServiceOrder(
        client_id=client_id,
        car_id=car_id,
        service_type=service_type,
        service_datetime=service_datetime,
        address=address,
        status=status
    )
    db.session.add(new_order)
    db.session.commit()

def get_order_by_id(order_id):
    return ServiceOrder.query.get(order_id)

def update_order(order_id, service_type, service_datetime, address, status):
    order_to_update = ServiceOrder.query.get(order_id)
    if order_to_update:
        order_to_update.status = status
        order_to_update.address = address
        order_to_update.service_datetime = service_datetime
        order_to_update.service_type = service_type
        db.session.commit()

def delete_order(order_id):
    order_to_delete = ServiceOrder.query.get(order_id)
    if order_to_delete:
        db.session.delete(order_to_delete)
        db.session.commit()

def list_orders():
    return ServiceOrder.query.all()

def get_car_by_id(car_id):
    return Car.query.get(car_id)

# Función para obtener los productos del carrito
def get_cart_products():
    cart = session.get('cart', [])
    return Product.query.filter(Product.id.in_(cart)).all()

from app import CashPaymentSummary

#front Cliente

@app.route('/cash_payment_summary/<float:total>')
def cash_payment_summary(total):
    client_id = session.get('client_id')
    if not client_id:
        return redirect(url_for('login_client'))

    car_id = session.get('car_id')
    car = Car.query.get(car_id) if car_id and car_id != 'all' else None

    # Guardar los datos en la base de datos
    cash_payment = CashPaymentSummary(client_id=client_id, car_id=car_id, total=total)
    db.session.add(cash_payment)
    db.session.commit()

    client = Client.query.get(client_id)
    cart = session.get('cart', [])
    selected_products = Product.query.filter(Product.id.in_(cart)).all()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    address = session.get('address', 'NA')

    dia_disponible = find_available_date(datetime.now().date(), datetime.now().date()+timedelta(days=30))
    for product in selected_products:
        create_order(client_id, car_id, product.name, dia_disponible, address, status='Pending')
    
    session.clear()
    return render_template('cash_payment_summary.html', client=client, car=car, selected_products=selected_products, total=total, current_time=current_time, dia_disponible=dia_disponible)



@app.route('/list_paid_services')
def list_paid_services():
    # Recupera todos los registros de CashPaymentSummary desde la base de datos
    paid_services = CashPaymentSummary.query.all()
    return render_template('list_paid_services.html', paid_services=paid_services)

@app.route('/payment_method')
def payment_method():
    total = session.get('total')
    return render_template('payment_method.html', total=total)




#backend
# Ruta para proceder al pago
@app.route('/proceed_payment', methods=['POST'])
def proceed_payment():
    car_id = request.form.get('car_selection')
    service_type = request.form.get('service_type')
    address = request.form.get('address', None)
    total = request.form.get('total')

    # Guardar la información necesaria en la sesión
    session['car_id'] = car_id
    session['service_type'] = service_type
    session['address'] = address
    session['total'] = total

    return redirect(url_for('payment_method'))


# Rutas

# Página principal
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

# Registro de clientes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name_p = request.form['last_name_p']
        last_name_m = request.form['last_name_m']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        cars = []
        num_cars = int(request.form['num_cars'])
        for i in range(num_cars):
            car_name = request.form[f'car_name_{i}']
            car_model = request.form[f'car_model_{i}']
            car_type = request.form[f'car_type_{i}']
            car = Car(name=car_name, model=car_model, type=car_type)
            cars.append(car)
        new_client = Client(first_name=first_name, last_name_p=last_name_p, last_name_m=last_name_m,
                            email=email, phone=phone, username=username, password=password, cars=cars)
        try:
            db.session.add(new_client)
            db.session.commit()
            return redirect(url_for('login_client'))
        except Exception as e:
            db.session.rollback()
            return f"Error al registrar cliente: {e}", 500
    return render_template('register.html')


# Función para inicializar la sesión del carrito
@app.before_request
def before_request():
    if 'cart' not in session:
        session['cart'] = []






# Otras rutas......

# Crear
@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        quantity = request.form['quantity']
        type = request.form['type']
        new_product = Product(name=name, price=price, quantity=quantity, type=type)
        try:
            db.session.add(new_product)
            db.session.commit()
            return redirect(url_for('list_products'))
        except Exception as e:
            db.session.rollback()
            return f"Error al agregar producto: {e}", 500
    return render_template('add_products.html')

# Leer
@app.route('/catalog')
def list_products():
    print(session, '\n\n\n\n\n\n\n')
    if 'is_admin' in session:
        products = Product.query.all()
        return render_template('list_products.html', products=products)
    else:
        return redirect(url_for('login_admin'))

# Actualizar
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_product(id):
    if 'is_admin' in session:
        product = Product.query.get_or_404(id)
        if request.method == 'POST':
            product.name = request.form['name']
            product.price = request.form['price']
            product.quantity = request.form['quantity']
            product.type = request.form['type']
            try:
                db.session.commit()
                return redirect(url_for('list_products'))
            except Exception as e:
                db.session.rollback()
                return f"Error al actualizar producto: {e}", 500
        return render_template('update_product.html', product=product)
    else:
        return redirect(url_for('login_admin'))

# Eliminar
@app.route('/delete/<int:id>')
def delete_product(id):
    if 'is_admin':
        product = Product.query.get_or_404(id)
        try:
            db.session.delete(product)
            db.session.commit()
            return redirect(url_for('list_products'))
        except Exception as e:
            db.session.rollback()
            return f"Error al eliminar producto: {e}", 500
    else:
        return redirect(url_for('login_admin'))




# Página principal del cliente
@app.route('/client')
def client():
    if 'client_id' not in session:
        return redirect(url_for('login_client'))

    client_id = session['client_id']
    #client = Client.query.get(client_id)
    products = Product.query.all()
    return render_template('client.html', client=client, products=products, cart=session['cart'])


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    cart = session.get('cart', [])
    cart.append(product_id)
    session['cart'] = cart
    print(f"Added product {product_id} to cart: {cart}")  # Mensaje de depuración
    return {'success': True}

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    if product_id in cart:
        cart.remove(product_id)
        session['cart'] = cart
    print(f"Removed product {product_id} from cart: {cart}")  # Mensaje de depuración
    return redirect(url_for('view_cart'))


    # Verificar disponibilidad de la fecha y hora
    service_datetime = datetime.strptime(f"{service_date} {service_time}", '%Y-%m-%d %H:%M')
    if not is_service_datetime_available(service_datetime):
        return "La fecha y hora seleccionada ya están ocupadas. Por favor, elija otra fecha y hora.", 400

    # Lógica para manejar la reserva
    if car_selection == 'all':
        for car in client.cars:
            create_service_order(client, car, service_type, service_datetime, address)
    else:
        car = Car.query.get(car_selection)
        create_service_order(client, car, service_type, service_datetime, address)

    return redirect(url_for('client'))

def is_service_datetime_available(service_date):
    # Aquí puedes implementar la lógica para verificar si la fecha y hora están disponibles
    # Por ejemplo, consultando la base de datos para ver si ya existe una reserva en ese momento
    existing_orders = ServiceOrder.query.filter(func.date(ServiceOrder.service_datetime) == service_date).first()
    return existing_orders is None

def find_available_date(start_date, end_date):
    current_date = start_date
    while current_date <= end_date:
        if is_service_datetime_available(current_date):
            return current_date
        current_date += timedelta(days=1)
    return None

def create_service_order(client, car, service_type, service_datetime, address):
    new_order = ServiceOrder(
        client_id=client.id,
        car_id=car.id,
        service_type=service_type,
        service_datetime=service_datetime,
        address=address
    )
    db.session.add(new_order)
    db.session.commit()




@app.route('/admin/payments_in_process')
def payments_in_process():
    if not session.get('is_admin'):
        return redirect(url_for('login_admin'))

    orders = ServiceOrder.query.filter_by(status='Pending').all()
    return render_template('payments_in_process.html', orders=orders)



@app.route('/logout')
def logout():
    session.pop('client_id', None)
    return redirect(url_for('login'))


@app.route('/logout_admin')
def logout_admin():
    session.pop('is_admin', None)
    return redirect(url_for('login_admin'))




# Ruta para mostrar el formulario de inicio de sesión
@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

# Ruta para mostrar el formulario de inicio de sesión como administrador
@app.route('/login/admin', methods=['GET'])
def login_admin():
    if 'is_admin' in session:
        return redirect(url_for('list_products'))
    else:
        return render_template('login_admin.html')

# Ruta para manejar el inicio de sesión como administrador
@app.route('/login/admin', methods=['POST'])
def login_admin_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == 'admin' and password == 'contraseña_admin':
        session['is_admin'] = True  # Marcar al usuario como administrador
        return redirect(url_for('list_products'))
    else:
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

    client = Client.query.filter_by(username=username).first()

    if client and check_password_hash(client.password, password):
        session['client_id'] = client.id
        return redirect(url_for('client'))
    else:
        return render_template('login_client.html', error='Credenciales incorrectas. Inténtalo de nuevo.')

@app.route('/clients')
def list_clients():
    if 'is_admin' in session:
        clients = Client.query.all()
        return render_template('list_clients.html', clients=clients)
    else:
        return redirect(url_for('login_admin'))


@app.route('/services')
def list_services():
    if 'is_admin' in session:
        service_orders = list_orders()
        next_day = find_available_date(datetime.now().date(), datetime.now().date()+timedelta(days=30))
        return render_template('list_services.html', orders=service_orders, next_day=next_day)
    else:
        return redirect(url_for('login_admin'))

@app.route('/update_service_order/<int:order_id>')
def update_service_order(order_id):
    if 'is_admin' in session:
        order = get_order_by_id(order_id)
        fecha = order.service_datetime.strftime('%Y-%m-%dT%H:%M')
        products = Product.query.all()
        return render_template('edit_service.html', order=order, products=products, fecha=fecha)
    else:
        return redirect(url_for('login_admin'))

@app.route('/update_service_order/<int:order_id>', methods=['POST'])
def update_service_order_post(order_id):
    if 'is_admin' in session:
        service_type = request.form.get('service_type')
        address = request.form.get('address')
        service_datetime = datetime.strptime(request.form.get('service_datetime'), '%Y-%m-%dT%H:%M')
        status = request.form.get('status')
        print(order_id, '\n', service_type, '\n', service_datetime, '\n', address, '\n', status, '\n\n\n\n\n\n\n\n')
        update_order(order_id, service_type, service_datetime, address, status)
        return redirect(url_for('list_services'))
    else:
        return redirect(url_for('login_admin'))

@app.route('/delete_service_order/<int:order_id>')
def delete_service_order(order_id):
    if 'is_admin' in session:
        delete_order(order_id)
        return redirect(url_for('list_services'))
    else:
        return redirect(url_for('login_admin'))

@app.route('/comprobante/<int:order_id>')
def generar_comprobante(order_id):
    order = get_order_by_id(order_id)
    client = Client.query.get(order.client_id)
    car  = get_car_by_id(order.car_id)

    buffer = BytesIO()  
    p = canvas.Canvas(buffer)

    p.drawString(100, 800, "Comprobante de Orden de Servicio")
    p.drawString(100, 750, f"ID de Orden: {order.id}")
    p.drawString(100, 730, f"Cliente: {client.first_name} {client.last_name_p} {client.last_name_m}")
    p.drawString(100, 710, f"Coche: {car.name}, {car.model}")
    p.drawString(100, 690, f"Tipo de Servicio: {order.service_type}")
    p.drawString(100, 670, f"Fecha y Hora del Servicio: {order.service_datetime}")
    p.drawString(100, 650, f"Dirección: {order.address}")
    p.drawString(100, 630, f"Estado: {order.status}")

    p.showPage()
    p.save()

    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=comprobante_orden_{order.id}.pdf'
    return response

def upgrade():
    # Agrega la columna status sin un valor predeterminado
    with op.batch_alter_table('service_order') as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=False))

def downgrade():
    # Elimina la columna status
    with op.batch_alter_table('service_order') as batch_op:
        batch_op.drop_column('status')



        

from datetime import datetime

@app.route('/handle_payment', methods=['POST'])
def handle_payment():
    client_id = session.get('client_id')
    if not client_id:
        return redirect(url_for('login_client'))
    client = Client.query.get(client_id)
    cart = session.get('cart', [])
    selected_products = Product.query.filter(Product.id.in_(cart)).all()
    total = sum(product.price for product in selected_products)
    payment_method = request.form.get('payment_method')

    if payment_method == 'cash':
        # Redirigir a la página de resumen para pagos en efectivo
        return redirect(url_for('cash_payment_summary', total=total))
    elif payment_method == 'card':
        # Redirigir a la página para ingresar detalles de tarjeta
        return redirect(url_for('payment_card_details', total=total))
    else:
        return "Método de pago no válido", 400






@app.route('/store_payment_receipt')
def store_payment_receipt():
    if 'client_id' not in session:
        return redirect(url_for('login_client'))

    client_id = session['client_id']
    #client = Client.query.get(client_id)

    # Lógica para mostrar la boleta y clave especial

    return render_template('store_payment_receipt.html', client=client)

@app.route('/payment_success')
def payment_success():
    if 'client_id' not in session:
        return redirect(url_for('login_client'))

    client_id = session['client_id']
    #client = Client.query.get(client_id)

    # Lógica para mostrar la confirmación del pago exitoso

    return render_template('payment_success.html', client=client)


@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    client_id = session.get('client_id')
    if not client_id:
        return redirect(url_for('login_client'))

    car_id = session.get('car_id')
    total = session.get('total')
    service_type = session.get('service_type')
    address = session.get('address')

    # Crear una nueva orden de servicio y marcarla como pagada
    new_order = ServiceOrder(
        client_id=client_id,
        car_id=car_id,
        service_type=service_type,
        service_datetime=datetime.now(),
        address=address,
        status='Paid'
    )
    db.session.add(new_order)
    db.session.commit()

    # Limpiar la sesión
    session.pop('car_id', None)
    session.pop('total', None)
    session.pop('service_type', None)
    session.pop('address', None)
    session.pop('cart', [])

    return render_template('payment_success.html', client=Client.query.get(client_id))



@app.route('/view_cart', methods=['GET', 'POST'])
def view_cart():
    if 'client_id' not in session:
        return redirect(url_for('login_client'))

    if request.method == 'POST':
        selected_car_id = request.form.get('car_id')
        session['selected_car_id'] = int(selected_car_id)

    client_id = session['client_id']
    client = Client.query.get(client_id)
    cars = client.cars
    cart = session.get('cart', [])
    selected_products = Product.query.filter(Product.id.in_(cart)).all()
    total = sum(product.price for product in selected_products)
    return render_template('view_cart.html', client=client, cars=cars, total=total, products=selected_products)


@app.route('/dashboard')
def dashboard():
    if 'is_admin' in session:
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login_admin'))

@socketio.on('connect')
def handle_connect():
    emit('service_orders', get_service_orders())

def get_service_orders():
    orders = ServiceOrder.query.all()
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'client_id': order.client_id,
            'car_id': order.car_id,
            'service_type': order.service_type,
            'service_datetime': order.service_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'address': order.address,
            'status': order.status
        })
    return orders_data

@socketio.on('request_service_orders')
def handle_request_service_orders():
    emit('service_orders', get_service_orders())



# Correr la aplicación
if __name__ == '__main__':
    app.run(debug=True)