from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
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
    phone = db.Column(db.String(15), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    birthdate = db.Column(db.Date)
    profile_image = db.Column(db.String(200), default='images/pp.png')
    theme_preference = db.Column(db.String(20), default='light')
    font_size = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    approval_date = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    permissions = db.Column(db.JSON, default={})

    # Password reset fields
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_reset_token(self):
        """Şifre sıfırlama tokeni oluştur"""
        import secrets
        token = secrets.token_urlsafe(32)
        self.reset_token = token
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # 1 saat geçerli
        return token

    def verify_reset_token(self, token):
        """Şifre sıfırlama tokenini doğrula"""
        if (self.reset_token == token and
            self.reset_token_expires):
            # Timezone-aware karşılaştırma için
            now = datetime.utcnow()
            expires = self.reset_token_expires
            # Eğer expires timezone-aware ise, now'ı da timezone-aware yap
            if expires.tzinfo is not None:
                from datetime import timezone
                now = now.replace(tzinfo=timezone.utc)
            if now < expires:
                return True
        return False

    def clear_reset_token(self):
        """Şifre sıfırlama tokenini temizle"""
        self.reset_token = None
        self.reset_token_expires = None

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
            
        # Bağımlı yetkiler için kontrol
        dependencies = self.get_permission_dependencies()
        if permission in dependencies:
            for dep in dependencies[permission]:
                if dep in self.permissions and self.permissions[dep]:
                    return True
            
        return False

    @staticmethod
    def get_permission_dependencies():
        """Yetkilerin birbirlerine olan bağımlılıkları"""
        return {
            'etkinlik_goruntule': ['takvim_goruntule'],
            'etkinlik_ekle': ['takvim_goruntule', 'etkinlik_goruntule'],
            'etkinlik_duzenle': ['takvim_goruntule', 'etkinlik_goruntule'],
            'etkinlik_sil': ['takvim_goruntule', 'etkinlik_goruntule'],
            'duyuru_duzenle': ['duyuru_goruntule'],
            'duyuru_sil': ['duyuru_goruntule'],
            'dosya_goruntule': ['dosya_sorgula'],
            'dosya_duzenle': ['dosya_sorgula'],
            'dosya_sil': ['dosya_sorgula'],
            'odeme_duzenle': ['odeme_goruntule'],
            'odeme_sil': ['odeme_goruntule'],
            'veritabani_yonetimi': ['panel_goruntule'],
            'ai_avukat': ['panel_goruntule'],
            'yargi_kararlari_arama': ['panel_goruntule'],
            'ornek_dilekceler': ['panel_goruntule'],
            'ornek_sozlesmeler': ['panel_goruntule'],
            'ucret_tarifeleri': ['panel_goruntule']
        }

    @staticmethod
    def get_default_permissions():
        """Rol bazlı varsayılan yetkileri döndürür"""
        return {
            'Yönetici Avukat': {
                'panel_goruntule': True,
                'ayarlar': True,
                'takvim_goruntule': True,
                'etkinlik_goruntule': True,
                'etkinlik_ekle': True,
                'etkinlik_duzenle': True,
                'etkinlik_sil': True,
                'duyuru_goruntule': True,
                'duyuru_ekle': True,
                'duyuru_duzenle': True,
                'duyuru_sil': True,
                'odeme_goruntule': True,
                'odeme_ekle': True,
                'odeme_duzenle': True,
                'odeme_sil': True,
                'dosya_sorgula': True,
                'dosya_ekle': True,
                'dosya_duzenle': True,
                'dosya_sil': True,
                'faiz_hesaplama': True,
                'harc_hesaplama': True,
                'isci_hesaplama': True,
                'vekalet_hesaplama': True,
                'ceza_infaz_hesaplama': True,
                'isci_gorusme_goruntule': True,
                'isci_gorusme_ekle': True,
                'isci_gorusme_duzenle': True,
                'isci_gorusme_sil': True,
                'veritabani_yonetimi': True,
                'ai_avukat': True,
                'yargi_kararlari_arama': True,
                'ornek_dilekceler': True,
                'ornek_sozlesmeler': True,
                'ucret_tarifeleri': True,
                'anasayfa_son_islemler': True
            },
            'Avukat': {
                'panel_goruntule': True,
                'ayarlar': True,
                'takvim_goruntule': True,
                'etkinlik_goruntule': True,
                'etkinlik_ekle': True,
                'etkinlik_duzenle': True,
                'etkinlik_sil': True,
                'duyuru_goruntule': True,
                'duyuru_ekle': True,
                'dosya_sorgula': True,
                'dosya_ekle': True,
                'dosya_duzenle': True,
                'dosya_sil': True,
                'odeme_goruntule': True,
                'odeme_ekle': True,
                'odeme_duzenle': True,
                'faiz_hesaplama': True,
                'harc_hesaplama': True,
                'isci_hesaplama': True,
                'vekalet_hesaplama': True,
                'ceza_infaz_hesaplama': True,
                'isci_gorusme_goruntule': True,
                'isci_gorusme_ekle': True,
                'isci_gorusme_duzenle': True,
                'ai_avukat': True,
                'yargi_kararlari_arama': True,
                'ornek_dilekceler': True,
                'ornek_sozlesmeler': True,
                'ucret_tarifeleri': True,
                'anasayfa_son_islemler': True
            },
            'Stajyer Avukat': {
                'panel_goruntule': True,
                'ayarlar': True,
                'takvim_goruntule': True,
                'etkinlik_goruntule': True,
                'duyuru_goruntule': True,
                'dosya_sorgula': True,
                'dosya_ekle': True,
                'odeme_goruntule': True,
                'faiz_hesaplama': True,
                'harc_hesaplama': True,
                'isci_hesaplama': True,
                'vekalet_hesaplama': True,
                'ceza_infaz_hesaplama': True,
                'isci_gorusme_goruntule': True,
                'isci_gorusme_ekle': True,
                'ai_avukat': True,
                'yargi_kararlari_arama': True,
                'ornek_dilekceler': True,
                'ornek_sozlesmeler': True,
                'ucret_tarifeleri': True,
                'anasayfa_son_islemler': True
            },
            'Sekreter': {
                'panel_goruntule': True,
                'ayarlar': True,
                'takvim_goruntule': True,
                'etkinlik_goruntule': True,
                'etkinlik_ekle': True,
                'duyuru_goruntule': True,
                'dosya_sorgula': True,
                'dosya_ekle': True,
                'odeme_goruntule': True,
                'odeme_ekle': True,
                'faiz_hesaplama': True,
                'harc_hesaplama': True,
                'isci_hesaplama': True,
                'vekalet_hesaplama': True,
                'ceza_infaz_hesaplama': True,
                'isci_gorusme_goruntule': True,
                'isci_gorusme_ekle': True,
                'ai_avukat': True,
                'yargi_kararlari_arama': True,
                'ornek_dilekceler': True,
                'ornek_sozlesmeler': True,
                'ucret_tarifeleri': True,
                'anasayfa_son_islemler': True
            },
            'Takip Elemanı': {
                'panel_goruntule': True,
                'ayarlar': True,
                'takvim_goruntule': True,
                'etkinlik_goruntule': True,
                'duyuru_goruntule': True,
                'dosya_sorgula': True,
                'odeme_goruntule': True,
                'faiz_hesaplama': True,
                'harc_hesaplama': True,
                'isci_hesaplama': True,
                'vekalet_hesaplama': True,
                'ceza_infaz_hesaplama': True,
                'ai_avukat': True,
                'yargi_kararlari_arama': True,
                'ornek_dilekceler': True,
                'ucret_tarifeleri': True,
                'anasayfa_son_islemler': False
            }
        }

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
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone(timedelta(hours=3))))
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
    payment_date = db.Column(db.Date, nullable=True)  # Ödeme tarihi (ödeme durumu ödendi ise)
    payments = db.relationship('Payment', backref='client', lazy=True)
    status = db.Column(db.String(10), nullable=False, default='Ödenmedi')
    description = db.Column(db.Text, nullable=True)
    payment_type = db.Column(db.String(50), nullable=True)  # Ödeme türü
    entity_type = db.Column(db.String(20), default='person')  # person/company
    payment_client_id = db.Column(db.Integer, db.ForeignKey('payment_client.id'), nullable=True)  # Kayıtlı müvekkil referansı

class PaymentClient(db.Model):
    """Kayıtlı Müvekkil - Ödemeler sayfasına özel"""
    __tablename__ = 'payment_client'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), nullable=False, default='person')  # person/company
    name = db.Column(db.String(200), nullable=False)  # Ad Soyad veya Kurum Adı
    surname = db.Column(db.String(100), nullable=True)  # Sadece kişiler için
    identity_number = db.Column(db.String(50), nullable=True)  # TC veya Vergi/Mersis/Ticaret Sicil
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def get_full_name(self):
        """Tam adı döndür"""
        if self.entity_type == 'person' and self.surname:
            return f"{self.name} {self.surname}"
        return self.name

    def __repr__(self):
        return f'<PaymentClient {self.get_full_name()}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PaymentDocument(db.Model):
    """Ödeme belgesi modeli - Dekont, Makbuz, Fiş, Fatura vb."""
    __tablename__ = 'payment_document'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # Dekont, Makbuz, Fiş, Fatura, Diğer
    document_name = db.Column(db.String(255), nullable=False)  # Kullanıcının verdiği isim
    filename = db.Column(db.String(255), nullable=False)  # Gerçek dosya adı
    filepath = db.Column(db.String(500), nullable=False)  # Dosya yolu
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # İlişkiler
    client = db.relationship('Client', backref=db.backref('documents', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('payment_documents', lazy='dynamic'))

    def __repr__(self):
        return f'<PaymentDocument {self.document_name}>'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)  # Belge türü
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pdf_version = db.Column(db.String(255), nullable=True)  # PDF dönüşümü varsa dosya yolu
    parent_document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)  # Ana belgenin ID'si (ekler için)

    # İlişkiler
    attachments = db.relationship('Document', backref=db.backref('parent', remote_side=[id]), lazy='dynamic', cascade='all, delete-orphan')

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
    city = db.Column(db.String(50))  # Şehir
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
    
    # Müvekkil detay bilgileri
    client_entity_type = db.Column(db.String(20), default='person')  # person/company
    client_identity_number = db.Column(db.String(20))  # TC/Vergi No
    client_capacity = db.Column(db.String(100))  # Sıfat
    client_address = db.Column(db.Text)  # Adres
    
    # Karşı taraf bilgileri
    opponent_entity_type = db.Column(db.String(20), default='person')  # person/company
    opponent_name = db.Column(db.String(150))
    opponent_identity_number = db.Column(db.String(20))  # TC/Vergi No
    opponent_capacity = db.Column(db.String(100))  # Sıfat
    opponent_phone = db.Column(db.String(20))
    opponent_address = db.Column(db.Text)
    opponent_lawyer = db.Column(db.String(150))
    opponent_lawyer_bar = db.Column(db.String(100))
    opponent_lawyer_bar_number = db.Column(db.String(20))
    opponent_lawyer_phone = db.Column(db.String(20))
    opponent_lawyer_address = db.Column(db.Text)
    
    # Çoklu kişi bilgileri (JSON formatında)
    additional_clients_json = db.Column(db.Text)  # Ek müvekkiller
    additional_opponents_json = db.Column(db.Text)  # Ek karşı taraflar
    additional_lawyers_json = db.Column(db.Text)  # Ek vekiller
    
    expenses = db.relationship('Expense', backref='case_file', lazy=True)
    documents = db.relationship('Document', backref='case_file', lazy=True)
    
    @property
    def additional_clients(self):
        """Ek müvekkilleri liste olarak döndür"""
        if self.additional_clients_json:
            try:
                return json.loads(self.additional_clients_json)
            except:
                return []
        return []
    
    @additional_clients.setter
    def additional_clients(self, value):
        """Ek müvekkilleri JSON olarak kaydet"""
        if value is None:
            self.additional_clients_json = None
        else:
            self.additional_clients_json = json.dumps(value)
    
    @property
    def additional_opponents(self):
        """Ek karşı tarafları liste olarak döndür"""
        if self.additional_opponents_json:
            try:
                return json.loads(self.additional_opponents_json)
            except:
                return []
        return []
    
    @additional_opponents.setter
    def additional_opponents(self, value):
        """Ek karşı tarafları JSON olarak kaydet"""
        if value is None:
            self.additional_opponents_json = None
        else:
            self.additional_opponents_json = json.dumps(value)
    
    @property
    def additional_lawyers(self):
        """Ek vekilleri liste olarak döndür"""
        if self.additional_lawyers_json:
            try:
                return json.loads(self.additional_lawyers_json)
            except:
                return []
        return []
    
    @additional_lawyers.setter
    def additional_lawyers(self, value):
        """Ek vekilleri JSON olarak kaydet"""
        if value is None:
            self.additional_lawyers_json = None
        else:
            self.additional_lawyers_json = json.dumps(value)

    def get_lawyers_by_party(self, party_type, party_index=0):
        """Belirli bir tarafın vekillerini getir
        Args:
            party_type: 'client' veya 'opponent'
            party_index: 0=ana taraf, 1+=ek taraflar
        Returns:
            List of Lawyer objects
        """
        return [
            assoc.lawyer for assoc in
            db.session.query(PartyLawyer).filter_by(
                party_type=party_type,
                party_index=party_index
            ).join(Lawyer).filter_by(case_id=self.id).all()
        ]

    def get_all_lawyers_grouped(self):
        """Tüm vekilleri taraflara göre gruplandırılmış şekilde getir
        Returns:
            {
                'client': {'main': [lawyers], 'additional': {0: [lawyers], 1: [lawyers]}},
                'opponent': {'main': [lawyers], 'additional': {0: [lawyers], 1: [lawyers]}}
            }
        """
        result = {
            'client': {'main': [], 'additional': {}},
            'opponent': {'main': [], 'additional': {}}
        }

        for lawyer in self.lawyers.all():
            for assoc in lawyer.party_associations:
                party_type = assoc.party_type
                party_index = assoc.party_index

                if party_index == 0:
                    result[party_type]['main'].append(lawyer)
                else:
                    if party_index not in result[party_type]['additional']:
                        result[party_type]['additional'][party_index] = []
                    result[party_type]['additional'][party_index].append(lawyer)

        return result

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
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
    # Günlük Kayıt bilgileri için ek alanlar
    muvekkil_isim = db.Column(db.String(200))  # Müvekkil İsim Soyisim
    muvekkil_telefon = db.Column(db.String(20))  # Telefon Numarası (isteğe bağlı)
    # Arabuluculuk Toplantısı bilgileri için ek alanlar
    basvuran_isim = db.Column(db.String(200))  # Başvuran Taraf İsim Soyisim
    basvuran_telefon = db.Column(db.String(20))  # Başvuran Telefon (isteğe bağlı)
    aleyhindeki_isim = db.Column(db.String(200))  # Aleyhindeki Taraf İsim Soyisim
    aleyhindeki_telefon = db.Column(db.String(20))  # Aleyhindeki Telefon (isteğe bağlı)
    arabulucu_isim = db.Column(db.String(200))  # Arabulucu İsim Soyisim
    arabulucu_telefon = db.Column(db.String(20))  # Arabulucu Telefon (isteğe bağlı)
    arabuluculuk_turu = db.Column(db.String(50))  # Arabuluculuk Türü (yuzyuze/telekonferans)
    toplanti_adresi = db.Column(db.String(500))  # Toplantı Adresi (yüzyüze toplantılar için, isteğe bağlı)

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
    registryNumber = db.Column(db.String(100))  # Mersis/Vergi/Ticaret Sicil No
    
    # Madde 5: Görev Bilgileri
    position = db.Column(db.String(100), nullable=False)
    
    # Madde 6: Çalışma Düzeni
    workHours = db.Column(db.String(100), nullable=False)
    overtime = db.Column(db.Text)
    
    # Madde 7: Ücret ve Yardımlar
    salary = db.Column(db.String(100), nullable=False)  # String olarak değiştirildi
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
    witness1Info = db.Column(db.Text)  # Tanık 1 bilgileri
    witness2 = db.Column(db.String(100))
    witness2Info = db.Column(db.Text)  # Tanık 2 bilgileri
    witness3 = db.Column(db.String(100))
    witness3Info = db.Column(db.Text)  # Tanık 3 bilgileri
    witness4 = db.Column(db.String(100))
    witness4Info = db.Column(db.Text)  # Tanık 4 bilgileri

    # Alacak Bilgileri Radio Button Seçimleri
    severancePayOption = db.Column(db.String(10), default='no')  # Kıdem Tazminatı
    noticePayOption = db.Column(db.String(10), default='no')     # İhbar Tazminatı
    unpaidWagesOption = db.Column(db.String(10), default='no')   # Ödenmemiş Ücretler
    overtimePayOption = db.Column(db.String(10), default='no')   # Fazla Mesai Ücreti
    annualLeavePayOption = db.Column(db.String(10), default='no') # Yıllık İzin Ücreti
    ubgtPayOption = db.Column(db.String(10), default='no')       # UBGT Ücreti
    witnessOption = db.Column(db.String(10), default='no')       # Tanık Var/Yok

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

    # Şirket Bilgileri
    companyAddress = db.Column(db.Text)  # Şirket Adresi-Telefonu
    
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
    
    # PDF Dosya Yolu
    pdf_path = db.Column(db.String(500))  # PDF dosyasının kaydedildiği yol
    
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

class DilekceKategori(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False, unique=True)
    dilekceler = db.relationship('OrnekDilekce', backref='kategori', lazy='dynamic')

    def __repr__(self):
        return f'<DilekceKategori {self.ad}>'

class OrnekDilekce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(255), nullable=False)
    dosya_yolu = db.Column(db.String(500), nullable=False) # Gerçek dosya sistemindeki adı
    yuklenme_tarihi = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    kategori_id = db.Column(db.Integer, db.ForeignKey('dilekce_kategori.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('yukledigi_ornek_dilekceler', lazy=True))

    def __repr__(self):
        return f'<OrnekDilekce {self.ad}>'

# Yeni eklenecek model
class OrnekSozlesme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sozlesme_adi = db.Column(db.String(255), nullable=False, unique=True) # Kullanıcının verdiği ad
    muvekkil_adi = db.Column(db.String(255), nullable=True) # Formdan alınacak
    sozlesme_tarihi = db.Column(db.Date, nullable=True) # Formdan alınacak
    icerik_json = db.Column(db.Text, nullable=False)  # Sözleşmenin pdfmake formatındaki JSON içeriği
    olusturulma_tarihi = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pdf_path = db.Column(db.String(500))  # PDF dosyasının kaydedildiği yol

    user = db.relationship('User', backref=db.backref('olusturdugu_ornek_sozlesmeler', lazy=True))

    def __repr__(self):
        return f'<OrnekSozlesme {self.sozlesme_adi}>'

class AISohbetGecmisi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    sohbet_verisi = db.Column(db.Text, nullable=False)  # JSON formatında sohbet mesajları
    olusturulma_tarihi = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    guncelleme_tarihi = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))), onupdate=lambda: datetime.now(timezone(timedelta(hours=3))))
    mesaj_sayisi = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    user = db.relationship('User', backref=db.backref('ai_sohbet_gecmisleri', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'baslik': self.baslik,
            'sohbet_verisi': json.loads(self.sohbet_verisi) if self.sohbet_verisi else [],
            'olusturulma_tarihi': self.olusturulma_tarihi.strftime('%Y-%m-%d %H:%M:%S'),
            'guncelleme_tarihi': self.guncelleme_tarihi.strftime('%Y-%m-%d %H:%M:%S'),
            'mesaj_sayisi': self.mesaj_sayisi,
            'user_id': self.user_id
        }
    
    def __repr__(self):
        return f'<AISohbetGecmisi {self.baslik}>'

class ContractTemplate(db.Model):
    """Avukatlık sözleşme taslağı modeli - Global template"""
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(100), default='Varsayılan Taslak')
    avukat_adi = db.Column(db.String(200))
    avukat_adres = db.Column(db.Text)
    banka_bilgisi = db.Column(db.String(200))
    iban_no = db.Column(db.String(50))
    yetkili_mahkeme = db.Column(db.String(200))
    kanun_no = db.Column(db.String(100))
    giris_metni = db.Column(db.Text)
    madde2 = db.Column(db.Text)
    madde3 = db.Column(db.Text)
    madde4 = db.Column(db.Text)
    madde5 = db.Column(db.Text)
    madde6 = db.Column(db.Text)
    madde7 = db.Column(db.Text)
    madde8 = db.Column(db.Text)
    madde9 = db.Column(db.Text)
    madde10 = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))), onupdate=lambda: datetime.now(timezone(timedelta(hours=3))))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<ContractTemplate {self.template_name}>'

class Lawyer(db.Model):
    """Vekil/Avukat bilgileri modeli"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    bar = db.Column(db.String(100))  # Baro
    bar_number = db.Column(db.String(20))  # Baro sicil numarası
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))
    case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'), nullable=False)

    # İlişki
    case = db.relationship('CaseFile', backref=db.backref('lawyers', lazy='dynamic', cascade='all, delete-orphan'))
    party_associations = db.relationship('PartyLawyer', back_populates='lawyer', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Lawyer {self.name}>'

class PartyLawyer(db.Model):
    """Taraf-Vekil ilişki tablosu (Many-to-Many)"""
    id = db.Column(db.Integer, primary_key=True)
    lawyer_id = db.Column(db.Integer, db.ForeignKey('lawyer.id'), nullable=False)
    party_type = db.Column(db.String(20), nullable=False)  # 'client' veya 'opponent'
    party_index = db.Column(db.Integer, nullable=False, default=0)  # 0=ana taraf, 1+=ek taraflar
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=3))))

    # İlişkiler
    lawyer = db.relationship('Lawyer', back_populates='party_associations')

    def __repr__(self):
        return f'<PartyLawyer lawyer_id={self.lawyer_id} party={self.party_type}:{self.party_index}>'