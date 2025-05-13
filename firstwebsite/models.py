from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import json

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
    permissions = db.Column(db.JSON, default={})

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission):
        """Kullanıcının belirli bir yetkiye sahip olup olmadığını kontrol eder"""
        if self.is_admin:  # Admin her şeyi yapabilir
            return True
            
        # Eğer yetkiler hiç tanımlanmamışsa
        if not self.permissions:
            return False
            
        # İstenen yetkiyi doğrudan kontrol et
        if permission in self.permissions and self.permissions[permission]:
            return True
        
        # Özel durumlar için kontrol
        # Eğer takvim görüntüleme yetkisi varsa ve etkinlik_görüntüleme istenmişse izin ver
        if permission == 'etkinlik_goruntule' and 'takvim_goruntule' in self.permissions and self.permissions['takvim_goruntule']:
            return True
            
        return False

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
    registration_date = db.Column(db.Date, nullable=True)  # Borç kayıt tarihi
    due_date = db.Column(db.Date, nullable=True)  # Son ödeme tarihi
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
    pdf_version = db.Column(db.String(255), nullable=True)  # PDF dönüşümü varsa dosya yolu

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
    hearing_type = db.Column(db.String(20), default='durusma')  # durusma veya e-durusma
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expenses = db.relationship('Expense', backref='case_file', lazy=True)
    documents = db.relationship('Document', backref='case_file', lazy=True)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    # Duruşma bilgileri için ek alanlar
    file_type = db.Column(db.String(50))  # Dosya türü (Hukuk, Ceza, İcra)
    courthouse = db.Column(db.String(100))  # Adliye 
    department = db.Column(db.String(100))  # Mahkeme/Birim

class WorkerInterview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Madde 1: Kişisel Bilgiler
    fullName = db.Column(db.String(100), nullable=False)
    tcNo = db.Column(db.String(11), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    
    # Madde 2: İşe Giriş Bilgileri
    startDate = db.Column(db.Date, nullable=False)
    insuranceDate = db.Column(db.Date, nullable=False)
    
    # Madde 3: İşten Ayrılma Bilgileri
    endDate = db.Column(db.Date, nullable=False)
    endReason = db.Column(db.Text, nullable=False)
    
    # Madde 4: İşyeri Bilgileri
    companyName = db.Column(db.String(100), nullable=False)
    businessType = db.Column(db.String(100), nullable=False)
    companyAddress = db.Column(db.Text, nullable=False)
    
    # Madde 5: Görev Bilgileri
    position = db.Column(db.String(100), nullable=False)
    
    # Madde 6: Çalışma Düzeni
    workHours = db.Column(db.String(100), nullable=False)
    overtime = db.Column(db.Text)
    
    # Madde 7: Ücret ve Yardımlar
    salary = db.Column(db.Float, nullable=False)
    transportation = db.Column(db.Float)
    food = db.Column(db.Float)
    benefits = db.Column(db.Text)
    
    # Madde 8: Tatil Bilgileri
    weeklyHoliday = db.Column(db.String(50), nullable=False)
    holidays = db.Column(db.Text)
    
    # Madde 9: İzin ve Alacak Bilgileri
    annualLeave = db.Column(db.Text)
    unpaidSalary = db.Column(db.Text)
    
    # Madde 10: Tanıklar
    witness1 = db.Column(db.String(100))
    witness2 = db.Column(db.String(100))
    witness3 = db.Column(db.String(100))
    witness4 = db.Column(db.String(100))
    
    # Ek Bilgiler
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'fullName': self.fullName,
            'tcNo': self.tcNo,
            'phone': self.phone,
            'address': self.address,
            'startDate': self.startDate.strftime('%Y-%m-%d'),
            'insuranceDate': self.insuranceDate.strftime('%Y-%m-%d'),
            'endDate': self.endDate.strftime('%Y-%m-%d'),
            'endReason': self.endReason,
            'companyName': self.companyName,
            'businessType': self.businessType,
            'companyAddress': self.companyAddress,
            'position': self.position,
            'workHours': self.workHours,
            'overtime': self.overtime,
            'salary': self.salary,
            'transportation': self.transportation,
            'food': self.food,
            'benefits': self.benefits,
            'weeklyHoliday': self.weeklyHoliday,
            'holidays': self.holidays,
            'annualLeave': self.annualLeave,
            'unpaidSalary': self.unpaidSalary,
            'witness1': self.witness1,
            'witness2': self.witness2,
            'witness3': self.witness3,
            'witness4': self.witness4,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id
        }

class IsciGorusmeTutanagi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # İşçi Bilgileri
    name = db.Column(db.String(100))
    tcNo = db.Column(db.String(11))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    
    # İş Bilgileri
    startDate = db.Column(db.String(10))  # GG.AA.YYYY formatında
    endDate = db.Column(db.String(10))    # GG.AA.YYYY formatında
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    
    # Sigorta Bilgileri
    insuranceStatus = db.Column(db.String(50))
    insuranceDate = db.Column(db.String(10))  # GG.AA.YYYY formatında
    insuranceNo = db.Column(db.String(20))
    salary = db.Column(db.String(50))
    
    # Çalışma Koşulları
    workingHours = db.Column(db.String(100))
    overtime = db.Column(db.String(100))
    weeklyHoliday = db.Column(db.String(50))
    annualLeave = db.Column(db.String(100))
    
    # İşten Ayrılma Nedeni
    terminationReason = db.Column(db.Text)
    terminationType = db.Column(db.String(50))
    noticeCompliance = db.Column(db.String(50))
    
    # Alacak Bilgileri
    severancePay = db.Column(db.String(50))
    noticePay = db.Column(db.String(50))
    unpaidWages = db.Column(db.String(50))
    overtimePay = db.Column(db.String(50))
    annualLeavePay = db.Column(db.String(50))
    ubgtPay = db.Column(db.String(50))
    
    # Alacak Bilgileri Var/Yok Seçenekleri
    severancePayOption = db.Column(db.String(10), default='no')
    noticePayOption = db.Column(db.String(10), default='no')
    unpaidWagesOption = db.Column(db.String(10), default='no')
    overtimePayOption = db.Column(db.String(10), default='no')
    annualLeavePayOption = db.Column(db.String(10), default='no')
    ubgtPayOption = db.Column(db.String(10), default='no')
    
    # Beyanlar
    workerStatement = db.Column(db.Text)
    employerStatement = db.Column(db.Text)
    
    # Tanık Var/Yok Seçeneği
    witnessOption = db.Column(db.String(10), default='no')
    
    # Tanıklar (dinamik sayıda tanık için JSON formatında saklayacağız)
    witnesses = db.Column(db.Text)  # JSON string olarak saklayacağız
    
    # Ek Bilgiler
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.strftime('%d.%m.%Y')
            else:
                result[column.name] = value
                
            # witnesses alanını JSON'dan dict'e çevir
            if column.name == 'witnesses' and value:
                try:
                    result[column.name] = json.loads(value)
                except:
                    pass
                    
        return result
