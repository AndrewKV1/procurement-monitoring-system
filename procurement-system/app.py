from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import hashlib
import os
import json
from sqlalchemy import and_, or_
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///procurement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

db = SQLAlchemy(app)


def require_role(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Будь ласка, увійдіть в систему', 'error')
                return redirect(url_for('login'))
            
            if session.get('user_role') not in roles:
                flash('Доступ заборонено. Недостатньо прав.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_project_manager(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') not in ['project_manager', 'admin']:
            flash('Доступ заборонено. Тільки для керівників проектів.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def require_authentication(f):
    """Декоратор для перевірки авторизації"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Будь ласка, увійдіть в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin_actions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            flash('Доступ заборонено. Тільки для адміністратора.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def require_read_only_analytics(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') not in ['admin', 'analyst']:
            flash('Доступ заборонено.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def require_manager_suppliers(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') not in ['manager']:
            flash('Доступ заборонено. Тільки для менеджерів.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# === МОДЕЛІ ДАНИХ ===
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(300))
    region = db.Column(db.String(50))
    rating = db.Column(db.Float, default=0.0)
    years_on_market = db.Column(db.Integer)
    has_certificates = db.Column(db.Boolean, default=False)
    specialization = db.Column(db.String(100))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    specifications = db.Column(db.Text)
    average_price = db.Column(db.Float)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    supplier = db.relationship('Supplier', backref=db.backref('equipment', lazy=True))


class PurchaseRequest(db.Model):
    __tablename__ = 'purchase_requests'
    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(20), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    equipment_details = db.Column(db.Text, nullable=False)
    
    # НОВЕ ПОЛЕ: посилання на довідник обладнання
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=True)
    equipment = db.relationship('Equipment', backref='purchase_requests')
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    delivery_time = db.Column(db.Integer)
    status = db.Column(db.String(20), default='draft')
    justification = db.Column(db.Text)
    approval_flow = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    supplier = db.relationship('Supplier', backref=db.backref('purchase_requests', lazy=True))
    user = db.relationship('User', backref=db.backref('purchase_requests', lazy=True))


class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    price = db.Column(db.Float, nullable=False)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)
    
    equipment = db.relationship('Equipment', backref=db.backref('price_history', lazy=True))
    supplier = db.relationship('Supplier', backref=db.backref('price_history', lazy=True))


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))


# === ФУНКЦІЇ ДЛЯ АУДИТУ ===
def log_audit(user_id, action, details, ip_address=None):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address
    )
    db.session.add(audit_log)
    db.session.commit()


# === ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ ===
def init_db():
    with app.app_context():
        db.create_all()
        
        if not User.query.first():
            # === КОРИСТУВАЧІ ВСІХ 5 РОЛЕЙ ===
            
            admin = User(
                email="admin@budsystem.com",
                full_name="Андрій Костецький",
                role="admin",
                department="IT"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            
            manager = User(
                email="petro@budsystem.com",
                full_name="Петро Сидоренко",
                role="manager",
                department="Закупівлі"
            )
            manager.set_password("manager123")
            db.session.add(manager)
            
            analyst = User(
                email="olena@budsystem.com",
                full_name="Олена Коваль",
                role="analyst",
                department="Аналітика"
            )
            analyst.set_password("analyst123")
            db.session.add(analyst)
            
            project_manager = User(
                email="ivan@budsystem.com",
                full_name="Іван Мельник",
                role="project_manager",
                department="Управління проектами"
            )
            project_manager.set_password("pm123")
            db.session.add(project_manager)
            
            financial_director = User(
                email="oksana@budsystem.com",
                full_name="Оксана Шевченко",
                role="financial_director",
                department="Фінанси"
            )
            financial_director.set_password("director123")
            db.session.add(financial_director)
            
            # === ПОСТАЧАЛЬНИКИ ===
            suppliers = [
                Supplier(
                    name="ТОВ Будматеріали",
                    contact_person="Петро Іваненко",
                    email="info@budmaterial.com",
                    phone="+380501234567",
                    address="Київ, вул. Центральна 123",
                    region="Київ",
                    rating=4.8,
                    years_on_market=5,
                    has_certificates=True,
                    specialization="Бетономішалки",
                    is_verified=True
                ),
                Supplier(
                    name="ПП Інструмент+",
                    contact_person="Марія Сидоренко",
                    email="sales@instrumentplus.com",
                    phone="+380631234568",
                    address="Львів, вул. Промислова 45",
                    region="Львів",
                    rating=4.2,
                    years_on_market=3,
                    has_certificates=True,
                    specialization="Електроінструменти",
                    is_verified=True
                ),
                Supplier(
                    name="ТОВ Будтехніка",
                    contact_person="Олександр Коваленко",
                    email="tech@budtehnika.com",
                    phone="+380671234569",
                    address="Харків, вул. Промислова 78",
                    region="Харків",
                    rating=4.5,
                    years_on_market=7,
                    has_certificates=True,
                    specialization="Віброобладнання",
                    is_verified=True
                )
            ]
            
            for supplier in suppliers:
                db.session.add(supplier)
            
            db.session.commit()
            
            # === ТЕСТОВЕ ОБЛАДНАННЯ ===
            equipment_list = [
                Equipment(
                    name="Пила електрична",
                    category="Електроінструменти",
                    specifications="Потужність 1.2 кВт, диск 190 мм",
                    average_price=3000.0,
                    supplier_id=2
                ),
                Equipment(
                    name="Бетономішалка BX-200",
                    category="Бетономішалки",
                    specifications="Об'єм 200 л, потужність 1.5 кВт",
                    average_price=25000.0,
                    supplier_id=1
                ),
                Equipment(
                    name="Дриль ударний",
                    category="Електроінструменти",
                    specifications="Потужність 800 Вт, патрон 13 мм",
                    average_price=1500.0,
                    supplier_id=2
                ),
                Equipment(
                    name="Віброплита",
                    category="Віброобладнання",
                    specifications="Вага 90 кг, глибина ущільнення 30 см",
                    average_price=18000.0,
                    supplier_id=3
                ),
                Equipment(
                    name="Кран баштовий",
                    category="Підйомні механізми",
                    specifications="Вантажопідйомність 5 т, стріла 20 м",
                    average_price=150000.0,
                    supplier_id=3
                ),
            ]
            
            for eq in equipment_list:
                db.session.add(eq)
            
            db.session.commit()
            print("OK Базу даних ініціалізовано з тестовими даними")
            print("Створено користувачів: admin, manager, analyst, project_manager, financial_director")


init_db()


# === MIDDLEWARE ===
@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'api_search_suppliers', 'api_debug_suppliers']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))


# === UC001: КЕРУВАННЯ КОРИСТУВАЧАМИ СИСТЕМИ ===
@app.route('/users')
@require_admin_actions
def users():
    users_list = User.query.all()
    return render_template('users.html', users=users_list)


@app.route('/users/add', methods=['GET', 'POST'])
@require_admin_actions
def add_user():
    if request.method == 'POST':
        email = request.form['email']
        full_name = request.form['full_name']
        role = request.form['role']
        department = request.form['department']
        password = request.form['password']
        
        if User.query.filter_by(email=email).first():
            flash('Користувач з таким email вже існує', 'error')
            return redirect(url_for('add_user'))
        
        if role == 'admin':
            flash('Призначення ролі "Адміністратор" потребує додаткового затвердження керівником IT-відділу', 'warning')
        
        new_user = User(
            email=email,
            full_name=full_name,
            role=role,
            department=department
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        log_audit(
            session['user_id'],
            'USER_CREATED',
            f'Створено користувача: {email} ({role})'
        )
        
        flash('Користувача успішно створено', 'success')
        return redirect(url_for('users'))
    
    return render_template('add_user.html')


@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@require_admin_actions
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.role = request.form['role']
        user.department = request.form.get('department', '')
        user.is_active = 'is_active' in request.form
        
        if user.role == 'admin':
            flash('Призначення ролі "Адміністратор" потребує додаткового затвердження', 'warning')
        
        db.session.commit()
        
        log_audit(
            session['user_id'],
            'USER_UPDATED',
            f'Оновлено користувача: {user.email}'
        )
        
        flash('Дані користувача оновлено', 'success')
        return redirect(url_for('users'))
    
    return render_template('edit_user.html', user=user)


@app.route('/users/delete/<int:user_id>')
@require_admin_actions
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    active_requests = PurchaseRequest.query.filter_by(user_id=user_id).count()
    if active_requests > 0:
        flash('Не можна видалити користувача з активними заявками', 'error')
        return redirect(url_for('users'))
    
    if user.role == 'admin' and user.is_active:
        admin_count = User.query.filter_by(role='admin', is_active=True).count()
        if admin_count <= 1:
            flash('Не можна видалити останнього активного адміністратора', 'error')
            return redirect(url_for('users'))
    
    log_audit(
        session['user_id'],
        'USER_DELETED',
        f'Видалено користувача: {user.email}'
    )
    
    db.session.delete(user)
    db.session.commit()
    
    flash('Користувача успішно видалено', 'success')
    return redirect(url_for('users'))


# === UC002: ПЕРЕГЛЯД АНАЛІТИКИ ЗАКУПІВЕЛЬ ===
@app.route('/analytics')
@require_read_only_analytics
def analytics():
    return render_template('analytics.html')


@app.route('/api/analytics/suppliers')
@require_read_only_analytics
def api_analytics_suppliers():
    try:
        suppliers = Supplier.query.all()
        supplier_stats = []
        
        for supplier in suppliers:
            approved_requests = PurchaseRequest.query.filter(
                PurchaseRequest.supplier_id == supplier.id,
                PurchaseRequest.status == 'approved'
            ).all()
            
            total_amount = sum(request.total_amount for request in approved_requests)
            purchase_count = len(approved_requests)
            
            supplier_stats.append({
                'id': supplier.id,
                'name': supplier.name,
                'rating': float(supplier.rating),
                'purchase_count': purchase_count,
                'total_amount': total_amount,
                'total_equipment_count': sum(request.quantity for request in approved_requests),
                'region': supplier.region or 'Не вказано',
                'average_order_value': total_amount / purchase_count if purchase_count > 0 else 0
            })
        
        return jsonify(supplier_stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/financial')
@require_read_only_analytics
def api_analytics_financial():
    try:
        total_requests = PurchaseRequest.query.filter_by(status='approved').count()
        approved_requests = PurchaseRequest.query.filter_by(status='approved').count()
        
        total_amount_result = db.session.query(db.func.sum(PurchaseRequest.total_amount)).filter(
            PurchaseRequest.status == 'approved'
        ).scalar()
        total_amount = float(total_amount_result or 0)
        
        avg_purchase = total_amount / approved_requests if approved_requests > 0 else 0
        
        active_suppliers_count = db.session.query(
            db.func.count(db.distinct(PurchaseRequest.supplier_id))
        ).filter(PurchaseRequest.status == 'approved').scalar() or 0
        
        monthly_stats = []
        for i in range(6):
            month_date = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)
            
            month_amount_result = db.session.query(
                db.func.sum(PurchaseRequest.total_amount)
            ).filter(
                PurchaseRequest.created_at.between(month_start, month_end),
                PurchaseRequest.status == 'approved'
            ).scalar()
            
            month_amount = float(month_amount_result or 0)
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'amount': month_amount
            })
        
        monthly_stats.reverse()
        
        result = {
            'total_requests': total_requests,
            'approved_requests': approved_requests,
            'total_amount': total_amount,
            'average_purchase': avg_purchase,
            'active_suppliers': active_suppliers_count,
            'monthly_stats': monthly_stats
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === UC003: ПОШУК ТА ПОРІВНЯННЯ ПОСТАЧАЛЬНИКІВ ===
@app.route('/suppliers')
@require_authentication
def suppliers():
    suppliers_list = Supplier.query.all()
    regions = db.session.query(Supplier.region).distinct().all()
    specializations = db.session.query(Supplier.specialization).distinct().all()
    
    return render_template('suppliers.html', 
                         suppliers=suppliers_list,
                         regions=[r[0] for r in regions],
                         specializations=[s[0] for s in specializations])


@app.route('/api/suppliers/search', methods=['POST', 'GET'])
@require_authentication
def api_search_suppliers():
    try:
        if request.method == 'GET':
            data = {}
        else:
            data = request.get_json() or {}
        
        query = Supplier.query
        
        if data.get('name'):
            query = query.filter(Supplier.name.ilike(f"%{data['name']}%"))
        
        if data.get('region'):
            query = query.filter(Supplier.region == data['region'])
        
        if data.get('specialization'):
            query = query.filter(Supplier.specialization == data['specialization'])
        
        if data.get('min_rating'):
            query = query.filter(Supplier.rating >= float(data['min_rating']))
        
        if data.get('min_experience'):
            query = query.filter(Supplier.years_on_market >= int(data['min_experience']))
        
        if data.get('has_certificates'):
            query = query.filter(Supplier.has_certificates == True)
        
        if data.get('is_verified'):
            query = query.filter(Supplier.is_verified == True)
        
        query = query.order_by(Supplier.rating.desc(), Supplier.years_on_market.desc())
        
        suppliers = query.all()
        
        result = []
        for supplier in suppliers:
            avg_delivery = db.session.query(db.func.avg(PurchaseRequest.delivery_time)).filter(
                PurchaseRequest.supplier_id == supplier.id,
                PurchaseRequest.status == 'approved'
            ).scalar() or 7.0
            
            result.append({
                'id': supplier.id,
                'name': supplier.name,
                'contact_person': supplier.contact_person or 'Не вказано',
                'email': supplier.email or 'Не вказано',
                'phone': supplier.phone or 'Не вказано',
                'region': supplier.region or 'Не вказано',
                'rating': float(supplier.rating),
                'years_on_market': supplier.years_on_market or 0,
                'has_certificates': bool(supplier.has_certificates),
                'specialization': supplier.specialization or 'Не вказано',
                'is_verified': bool(supplier.is_verified),
                'avg_delivery_time': round(float(avg_delivery), 1)
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suppliers/compare', methods=['POST'])
@require_authentication
def api_compare_suppliers():
    try:
        data = request.get_json()
        supplier_ids = data.get('supplier_ids', [])
        
        comparison_data = []
        for supplier_id in supplier_ids:
            supplier = Supplier.query.get(supplier_id)
            if supplier:
                purchase_stats = db.session.query(
                    db.func.count(PurchaseRequest.id),
                    db.func.avg(PurchaseRequest.total_amount),
                    db.func.avg(PurchaseRequest.delivery_time)
                ).filter(
                    PurchaseRequest.supplier_id == supplier_id,
                    PurchaseRequest.status == 'approved'
                ).first()
                
                comparison_data.append({
                    'id': supplier.id,
                    'name': supplier.name,
                    'rating': float(supplier.rating),
                    'years_on_market': supplier.years_on_market or 0,
                    'has_certificates': bool(supplier.has_certificates),
                    'region': supplier.region or 'Не вказано',
                    'purchase_count': purchase_stats[0] or 0,
                    'avg_purchase_amount': float(purchase_stats[1] or 0),
                    'avg_delivery_time': float(purchase_stats[2] or 0)
                })
        
        return jsonify(comparison_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === УПРАВЛІННЯ ОБЛАДНАННЯМ ===
@app.route('/equipment')
@require_role(['manager', 'analyst'])
def equipment_list():
    """Сторінка зі списком обладнання (тільки менеджер)"""
    equipment = Equipment.query.all()
    suppliers = Supplier.query.all()
    return render_template('equipment.html', equipment=equipment, suppliers=suppliers)


@app.route('/api/equipment/list')
@require_authentication
def api_equipment_list():
    """API для отримання списку обладнання (доступне всім авторизованим)"""
    try:
        equipment = Equipment.query.all()
        result = [{
            'id': e.id,
            'name': e.name,
            'category': e.category or '',
            'specifications': e.specifications or '',
            'average_price': float(e.average_price or 0),
            'supplier_id': e.supplier_id,
            'supplier_name': e.supplier.name if e.supplier else 'Не вказано'
        } for e in equipment]
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/equipment/add', methods=['POST'])
@require_role(['manager'])
def add_equipment():
    """Додавання нового обладнання (тільки менеджер)"""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Назва обов\'язкова'}), 400
        
        new_equipment = Equipment(
            name=data['name'].strip(),
            category=data.get('category', '').strip(),
            specifications=data.get('specifications', '').strip(),
            average_price=float(data.get('average_price', 0)),
            supplier_id=int(data['supplier_id']) if data.get('supplier_id') else None
        )
        
        db.session.add(new_equipment)
        db.session.commit()
        
        log_audit(
            session['user_id'],
            'EQUIPMENT_CREATED',
            f'Додано обладнання: {new_equipment.name} (ціна: {new_equipment.average_price} грн)'
        )
        
        return jsonify({
            'success': True,
            'id': new_equipment.id,
            'name': new_equipment.name,
            'category': new_equipment.category or '',
            'specifications': new_equipment.specifications or '',
            'average_price': float(new_equipment.average_price or 0),
            'supplier_id': new_equipment.supplier_id,
            'supplier_name': new_equipment.supplier.name if new_equipment.supplier else 'Не вказано'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/equipment/delete/<int:equipment_id>')
@require_role(['manager'])
def delete_equipment(equipment_id):
    """Видалення обладнання (тільки менеджер)"""
    equipment = Equipment.query.get_or_404(equipment_id)
    
    requests_count = PurchaseRequest.query.filter_by(equipment_id=equipment_id).count()
    if requests_count > 0:
        flash(f'Не можна видалити обладнання, яке використовується в {requests_count} заявках', 'error')
        return redirect(url_for('equipment_list'))
    
    log_audit(
        session['user_id'],
        'EQUIPMENT_DELETED',
        f'Видалено обладнання: {equipment.name}'
    )
    
    db.session.delete(equipment)
    db.session.commit()
    
    flash(f'Обладнання "{equipment.name}" успішно видалено', 'success')
    return redirect(url_for('equipment_list'))


# === UC004: ФОРМУВАННЯ ЗАЯВКИ НА ЗАКУПІВЛЮ ===
@app.route('/requests')
@require_authentication
def purchase_requests():
    user_role = session.get('user_role')
    
    if user_role == 'analyst':
        user_requests = PurchaseRequest.query.order_by(PurchaseRequest.created_at.desc()).all()
    elif user_role == 'project_manager':
        user_requests = PurchaseRequest.query.order_by(PurchaseRequest.created_at.desc()).all()
    elif user_role == 'financial_director':
        user_requests = PurchaseRequest.query.order_by(PurchaseRequest.created_at.desc()).all()
    elif user_role == 'manager':
        user_requests = PurchaseRequest.query.filter_by(
            user_id=session['user_id']
        ).order_by(PurchaseRequest.created_at.desc()).all()
    else:
        user_requests = []
    
    return render_template('requests.html', requests=user_requests)


@app.route('/requests/create', methods=['GET', 'POST'])
@require_role(['manager', 'project_manager'])
def create_request():
    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        equipment_id = request.form.get('equipment_id')
        equipment_details = request.form.get('equipment_details', '').strip()
        quantity = int(request.form['quantity'])
        unit_price = float(request.form['unit_price'])
        delivery_time = int(request.form['delivery_time'])
        justification = request.form.get('justification', '')
        
        # Обробка обладнання: або з dropdown, або вручну
        if equipment_id:
            equipment = Equipment.query.get(int(equipment_id))
            if equipment:
                equipment_details = equipment.name
                if equipment.specifications:
                    equipment_details += f" - {equipment.specifications}"
            else:
                flash('Обладнання не знайдено', 'error')
                return redirect(url_for('create_request'))
        
        if not equipment_details:
            flash('Оберіть обладнання зі списку або введіть опис вручну', 'error')
            return redirect(url_for('create_request'))
        
        total_amount = quantity * unit_price
        
        today = datetime.now().strftime('%Y%m%d')
        last_request = PurchaseRequest.query.filter(
            PurchaseRequest.request_number.like(f'{today}-%')
        ).order_by(PurchaseRequest.id.desc()).first()
        
        if last_request:
            last_number = int(last_request.request_number.split('-')[1])
            new_number = f"{today}-{last_number + 1:03d}"
        else:
            new_number = f"{today}-001"
        
        if total_amount <= 25000:
            status = 'approved'
        elif total_amount <= 100000:
            status = 'pending_project_manager'
        else:
            status = 'pending_financial_director'
        
        approval_flow = []
        if total_amount > 100000:
            approval_flow.append('financial_director')
        if total_amount > 25000:
            approval_flow.append('project_manager')
        
        new_request = PurchaseRequest(
            request_number=new_number,
            supplier_id=supplier_id,
            user_id=session['user_id'],
            equipment_details=equipment_details,
            equipment_id=int(equipment_id) if equipment_id else None,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            delivery_time=delivery_time,
            status=status,
            justification=justification,
            approval_flow=json.dumps(approval_flow)
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        log_audit(
            session['user_id'],
            'PURCHASE_REQUEST_CREATED',
            f'Створено заявку {new_number} на суму {total_amount} грн. Статус: {status}'
        )
        
        flash(f'Заявку {new_number} успішно створено! Статус: {status}', 'success')
        return redirect(url_for('purchase_requests'))
    
    suppliers_list = Supplier.query.all()
    return render_template('create_request.html', suppliers=suppliers_list)


@app.route('/requests/approve/<int:request_id>')
@require_authentication
def approve_request(request_id):
    purchase_request = PurchaseRequest.query.get_or_404(request_id)
    
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    can_approve = False
    
    if user_role == 'admin':
        if purchase_request.status not in ['approved', 'rejected']:
            can_approve = True
    
    elif user_role == 'manager':
        if (purchase_request.user_id == user_id and 
            purchase_request.status in ['pending', 'draft'] and 
            purchase_request.total_amount <= 25000):
            can_approve = True
    
    elif user_role == 'project_manager':
        if (purchase_request.status == 'pending_project_manager' and 
            purchase_request.total_amount <= 100000):
            can_approve = True
    
    elif user_role == 'financial_director':
        if purchase_request.status in ['pending', 'pending_project_manager', 'pending_financial_director', 'draft']:
            can_approve = True
    
    if not can_approve:
        flash('Недостатньо прав для затвердження цієї заявки', 'error')
        return redirect(url_for('purchase_requests'))
    
    if purchase_request.status == 'approved':
        flash('Ця заявка вже затверджена', 'info')
        return redirect(url_for('purchase_requests'))
    
    purchase_request.status = 'approved'
    purchase_request.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_audit(
        session['user_id'],
        'PURCHASE_REQUEST_APPROVED',
        f'Заявку {purchase_request.request_number} затверджено ({user_role})'
    )
    
    flash(f'Заявку {purchase_request.request_number} успішно затверджено!', 'success')
    return redirect(url_for('purchase_requests'))


@app.route('/requests/view/<int:request_id>')
@require_authentication
def view_request(request_id):
    purchase_request = PurchaseRequest.query.get_or_404(request_id)
    
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    can_view = False
    
    if user_role == 'admin':
        can_view = True
    elif user_role == 'analyst':
        can_view = True
    elif user_role == 'manager':
        if purchase_request.user_id == user_id:
            can_view = True
        else:
            if purchase_request.status == 'pending' and purchase_request.total_amount <= 25000:
                can_view = True
    elif user_role == 'project_manager':
        can_view = True
    elif user_role == 'financial_director':
        can_view = True
    else:
        can_view = False
    
    if not can_view:
        flash('Доступ заборонено. Недостатньо прав для перегляду цієї заявки.', 'error')
        return redirect(url_for('purchase_requests'))
    
    return render_template('view_request.html', request=purchase_request)


# === ДОДАТКОВІ ФУНКЦІЇ ===
@app.route('/requests/reject/<int:request_id>')
@require_authentication
def reject_request(request_id):
    purchase_request = PurchaseRequest.query.get_or_404(request_id)
    
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    can_reject = False
    
    if user_role == 'admin':
        if purchase_request.status not in ['approved', 'rejected']:
            can_reject = True
    
    elif user_role == 'manager':
        if (purchase_request.user_id == user_id and 
            purchase_request.status in ['pending', 'draft'] and 
            purchase_request.total_amount <= 25000):
            can_reject = True
    
    elif user_role == 'project_manager':
        if (purchase_request.status == 'pending_project_manager' and 
            purchase_request.total_amount <= 100000):
            can_reject = True
    
    elif user_role == 'financial_director':
        if purchase_request.status in ['pending', 'pending_project_manager', 'pending_financial_director', 'draft']:
            can_reject = True
    
    if not can_reject:
        flash('Недостатньо прав для відхилення цієї заявки', 'error')
        return redirect(url_for('purchase_requests'))
    
    if purchase_request.status in ['approved', 'rejected']:
        flash('Не можна відхилити вже затверджену або відхилену заявку', 'error')
        return redirect(url_for('purchase_requests'))
    
    purchase_request.status = 'rejected'
    purchase_request.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_audit(
        session['user_id'],
        'PURCHASE_REQUEST_REJECTED',
        f'Заявку {purchase_request.request_number} відхилено ({user_role})'
    )
    
    flash(f'Заявку {purchase_request.request_number} успішно відхилено!', 'success')
    return redirect(url_for('purchase_requests'))


@app.route('/requests/cancel/<int:request_id>')
@require_authentication
def cancel_request(request_id):
    purchase_request = PurchaseRequest.query.get_or_404(request_id)
    
    if purchase_request.user_id != session['user_id'] and session.get('user_role') != 'admin':
        flash('Доступ заборонено', 'error')
        return redirect(url_for('purchase_requests'))
    
    if purchase_request.status in ['approved', 'rejected']:
        flash('Не можна скасувати заявку, яка вже затверджена або відхилена', 'error')
        return redirect(url_for('purchase_requests'))
    
    purchase_request.status = 'cancelled'
    purchase_request.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_audit(
        session['user_id'],
        'PURCHASE_REQUEST_CANCELLED',
        f'Заявку {purchase_request.request_number} скасовано'
    )
    
    flash(f'Заявку {purchase_request.request_number} успішно скасовано!', 'success')
    return redirect(url_for('purchase_requests'))


@app.route('/requests/delete/<int:request_id>')
@require_authentication
def delete_request(request_id):
    purchase_request = PurchaseRequest.query.get_or_404(request_id)
    
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    can_delete = False
    
    if user_role == 'manager':
        if (purchase_request.user_id == user_id and 
            purchase_request.status in ['pending', 'rejected']):
            can_delete = True
    
    elif user_role == 'admin':
        if purchase_request.status in ['pending', 'rejected']:
            can_delete = True
    
    if not can_delete:
        flash('Недостатньо прав для видалення цієї заявки', 'error')
        return redirect(url_for('purchase_requests'))
    
    if purchase_request.status in ['approved', 'pending_project_manager', 'pending_financial_director', 'cancelled']:
        flash('Не можна видалити заявку, яка очікує затвердження або вже затверджена', 'error')
        return redirect(url_for('purchase_requests'))
    
    request_info = f"№{purchase_request.request_number}, постачальник: {purchase_request.supplier.name}, сума: {purchase_request.total_amount} грн"
    
    db.session.delete(purchase_request)
    db.session.commit()
    
    log_audit(
        session['user_id'],
        'PURCHASE_REQUEST_DELETED',
        f'Видалено заявку: {request_info}'
    )
    
    flash(f'Заявку {purchase_request.request_number} успішно видалено!', 'success')
    return redirect(url_for('purchase_requests'))


@app.route('/admin/approve_all')
@require_role(['admin'])
def approve_all_requests():
    pending_requests = PurchaseRequest.query.filter_by(status='pending').all()
    
    approved_count = 0
    for request in pending_requests:
        request.status = 'approved'
        request.updated_at = datetime.utcnow()
        approved_count += 1
        
        log_audit(
            session['user_id'],
            'PURCHASE_REQUEST_APPROVED',
            f'Заявку {request.request_number} затверджено (масове затвердження)'
        )
    
    db.session.commit()
    
    if approved_count > 0:
        flash(f'Успішно затверджено {approved_count} заявок', 'success')
    else:
        flash('Немає заявок для затвердження', 'info')
    
    return redirect(url_for('purchase_requests'))


# === ОСНОВНІ МАРШРУТИ ===
@app.route('/')
@require_authentication
def dashboard():
    user = User.query.get(session['user_id'])
    
    stats = {
        'total_users': User.query.count(),
        'total_suppliers': Supplier.query.count(),
        'active_requests': PurchaseRequest.query.filter(
            PurchaseRequest.status.in_(['pending', 'pending_project_manager', 'pending_financial_director', 'draft'])
        ).count(),
        'total_requests': PurchaseRequest.query.count(),
        'approved_requests': PurchaseRequest.query.filter_by(status='approved').count()
    }
    
    recent_requests = PurchaseRequest.query.order_by(
        PurchaseRequest.created_at.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                         user=user, 
                         stats=stats, 
                         recent_requests=recent_requests)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.full_name
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_audit(
                user.id,
                'USER_LOGIN',
                'Успішний вхід в систему',
                request.remote_addr
            )
            
            flash('Успішний вхід в систему!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Невірний email або пароль', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_audit(
            session['user_id'],
            'USER_LOGOUT',
            'Вихід з системи',
            request.remote_addr
        )
        session.clear()
    flash('Ви вийшли з системи', 'info')
    return redirect(url_for('login'))


@app.route('/audit')
@require_admin_actions
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    
    unique_users = len(set(log.user_id for log in logs if log.user_id))
    action_count = len(set(log.action for log in logs))
    
    today = datetime.now().date()
    today_count = AuditLog.query.filter(
        db.func.date(AuditLog.timestamp) == today
    ).count()
    
    return render_template('audit.html', 
                         logs=logs,
                         unique_users=unique_users,
                         action_count=action_count,
                         today_count=today_count)


# === ДОДАТКОВІ API ЕНДПОІНТИ ===
@app.route('/api/users/count')
@require_role(['admin'])
def api_users_count():
    count = User.query.count()
    return jsonify({'count': count})


@app.route('/api/suppliers/count')
@require_authentication
def api_suppliers_count():
    count = Supplier.query.count()
    return jsonify({'count': count})


@app.route('/api/requests/stats')
@require_authentication
def api_requests_stats():
    total = PurchaseRequest.query.count()
    approved = PurchaseRequest.query.filter_by(status='approved').count()
    pending = PurchaseRequest.query.filter_by(status='pending').count()
    
    return jsonify({
        'total': total,
        'approved': approved,
        'pending': pending
    })


# === ЕКСПОРТ ЗВІТІВ ===
@app.route('/api/analytics/export', methods=['POST'])
@require_read_only_analytics
def api_export_report():
    try:
        data = request.get_json()
        report_type = data.get('report_type', 'financial')
        period = int(data.get('period', 30))
        
        start_date = datetime.now() - timedelta(days=period)
        
        if report_type == 'financial':
            report_content = generate_financial_report(start_date)
        elif report_type == 'suppliers':
            report_content = generate_suppliers_report(start_date)
        elif report_type == 'trends':
            report_content = generate_trends_report(start_date)
        else:
            report_content = generate_financial_report(start_date)
        
        log_audit(
            session['user_id'],
            'REPORT_EXPORTED',
            f'Експортовано звіт {report_type} за період {period} днів'
        )
        
        return jsonify({
            'success': True,
            'content': report_content,
            'filename': f"звіт_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_financial_report(start_date):
    approved_requests = PurchaseRequest.query.filter(
        PurchaseRequest.created_at >= start_date,
        PurchaseRequest.status == 'approved'
    ).all()
    
    total_amount = sum(r.total_amount for r in approved_requests)
    
    report = f"""
ФІНАНСОВИЙ ЗВІТ ПО ЗАКУПІВЛЯХ
============================
Період: з {start_date.strftime('%d.%m.%Y')} по {datetime.now().strftime('%d.%m.%Y')}
Дата формування: {datetime.now().strftime('%d.%m.%Y %H:%M')}

ЗАГАЛЬНА СТАТИСТИКА:
-------------------
• Всього затверджених заявок: {len(approved_requests)}
• Загальна сума закупівель: {total_amount:,.2f} грн
• Середня вартість заявки: {total_amount/len(approved_requests) if approved_requests else 0:,.2f} грн

ДЕТАЛЬНИЙ ОГЛЯД ЗАЯВОК:
----------------------
"""
    for req in approved_requests:
        report += f"• {req.request_number}: {req.quantity} шт. × {req.unit_price:,.2f} грн = {req.total_amount:,.2f} грн\n"
    
    return report


def generate_suppliers_report(start_date):
    suppliers = Supplier.query.all()
    report = f"""
ЗВІТ ПО ЕФЕКТИВНОСТІ ПОСТАЧАЛЬНИКІВ
==================================
Період: з {start_date.strftime('%d.%m.%Y')} по {datetime.now().strftime('%d.%m.%Y')}

"""
    for s in suppliers:
        report += f"• {s.name} ({s.region}) - рейтинг: {s.rating}\n"
    return report


def generate_trends_report(start_date):
    return f"""
ЗВІТ ПО ТЕНДЕНЦІЯХ ЦІН
=====================
Період: з {start_date.strftime('%d.%m.%Y')} по {datetime.now().strftime('%d.%m.%Y')}

Рекомендації:
• Аналізувати постачальників з рейтингом вище 4.2
• Порівнювати ціни мінімум 3 постачальників
"""


# === ЕКСПОРТ ЖУРНАЛУ АУДИТУ ===
@app.route('/audit/export/csv')
@require_admin_actions
def export_audit_csv():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    
    csv_content = "Дата та час;Користувач;Email;Роль;Дія;Деталі;IP-адреса\n"
    
    for log in logs:
        user_name = log.user.full_name if log.user else "Невідомий користувач"
        user_email = log.user.email if log.user else "N/A"
        user_role = log.user.role if log.user else "N/A"
        details = (log.details or "").replace('"', '""')
        
        csv_content += f"{log.timestamp.strftime('%d.%m.%Y %H:%M:%S')};"
        csv_content += f"{user_name};"
        csv_content += f"{user_email};"
        csv_content += f"{user_role};"
        csv_content += f"{log.action};"
        csv_content += f"\"{details}\";"
        csv_content += f"{log.ip_address or 'N/A'}\n"
    
    from flask import Response
    response = Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment;filename=audit_log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        }
    )
    return response


@app.route('/audit/export/json')
@require_admin_actions
def export_audit_json():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    
    audit_data = []
    for log in logs:
        if log.user:
            user_data = {
                'id': log.user.id,
                'full_name': log.user.full_name,
                'email': log.user.email,
                'role': log.user.role,
                'department': log.user.department or "N/A"
            }
        else:
            user_data = {
                'id': None,
                'full_name': "Невідомий користувач",
                'email': "N/A",
                'role': "N/A",
                'department': "N/A"
            }
        
        audit_data.append({
            'id': log.id,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user': user_data,
            'action': log.action,
            'details': log.details,
            'ip_address': log.ip_address
        })
    
    from flask import Response
    response = Response(
        json.dumps(audit_data, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment;filename=audit_log_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        }
    )
    return response


@app.route('/audit/export/txt')
@require_admin_actions
def export_audit_txt():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    
    txt_content = "ЖУРНАЛ АУДИТУ СИСТЕМИ МОНІТОРИНГУ ЗАКУПІВЕЛЬ\n"
    txt_content += "=" * 60 + "\n"
    txt_content += f"Дата експорту: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
    txt_content += f"Всього записів: {len(logs)}\n"
    txt_content += "=" * 60 + "\n\n"
    
    for i, log in enumerate(logs, 1):
        user_name = log.user.full_name if log.user else "Невідомий користувач"
        user_email = log.user.email if log.user else "N/A"
        
        txt_content += f"ЗАПИС #{i}\n"
        txt_content += f"Дата/час: {log.timestamp.strftime('%d.%m.%Y %H:%M:%S')}\n"
        txt_content += f"Користувач: {user_name} ({user_email})\n"
        txt_content += f"Дія: {log.action}\n"
        txt_content += f"Деталі: {log.details or 'Немає'}\n"
        txt_content += f"IP-адреса: {log.ip_address or 'N/A'}\n"
        txt_content += "-" * 40 + "\n\n"
    
    from flask import Response
    response = Response(
        txt_content,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment;filename=audit_log_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        }
    )
    return response


# === ДОДАТКОВІ ФУНКЦІЇ ДЛЯ ПЕРЕВІРКИ ДАНИХ ===
@app.route('/admin/check_data_integrity')
@require_admin_actions
def check_data_integrity():
    problematic_requests = []
    all_requests = PurchaseRequest.query.all()
    
    for request in all_requests:
        calculated_total = request.quantity * request.unit_price
        if abs(calculated_total - request.total_amount) > 0.01:
            problematic_requests.append({
                'request_number': request.request_number,
                'quantity': request.quantity,
                'unit_price': request.unit_price,
                'stored_total': request.total_amount,
                'calculated_total': calculated_total,
                'difference': abs(calculated_total - request.total_amount)
            })
    
    result = f"""
    <h2>Перевірка цілісності даних</h2>
    <p>Всього заявок: {len(all_requests)}</p>
    <p>Проблемних заявок: {len(problematic_requests)}</p>
    """
    
    if problematic_requests:
        result += "<h3>Проблемні заявки:</h3>"
        for problem in problematic_requests:
            result += f"""
            <div style="border: 1px solid red; padding: 10px; margin: 10px;">
                <strong>{problem['request_number']}</strong><br>
                Кількість: {problem['quantity']}<br>
                Ціна: {problem['unit_price']}<br>
                Різниця: {problem['difference']}
            </div>
            """
    else:
        result += "<h3>Всі дані коректні</h3>"
    
    return result


def update_request_statuses():
    with app.app_context():
        all_requests = PurchaseRequest.query.all()
        for request in all_requests:
            if request.status == 'pending' and request.total_amount <= 25000:
                request.status = 'approved'
        db.session.commit()


def fix_all_request_statuses():
    with app.app_context():
        all_requests = PurchaseRequest.query.all()
        updated_count = 0
        
        for request in all_requests:
            old_status = request.status
            
            if request.status == 'pending' and request.total_amount <= 25000:
                request.status = 'approved'
            elif request.status == 'pending' and request.total_amount > 25000:
                if request.total_amount <= 100000:
                    request.status = 'pending_project_manager'
                else:
                    request.status = 'pending_financial_director'
            
            if old_status != request.status:
                updated_count += 1
        
        db.session.commit()
        return updated_count


fix_all_request_statuses()


if __name__ == '__main__':
    print("=" * 60)
    print("ЗАПУСК СИСТЕМИ МОНІТОРИНГУ ЗАКУПІВЕЛЬ")
    print("=" * 60)
    print("Доступні облікові дані (тестові):")
    print("-" * 60)
    print(" Адміністратор:       admin@budsystem.com / admin123")
    print(" Менеджер:            petro@budsystem.com / manager123")
    print(" Аналітик:            olena@budsystem.com / analyst123")
    print(" Керівник проекту:    ivan@budsystem.com / pm123")
    print(" Фінансовий директор: oksana@budsystem.com / director123")
    print("-" * 60)
    print("Відкрийте: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)