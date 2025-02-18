from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(10), nullable=False)  # Unique kısıtlaması kaldırıldı
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    birthdate = db.Column(db.Date)
    profile_image = db.Column(db.String(200), default='images/pp.png')
    theme_preference = db.Column(db.String(10), default='light')  # Tema tercihi
    font_size = db.Column(db.String(10), default='medium')  # Yeni eklenen alan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False)  # 'dosya_ekleme', 'masraf_ekleme', 'belge_yukleme', vs.
    description = db.Column(db.String(250), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    related_case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'), nullable=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    tc = db.Column(db.String(11), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    installments = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    payments = db.relationship('Payment', backref='client', lazy=True)
    status = db.Column(db.String(10), nullable=False, default='Ödenmedi')
    description = db.Column(db.Text, nullable=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)  # Belge türü
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'), nullable=False)
    expense_type = db.Column(db.String(100), nullable=False)  # Masraf türü
    amount = db.Column(db.Float, nullable=False)  # Masraf miktarı
    date = db.Column(db.Date, nullable=False)  # Masraf tarihi
    is_paid = db.Column(db.Boolean, default=False)  # Ödeme durumu
    description = db.Column(db.Text)  # Açıklama

class CaseFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_type = db.Column(db.String(50), nullable=False)
    courthouse = db.Column(db.String(100), nullable=False)  # Adliye
    department = db.Column(db.String(100), nullable=False)  # Birim
    year = db.Column(db.Integer, nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    client_name = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(20))
    status = db.Column(db.String(50), default='Aktif')
    open_date = db.Column(db.Date)
    next_hearing = db.Column(db.Date)
    hearing_time = db.Column(db.String(5))  # HH:MM formatında
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expenses = db.relationship('Expense', backref='case_file', lazy=True)
    documents = db.relationship('Document', backref='case_file', lazy=True)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'))
    assigned_to = db.Column(db.String(100))  # Atanan kişi
    deadline_date = db.Column(db.Date)  # Son gün tarihi
    is_completed = db.Column(db.Boolean, default=False)  # Tamamlanma durumu
