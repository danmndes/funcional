from flask import Flask, jsonify, request, render_template, redirect, url_for
from models import db, User, Merchant, Charity, Product
from flask_bcrypt import Bcrypt
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
import qrcode
from io import BytesIO
import base64
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.config["SECRET_KEY"] = "mysecretkey"
db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    models = [User, Merchant, Charity]
    return next((model.query.get(int(user_id)) for model in models if model.query.get(int(user_id))), None)

with app.app_context():
    db.create_all()  # Roda para criar o Banco de Dados

def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffered = BytesIO()
    path = f"static/QR{current_user.id}.png"
    img.save(buffered)  # Correção: salvar no buffer
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str, path

# Função Lambda para verificar se um produto é visível
is_visible = lambda checkbox: checkbox is not None

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    if current_user.tipo == 'merchant':
        form = request.form
        name = form.get('name')
        description = form.get('description')
        price = float(form.get('price'))
        discount = float(form.get('discount', 0))
        visible = is_visible(form.get('checkbox'))  # Utiliza a função lambda
        
        qr_code_data = f"Produto: {name}, Desconto: {discount}%"
        qr_code, path = generate_qr_code(qr_code_data)
        
        product = Product(
            name=name,
            description=description,
            price=price,
            discount=discount,
            qr_code=qr_code,
            merchant_id=current_user.id,
            visible=visible,
            path=path
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({"success": True, "message": "Produto adicionado com sucesso"}), 201
    return jsonify({"error": "Unauthorized"}), 403

@app.route('/view_all_products')
@login_required
def view_all_products():
    # List comprehension para obter produtos visíveis
    produtos = [p for p in Product.query.filter_by(merchant_id=current_user.id).all() if p.visible]
    return render_template('view_all_products.html', products=produtos)

@app.route('/add_product_form')
def add_product_form():
    return render_template('add_product_form.html')

# Função de alta ordem para autenticar usuários
def authenticate_user(username, password, models):
    def check_password(user):
        return user and bcrypt.check_password_hash(user.password, password)
    
    user = next((model.query.filter_by(username=username).first() for model in models), None)
    return user if check_password(user) else None

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        form_remember = 'remember' in request.form
        
        user = authenticate_user(username, password, [User, Merchant, Charity])  # Passa modelos para a função de alta ordem
        
        if user:
            login_user(user, remember=form_remember)
            return jsonify({"redirect": url_for('dashboard')})
        return jsonify({"error": "Usuário não encontrado ou senha incorreta"}), 403
    
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    paginated_merchants = Merchant.query.paginate(page=page, per_page=per_page, error_out=False)
    
    template = 'nonuser_dashboard.html' if current_user.tipo != "user" else 'dashboard.html'
    username = current_user.shop_name if current_user.tipo != "user" else current_user.username
    products = Product.query.filter_by(merchant_id=current_user.id)
    
    return render_template(
        template,
        username=username,
        merchants=paginated_merchants.items,
        page=page,
        pages=paginated_merchants.pages,
    )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/get_users', methods=['GET'])
def get_all_users():
    # List comprehension para obter perfis
    profiles = [profile for model in [User, Merchant, Charity] for profile in model.query.all()]
    all_profiles = [{
        "username": profile.username,
        "email": profile.email,
        "tipo": profile.tipo,
        "shop_name": getattr(profile, 'shop_name', None)
    } for profile in profiles]
    return jsonify(all_profiles)

# Closure para criar uma função de busca de usuário
def create_user_search_function(model):
    def search_user(username):
        return model.query.filter_by(username=username).first()
    return search_user

search_user = create_user_search_function(User)  # Exemplo de uso da closure para User

@app.route('/profile/<username>')
def profile(username):
    user = search_user(username)
    if user:
        return render_template('perfil.html', id=user.id, username=user.username, email=user.email, shop_name=user.shop_name, bairro=user.bairro, tipo=user.tipo)
    return jsonify({"error": "Profile not found"}), 404

@app.route("/create_user", methods=['POST'])
def create_user():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    bairro = request.form.get("bairro")
    tipo = request.form.get("tipo")

    atuacao = request.form.get("atuacao_loja") if tipo == "merchant" else request.form.get("atuacao_org")
    nome_local = request.form.get("shop_name") if tipo in ["merchant", "charity"] else None

    if not all([username, email, password, bairro]):
        return jsonify({"error": "Missing username, email, password, or bairro"}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user_model = {'user': User, 'merchant': Merchant, 'charity': Charity}.get(tipo, User)
    user = user_model(username=username, email=email, password=hashed_password, bairro=bairro, tipo=tipo, shop_name=nome_local, atuacao=atuacao)

    db.session.add(user)
    db.session.commit()
    return jsonify({"success": True, "message": "Conta criada com Sucesso"}), 201

@app.route('/edit_user/<int:id>', methods=['POST'])
@login_required
def edit_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user != current_user:
        return jsonify({"error": "You are not authorized to edit this user"}), 403

    user.username = request.form.get("username", user.username)
    user.email = request.form.get("email", user.email)
    user.bairro = request.form.get("bairro", user.bairro)

    db.session.commit()
    return jsonify({"success": True, "message": "User updated successfully"}), 200

@app.route('/charity')
def charity():
    charity = Charity.query.filter_by(bairro=current_user.bairro).all()
    return render_template('instituicoessociais.html', instituicoes=charity, username=current_user.username)

if __name__ == "__main__":
    app.run(debug=True, port=8000)


# Explicação das Implementações Funcionais:

# Função Lambda: Utilizada na linha is_visible = lambda checkbox: checkbox is not None para verificar se um produto deve ser visível.

# List Comprehension: Utilizada em view_all_products e get_all_users para criar listas a partir de filtros e consultas de banco de dados.

# Closure: A função create_user_search_function cria e retorna uma função search_user com um modelo específico. Isso permite criar funções de busca para diferentes modelos sem reescrever o código.

# Função de Alta Ordem: A função authenticate_user recebe uma lista de modelos e uma função interna para verificar a senha, demonstrando o conceito de função de alta ordem.