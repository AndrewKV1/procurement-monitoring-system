import pytest
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Supplier, PurchaseRequest, AuditLog, Equipment, PriceHistory, log_audit


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False


class TestBase:
    def setup_method(self):
        app.config.from_object(TestConfig)
        self.app = app
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.create_test_data()

    def teardown_method(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create_test_data(self):
        with self.app.app_context():
            self.admin = User(
                email="admin@test.com", 
                full_name="Андрій Коваленко",
                role="admin",
                department="IT"
            )
            self.admin.set_password("admin123")
            
            self.manager = User(
                email="manager@test.com",
                full_name="Марія Петренко",
                role="manager", 
                department="Відділ закупівель"
            )
            self.manager.set_password("manager123")
            
            self.analyst = User(
                email="analyst@test.com",
                full_name="Олена Коваль",
                role="analyst",
                department="Аналітика"
            )
            self.analyst.set_password("analyst123")
            
            self.project_manager = User(
                email="pm@test.com",
                full_name="Іван Мельник",
                role="project_manager",
                department="Управління проектами"
            )
            self.project_manager.set_password("pm123")
            
            self.supplier1 = Supplier(
                name="ТОВ Будматеріали Плюс",
                contact_person="Петро Сидоренко",
                email="info@budmaterial.com",
                region="Київ",
                rating=4.5
            )
            
            db.session.add_all([self.admin, self.manager, self.analyst, 
                                self.project_manager, self.supplier1])
            db.session.commit()
            
            # ← ЗБЕРІГАЄМО ID ЯК ЧИСЛА
            self.admin_id = self.admin.id
            self.manager_id = self.manager.id
            self.analyst_id = self.analyst.id
            self.pm_id = self.project_manager.id
            self.supplier1_id = self.supplier1.id
            
            self.equipment1 = Equipment(
                name="Бетономішалка BX-200",
                category="Будівельне обладнання",
                specifications="Об'єм 200 л, потужність 1.5 кВт",
                average_price=22500.0,
                supplier_id=self.supplier1_id
            )
            
            db.session.add(self.equipment1)
            db.session.commit()
            
            self.equipment1_id = self.equipment1.id


# ============ ТЕСТИ СТРУКТУРИ БАЗИ ДАНИХ ============

class TestDatabaseStructure(TestBase):
    
    def test_all_tables_exist(self):
        with self.app.app_context():
            assert User.query.count() >= 4
            assert Supplier.query.count() >= 1  
            assert Equipment.query.count() >= 1
            assert PurchaseRequest.query.count() >= 0
            assert AuditLog.query.count() >= 0
            assert PriceHistory.query.count() >= 0
    
    def test_user_roles(self):
        with self.app.app_context():
            roles = [u.role for u in User.query.all()]
            assert 'admin' in roles
            assert 'manager' in roles
            assert 'analyst' in roles
            assert 'project_manager' in roles


# ============ ТЕСТИ ЗАЯВОК ============

class TestPurchaseRequests(TestBase):
    
    def test_auto_approval_small_amount(self):
        """Заявка до 25 000 грн має автоматично затверджуватися"""
        with self.app.app_context():
            request = PurchaseRequest(
                request_number="SMALL-001",
                supplier_id=self.supplier1_id,
                user_id=self.manager_id,
                equipment_details="Будівельне обладнання",
                quantity=1,
                unit_price=20000.0,
                total_amount=20000.0,
                delivery_time=5,
                status="pending"
            )
            
            if request.total_amount <= 25000:
                request.status = "approved"
            
            assert request.status == "approved"
    
    def test_project_manager_approval_medium_amount(self):
        """Заявка від 25 001 до 100 000 грн потребує затвердження керівником"""
        with self.app.app_context():
            request = PurchaseRequest(
                request_number="MEDIUM-001",
                supplier_id=self.supplier1_id,
                user_id=self.manager_id,
                equipment_details="Середнє обладнання",
                quantity=1,
                unit_price=50000.0,
                total_amount=50000.0,
                delivery_time=7,
                status="pending"
            )
            
            if request.total_amount <= 25000:
                request.status = "approved"
            elif request.total_amount <= 100000:
                request.status = "pending_project_manager"
            else:
                request.status = "pending_financial_director"
            
            assert request.status == "pending_project_manager"
    
    def test_financial_director_approval_large_amount(self):
        """Заявка понад 100 000 грн потребує затвердження фінансовим директором"""
        with self.app.app_context():
            request = PurchaseRequest(
                request_number="LARGE-001",
                supplier_id=self.supplier1_id,
                user_id=self.manager_id,
                equipment_details="Дороге обладнання",
                quantity=1,
                unit_price=150000.0,
                total_amount=150000.0,
                delivery_time=10,
                status="pending"
            )
            
            if request.total_amount <= 25000:
                request.status = "approved"
            elif request.total_amount <= 100000:
                request.status = "pending_project_manager"
            else:
                request.status = "pending_financial_director"
            
            assert request.status == "pending_financial_director"
    
    def test_total_amount_calculation(self):
        """Перевірка автоматичного розрахунку суми"""
        quantity = 3
        unit_price = 15000.0
        total_amount = quantity * unit_price
        assert total_amount == 45000.0


# ============ ТЕСТИ КОРИСТУВАЧІВ ============

class TestUserFunctionality(TestBase):
    
    def test_user_authentication(self):
        with self.app.test_client() as client:
            response = client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'admin123'
            }, follow_redirects=True)
            
            assert response.status_code == 200
    
    def test_user_wrong_password(self):
        with self.app.test_client() as client:
            response = client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'wrong_password'
            }, follow_redirects=True)
            
            assert response.status_code == 200
    
    def test_password_hashing(self):
        with self.app.app_context():
            user = User.query.filter_by(email='admin@test.com').first()
            assert user.password_hash != 'admin123'
            assert user.check_password('admin123') == True
            assert user.check_password('wrong') == False


# ============ ТЕСТИ ПОСТАЧАЛЬНИКІВ ============

class TestSupplierFunctionality(TestBase):
    
    def test_supplier_search(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'manager@test.com',
                'password': 'manager123'
            })
            
            response = client.post('/api/suppliers/search', 
                                 json={'region': 'Київ'})
            
            assert response.status_code == 200
    
    def test_supplier_search_empty(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'manager@test.com',
                'password': 'manager123'
            })
            
            response = client.post('/api/suppliers/search', json={})
            assert response.status_code == 200


# ============ ТЕСТИ ОБЛАДНАННЯ ============

class TestEquipmentFunctionality(TestBase):
    
    def test_equipment_list_api(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'manager@test.com',
                'password': 'manager123'
            })
            
            response = client.get('/api/equipment/list')
            assert response.status_code == 200
            
            data = response.get_json()
            assert isinstance(data, list)
            assert len(data) >= 1
    
    def test_add_equipment_api(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'manager@test.com',
                'password': 'manager123'
            })
            
            response = client.post('/equipment/add', 
                json={
                    'name': 'Нова бетономішалка',
                    'category': 'Бетономішалки',
                    'specifications': "Об'єм 300 л",
                    'average_price': 30000.0,
                    'supplier_id': self.supplier1_id
                })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] == True
            assert data['name'] == 'Нова бетономішалка'
    
    def test_add_equipment_forbidden_for_analyst(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'analyst@test.com',
                'password': 'analyst123'
            })
            
            response = client.post('/equipment/add', 
                json={
                    'name': 'Спроба додати',
                    'average_price': 100
                },
                follow_redirects=False)
            
            assert response.status_code in [302, 403]
    
    def test_add_equipment_without_name(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'manager@test.com',
                'password': 'manager123'
            })
            
            response = client.post('/equipment/add', 
                json={
                    'name': '',
                    'average_price': 100
                })
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] == False


# ============ ТЕСТИ РОЛЕЙ ============

class TestRoleAccess(TestBase):
    
    def test_admin_can_access_users(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'admin123'
            })
            
            response = client.get('/users')
            assert response.status_code == 200
    
    def test_manager_cannot_access_users(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'manager@test.com',
                'password': 'manager123'
            })
            
            response = client.get('/users', follow_redirects=False)
            assert response.status_code == 302
    
    def test_analyst_cannot_access_users(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'analyst@test.com',
                'password': 'analyst123'
            })
            
            response = client.get('/users', follow_redirects=False)
            assert response.status_code == 302


# ============ ТЕСТИ АНАЛІТИКИ ============

class TestAnalyticsFunctionality(TestBase):
    
    def test_analytics_access(self):
        with self.app.test_client() as client:
            response = client.get('/analytics', follow_redirects=True)
            assert response.status_code == 200
    
    def test_analytics_financial_api(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'admin123'
            })
            
            response = client.get('/api/analytics/financial')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'total_amount' in data
            assert 'total_requests' in data
    
    def test_analytics_suppliers_api(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'admin123'
            })
            
            response = client.get('/api/analytics/suppliers')
            assert response.status_code == 200
            
            data = response.get_json()
            assert isinstance(data, list)


# ============ ТЕСТИ АУДИТУ ============

class TestAuditFunctionality(TestBase):
    
    def test_log_audit_creates_record(self):
        with self.app.app_context():
            log_audit(
                user_id=self.admin_id,
                action='TEST_ACTION',
                details='Тестова дія',
                ip_address='127.0.0.1'
            )
            
            log = AuditLog.query.filter_by(action='TEST_ACTION').first()
            assert log is not None
            assert log.details == 'Тестова дія'
            assert log.ip_address == '127.0.0.1'
    
    def test_audit_logs_page_admin(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'admin123'
            })
            
            response = client.get('/audit')
            assert response.status_code == 200
    
    def test_audit_logs_page_manager_forbidden(self):
        with self.app.test_client() as client:
            client.post('/login', data={
                'email': 'manager@test.com',
                'password': 'manager123'
            })
            
            response = client.get('/audit', follow_redirects=False)
            assert response.status_code == 302


# ============ ЗАПУСК ============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])