from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)  # Yeni eklenen alan
    last_name = db.Column(db.String(50), nullable=False)   # Yeni eklenen alan
    phone = db.Column(db.String(10), nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    birthdate = db.Column(db.Date)
    profile_image = db.Column(db.String(200), default='images/pp.png')
    theme_preference = db.Column(db.String(10), default='light')
    font_size = db.Column(db.String(10), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    approval_date = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    permissions = db.Column(db.JSON, default=dict)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission):
        if self.is_admin:  # Admin her şeyi yapabilir
            return True
            
        # Bazı yetkiler birbirine bağımlı
        permission_dependencies = {
            'duyuru_ekle': ['duyuru_goruntule'],
            'duyuru_duzenle': ['duyuru_goruntule'],
            'duyuru_sil': ['duyuru_goruntule'],
            'etkinlik_ekle': ['takvim_goruntule'],
            'etkinlik_duzenle': ['takvim_goruntule', 'etkinlik_goruntule'],
            'etkinlik_sil': ['takvim_goruntule', 'etkinlik_goruntule'],
            'odeme_ekle': ['odeme_goruntule'],
            'odeme_duzenle': ['odeme_goruntule'],
            'odeme_sil': ['odeme_goruntule'],
            'dosya_ekle': ['dosya_sorgula'],
            'dosya_duzenle': ['dosya_sorgula'],
            'dosya_sil': ['dosya_sorgula']
        }
        
        # İstenen yetkiyi veya bağımlı olduğu yetkileri kontrol et
        if permission in permission_dependencies:
            for required_permission in permission_dependencies[permission]:
                if not self.permissions.get(required_permission, False):
                    return False
                    
        return self.permissions.get(permission, False)

    def get_title(self):
        """Kullanıcının rolüne göre ünvanını döndürür"""
        if self.role == 'Yönetici Avukat' or self.role == 'Avukat':
            return 'Av.'
        elif self.role == 'Stajyer Avukat':
            return 'Stj. Av.'
        elif self.role == 'Sekreter':
            return 'Asst.'
        elif self.role == 'Ulaşım':
            return 'Ulşm.'
        elif self.role == 'Takip Elemanı':
            return 'Tkp El.'
        return ''

    def get_full_name(self):
        """Kullanıcının tam adını ünvanıyla birlikte döndürür"""
        title = self.get_title()
        if title:
            return f"{title} {self.first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<User {self.username}>'

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False)  # 'dosya_ekleme', 'duyuru_ekleme', 'etkinlik_ekleme', vs.
    description = db.Column(db.String(250), nullable=False)
    details = db.Column(db.JSON, nullable=True)  # Detaylı bilgileri JSON olarak saklayacağız
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    related_case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'), nullable=True)
    related_announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=True)
    related_event_id = db.Column(db.Integer, db.ForeignKey('calendar_event.id'), nullable=True)
    related_payment_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)

    # İlişkiler
    user = db.relationship('User', backref='activities')
    case = db.relationship('CaseFile', backref='activities')
    announcement = db.relationship('Announcement', backref='activities')
    event = db.relationship('CalendarEvent', backref='activities')
    payment = db.relationship('Client', backref='activities')

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
