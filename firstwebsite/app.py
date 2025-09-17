# .env dosyasını yükle
from dotenv import load_dotenv
load_dotenv()

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import Flask, render_template, request, url_for, flash, redirect, jsonify, session, send_from_directory, send_file, make_response, current_app, Response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta, date, time, timezone
import json
import os
from werkzeug.utils import secure_filename
import locale
import time as pytime

# Türkçe karakter desteği için encoding ayarı
try:
    locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
    except locale.Error:
        pass  # Sistem desteklemiyorsa varsayılan encoding kullan
import subprocess
import tempfile
from flask_mail import Mail, Message
from bs4 import BeautifulSoup
from email_utils import send_calendar_event_assignment_email, send_calendar_event_reminder_email
import requests
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect # CSRF Koruması için eklendi
from models import db, User, ActivityLog, Client, Payment, Document, Notification, Expense, CaseFile, Announcement, CalendarEvent, WorkerInterview, IsciGorusmeTutanagi, DilekceKategori, OrnekDilekce, OrnekSozlesme, ContractTemplate
import uuid
from PIL import Image
from functools import wraps
from yargi_integration import yargi_integration
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from html import escape  # HTML escape için bu modülü kullanacağız
from fpdf import FPDF
from xhtml2pdf import pisa
import glob # Add glob import
from sqlalchemy import func, desc
import shutil
import mammoth
import pdfkit
import logging # Logging için eklendi

# Logger yapılandırması
logger = logging.getLogger(__name__)
import traceback # traceback importu eklendi

# Flask-Admin imports
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action # Import action decorator
from markupsafe import Markup # For rendering HTML in actions

# Helper function to parse adliyelist.txt
def parse_adliye_list(filepath='../adliyelist.txt'): # Adjusted path
    cities_courthouses = {}
    try:
        # Ensure the path is correct relative to app.py location
        script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
        abs_file_path = os.path.join(script_dir, filepath)

        with open(abs_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Skip header and potential separator lines
            data_lines = [line.strip() for line in lines if line.strip() and not line.startswith('İl\t') and not line.startswith('___')]
            current_city = None
            for line in data_lines:
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    city, courthouses_str = parts
                    current_city = city.strip()
                    # Process courthouses string: split by comma or bullet, handle ACM markers etc.
                    # Keep the original names including ACM details
                    courthouses = [ch.strip() for ch in re.split(r'\s*,\s*|\s*•\s*', courthouses_str) if ch.strip()]
                    cities_courthouses[current_city] = courthouses
                # Removed the elif part as it's unlikely based on file structure
    except FileNotFoundError:
        print(f"Error: {abs_file_path} not found.")
        return {}, []
    except Exception as e:
        print(f"Error parsing {abs_file_path}: {e}")
        return {}, []

    # İstanbul'u şehir listesine manuel olarak ekle (zaten varsa sorun değil)
    if 'İstanbul' not in cities_courthouses:
        # İstanbul adliyeleri bu listede olmayacak, çünkü bunlar hardcoded olarak frontend'de tanımlanmış
        cities_courthouses['İstanbul'] = []  
        
    # Önce standart alfabetik sıralama
    cities = sorted(cities_courthouses.keys())
    
    # Özel sıralama için listeyi yeniden düzenle
    # İstanbul'u listeden çıkar ve en başa ekle
    if 'İstanbul' in cities:
        cities.remove('İstanbul')
        cities.insert(0, 'İstanbul')
    
    # İzmir'i Isparta'dan sonra getir
    if 'İzmir' in cities and 'Isparta' in cities:
        izmir_index = cities.index('İzmir')
        isparta_index = cities.index('Isparta')
        
        # İzmir'i çıkar
        cities.remove('İzmir')
        
        # Isparta'dan sonraya ekle
        cities.insert(isparta_index + 1, 'İzmir')
    
    # İstanbul'un listede olduğundan emin olalım
    if 'İstanbul' in cities:
        print("İstanbul şehir listesinde mevcut.")
    else:
        print("UYARI: İstanbul şehir listesine eklenemedi!")
        
    return cities_courthouses, cities

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Bu işlem için giriş yapmanız gerekmektedir.', 'error')
                return redirect(url_for('login', next=request.url))
            
            # Admin kontrolü ekle - Admin her şeyi yapabilir
            if current_user.is_admin:
                return f(*args, **kwargs)
                
            # Normal kullanıcılar için yetki kontrolü yap
            if not current_user.has_permission(permission):
                # Hangi yetkiye ihtiyaç duyulduğunu belirten bir hata mesajı
                permission_names = {
                    'dosya_sorgula': 'Dosya Sorgulama',
                    'dosya_ekle': 'Dosya Ekleme', 
                    'dosya_duzenle': 'Dosya Düzenleme',
                    'dosya_sil': 'Dosya Silme',
                    'takvim_goruntule': 'Takvim Görüntüleme',
                    'etkinlik_goruntule': 'Etkinlik Görüntüleme',
                    'etkinlik_ekle': 'Etkinlik Ekleme',
                    'etkinlik_duzenle': 'Etkinlik Düzenleme',
                    'etkinlik_sil': 'Etkinlik Silme',
                    'duyuru_goruntule': 'Duyuru Görüntüleme',
                    'duyuru_ekle': 'Duyuru Ekleme',
                    'duyuru_duzenle': 'Duyuru Düzenleme',
                    'duyuru_sil': 'Duyuru Silme',
                    'odeme_goruntule': 'Ödeme Görüntüleme',
                    'odeme_ekle': 'Ödeme Ekleme',
                    'odeme_duzenle': 'Ödeme Düzenleme',
                    'odeme_sil': 'Ödeme Silme',
                    'faiz_hesaplama': 'Faiz Hesaplama',
                    'harc_hesaplama': 'Harç Hesaplama',
                    'isci_hesaplama': 'İşçi Alacağı Hesaplama',
                    'vekalet_hesaplama': 'Vekalet Ücreti Hesaplama',
                    'ceza_infaz_hesaplama': 'Ceza İnfaz Hesaplama',
                    'rapor_goruntule': 'Rapor Görüntüleme',
                    'rapor_olustur': 'Rapor Oluşturma',
                    'musteri_goruntule': 'Müşteri Görüntüleme',
                    'musteri_ekle': 'Müşteri Ekleme',
                    'musteri_duzenle': 'Müşteri Düzenleme',
                    'musteri_sil': 'Müşteri Silme',
                    'panel_goruntule': 'Panel Görüntüleme',
                    'ayarlar': 'Ayarlar Erişimi',
                    'isci_gorusme_goruntule': 'İşçi Görüşme Görüntüleme',
                    'isci_gorusme_ekle': 'İşçi Görüşme Ekleme',
                    'isci_gorusme_duzenle': 'İşçi Görüşme Düzenleme',
                    'isci_gorusme_sil': 'İşçi Görüşme Silme',
                    'ornek_dilekceler': 'Örnek Dilekçeler',
                    'ornek_sozlesmeler': 'Örnek Sözleşmeler',
                    'ucret_tarifeleri': 'Ücret Tarifeleri',
                    'yargi_kararlari_arama': 'Yargı Kararları Arama',
                    'veritabani_yonetimi': 'Veritabanı Yönetimi'
                }
                
                permission_name = permission_names.get(permission, permission)
                flash(f'Bu işlem için "{permission_name}" yetkisine sahip olmanız gerekiyor.', 'error')
                
                # API isteklerinde JSON yanıtı döndür, sayfa isteklerinde anasayfaya yönlendir
                if request.is_json:
                    return jsonify({'success': False, 'error': f'Yetkiniz yok: {permission_name}'}), 403
                    
                return redirect(url_for('anasayfa'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

app = Flask(__name__, static_url_path='/static')
basedir = os.path.abspath(os.path.dirname(__file__))

# Load configuration from config.py if it exists, otherwise use defaults
try:
    from config import config
    config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
except ImportError:
    # Fallback to original configuration if config.py doesn't exist
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-this')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ORNEK_DILEKCE_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'ornek_dilekceler') # Yeni eklendi
# CSRF için WTF_CSRF_ENABLED=True (varsayılan olarak True'dur ama açıkça belirtmek iyi olabilir)
app.config['WTF_CSRF_ENABLED'] = True
# SECRET_KEY zaten yukarıda tanımlı, CSRF için de kullanılır.

# E-posta konfigürasyonu (.env dosyasından) - Gmail kullan
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_ASCII_ATTACHMENTS'] = False  # Türkçe karakter desteği için
app.config['MAIL_DEFAULT_CHARSET'] = 'utf-8'  # UTF-8 charset ayarla
app.config['MAIL_SUPPRESS_SEND'] = False
app.config['MAIL_DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

db.init_app(app)
migrate = Migrate(app, db)
mail = Mail(app)
csrf = CSRFProtect(app) # CSRF korumasını başlat

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Lütfen giriş yapın.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Flask-Admin Setup ---

# Secure Admin Index View
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        # Redirect non-admins or non-authenticated users to login page
        flash('Bu sayfaya erişmek için admin yetkilerine sahip olmanız gerekiyor.', 'error')
        return redirect(url_for('login'))
    
    @expose('/')
    def index(self):
        stats = {
            'total_users': User.query.count(),
            'pending_users': User.query.filter_by(is_approved=False).count(),
            'total_case_files': CaseFile.query.count(),
            'active_case_files': CaseFile.query.filter_by(status='Aktif').count(),
            'total_hearings': CalendarEvent.query.filter(CalendarEvent.event_type.in_(['durusma', 'e-durusma'])).count(),
            'total_payments': Payment.query.count(),
            'total_expenses': Expense.query.count(),
            'total_documents': Document.query.count(),
        }
        self._template_args['stats'] = stats
        self._template_args['admin_view'] = self
        return super(MyAdminIndexView, self).index()

    # Özel dizayn ekliyoruz
    @expose('/admin/back_to_app')
    def back_to_app(self):
        return redirect(url_for('anasayfa'))

# Secure Model View
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect(url_for('login', next=request.url))

# User Model View Customization
class UserView(SecureModelView):
    column_exclude_list = ['password_hash']
    form_excluded_columns = ['password_hash', 'activities']
    column_searchable_list = ['username', 'email', 'first_name', 'last_name']
    column_filters = ['role', 'is_admin', 'is_approved']
    column_list = ('username', 'email', 'first_name', 'last_name', 'role', 'is_admin', 'is_approved', 'created_at')
    column_labels = dict(username='Kullanıcı Adı', email='E-posta', first_name='Ad', last_name='Soyad', role='Rol', is_admin='Admin?', is_approved='Onaylı?', created_at='Kayıt Tarihi')
    
    can_create = True
    can_edit = True
    can_delete = True

    # Kullanıcı onaylama eylemi
    @action('approve', 'Seçili Kullanıcıları Onayla', 'Seçili kullanıcıları onaylamak istediğinizden emin misiniz?')
    def action_approve(self, ids):
        try:
            query = User.query.filter(User.id.in_(ids))
            count = 0
            for user in query.all():
                if not user.is_approved:
                    user.is_approved = True
                    user.approval_date = datetime.now()
                    user.approved_by = current_user.id
                    count += 1
            db.session.commit()
            flash(f'{count} kullanıcı başarıyla onaylandı.', 'success')
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(f'Kullanıcılar onaylanırken hata oluştu: {ex}', 'error')

    # Kullanıcı onay durumunu değiştirme eylemi
    @action('toggle_approval', 'Seçili Kullanıcıların Onay Durumunu Değiştir', 'Seçili kullanıcıların onay durumunu değiştirmek istediğinizden emin misiniz?')
    def action_toggle_approval(self, ids):
        try:
            query = User.query.filter(User.id.in_(ids))
            approved_count = 0
            disapproved_count = 0
            for user in query.all():
                if user.is_approved:
                    user.is_approved = False
                    user.approval_date = None
                    user.approved_by = None
                    disapproved_count += 1
                else:
                    user.is_approved = True
                    user.approval_date = datetime.now()
                    user.approved_by = current_user.id
                    approved_count += 1
            db.session.commit()
            flash(f'{approved_count} kullanıcı onaylandı, {disapproved_count} kullanıcının onayı kaldırıldı.', 'success')
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(f'Onay durumu değiştirilirken hata oluştu: {ex}', 'error')

# ActivityLog için özel view (ilişkili alanları göstermek için)
class ActivityLogView(SecureModelView):
    can_create = False
    can_edit = False
    can_delete = True # Logları silebilme (opsiyonel)
    column_list = ('timestamp', 'user', 'activity_type', 'description', 'related_case', 'related_event')
    column_labels = dict(timestamp='Zaman Damgası', user='Kullanıcı', activity_type='İşlem Türü', description='Açıklama', related_case='İlgili Dosya', related_event='İlgili Etkinlik')
    column_formatters = {
        'user': lambda v, c, m, p: m.user.get_full_name() if m.user else '-',
        'related_case': lambda v, c, m, p: f"{m.case.client_name} ({m.case.year}/{m.case.case_number})" if m.case else '-',
        'related_event': lambda v, c, m, p: m.event.title if m.event else '-'
    }
    column_filters = ('activity_type', 'user.username', 'timestamp')
    column_searchable_list = ('description', 'user.username', 'activity_type')
    column_default_sort = ('timestamp', True) # En son işlem en üstte

# Initialize Flask-Admin
admin = Admin(app, name='Veri Kontrol', template_mode='bootstrap4', index_view=MyAdminIndexView())

# Add Admin Views for your models
admin.add_view(UserView(User, db.session, name='Kullanıcılar'))
admin.add_view(SecureModelView(CaseFile, db.session, name='Dosyalar'))
admin.add_view(SecureModelView(CalendarEvent, db.session, name='Takvim Etkinlikleri'))
admin.add_view(SecureModelView(Document, db.session, name='Belgeler'))
admin.add_view(SecureModelView(Expense, db.session, name='Masraflar'))
admin.add_view(SecureModelView(Client, db.session, name='Müşteri Ödemeleri'))
admin.add_view(SecureModelView(Payment, db.session, name='Ödemeler (Taksit)'))
admin.add_view(SecureModelView(Announcement, db.session, name='Duyurular'))
admin.add_view(ActivityLogView(ActivityLog, db.session, name='İşlem Kayıtları')) # Özel view kullanıldı
admin.add_view(SecureModelView(WorkerInterview, db.session, name='İşçi Görüşme (Eski)'))
admin.add_view(SecureModelView(IsciGorusmeTutanagi, db.session, name='İşçi Görüşme Tutanağı'))
admin.add_view(SecureModelView(Notification, db.session, name='Bildirimler'))
admin.add_view(SecureModelView(DilekceKategori, db.session, name='Örnek Dilekçe Kategorileri')) # Örnek Dilekçe Kategori için Admin View
admin.add_view(SecureModelView(OrnekDilekce, db.session, name='Örnek Dilekçeler')) # Örnek Dilekçeler için Admin View
admin.add_view(SecureModelView(OrnekSozlesme, db.session, name='Örnek Sözleşmeler')) # Yeni eklendi

# --- End Flask-Admin Setup ---

# Auth routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('anasayfa'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        role = request.form.get('role')
        gender = request.form.get('gender')
        if gender:
            gender = gender.lower()
        else:
            gender = None
        phone = request.form.get('phone')
        
        # Telefon numarası validasyonu
        if phone:
            # Sadece rakam karakterleri bırak
            phone_digits = ''.join(filter(str.isdigit, phone))
            
            # 0 ile başlıyorsa kaldır
            if phone_digits.startswith('0'):
                phone_digits = phone_digits[1:]
            
            # Türk telefon numarası kontrolü (10 haneli, 5 ile başlamalı)
            if len(phone_digits) != 10 or not phone_digits.startswith('5'):
                flash('Telefon numarası 5 ile başlamalı ve 10 haneli olmalıdır. Örnek: 5123456789', 'error')
                return render_template('auth.html', show_register=True)
            
            phone = phone_digits
        else:
            flash('Telefon numarası zorunludur.', 'error')
            return render_template('auth.html', show_register=True)
        
        try:
            birth_day = int(request.form.get('birth_day'))
            birth_month = int(request.form.get('birth_month'))
            birth_year = int(request.form.get('birth_year'))
            birthdate = datetime(birth_year, birth_month, birth_day).date()
        except (ValueError, TypeError):
            flash('Geçersiz doğum tarihi.', 'error')
            return render_template('auth.html', show_register=True)
        
        if User.query.filter_by(email=email).first():
            flash('Bu e-posta adresi zaten kayıtlı.', 'error')
            return render_template('auth.html', show_register=True)
            
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten kullanılıyor.', 'error')
            return render_template('auth.html', show_register=True)
        
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            gender=gender,
            birthdate=birthdate,
            phone=phone,
            is_admin=False,
            is_approved=False
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Kayıt başarılı! Hesabınız yönetici onayı bekliyor.', 'info')
        return redirect(url_for('login'))
    
    return render_template('auth.html', show_register=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/settings')
@login_required
@permission_required('ayarlar')
def settings():
    return render_template('settings.html')

@app.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        try:
            user = User.query.get(current_user.id)
            
            # Profil resmi yükleme işlemi
            if 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and allowed_file(file.filename):
                    try:
                        # Eski profil resmini sil (varsayılan resim hariç)
                        if user.profile_image and user.profile_image != 'images/pp.png':
                            old_image_path = os.path.join(app.static_folder, user.profile_image)
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                        
                        # Yeni resmi kaydet
                        filename = secure_filename(file.filename)
                        unique_filename = f"images/profile_{user.id}_{int(pytime.time())}_{filename}"
                        filepath = os.path.join(app.static_folder, unique_filename)
                        
                        # Resmi boyutlandır ve kaydet
                        image = Image.open(file)
                        image = image.convert('RGB')  # PNG'yi JPG'ye çevir
                        
                        # En-boy oranını koru ve 300x300 boyutuna getir
                        output_size = (300, 300)
                        image.thumbnail(output_size, Image.Resampling.LANCZOS)
                        
                        # Kare crop için merkezi al
                        width, height = image.size
                        left = (width - min(width, height))/2
                        top = (height - min(width, height))/2
                        right = (width + min(width, height))/2
                        bottom = (height + min(width, height))/2
                        image = image.crop((left, top, right, bottom))
                        
                        # Resmi kaydet
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        image.save(filepath, 'JPEG', quality=85)
                        user.profile_image = unique_filename
                    except Exception as e:
                        return jsonify(success=False, message=f"Resim yükleme hatası: {str(e)}")

            # Diğer profil bilgilerini güncelle
            user.username = request.form.get('username')
            user.first_name = request.form.get('first_name')
            user.last_name = request.form.get('last_name')
            user.email = request.form.get('email')
            # Telefon numarası validasyonu ve temizleme
            phone_input = request.form.get('phone')
            if phone_input:
                # Sadece rakam karakterleri bırak
                phone_digits = ''.join(filter(str.isdigit, phone_input))
                
                # 0 ile başlıyorsa kaldır
                if phone_digits.startswith('0'):
                    phone_digits = phone_digits[1:]
                
                # Türk telefon numarası kontrolü (10 haneli, 5 ile başlamalı)
                if len(phone_digits) != 10 or not phone_digits.startswith('5'):
                    return jsonify(success=False, message="Telefon numarası 5 ile başlamalı ve 10 haneli olmalıdır. Örnek: 5123456789")
                
                user.phone = phone_digits
            else:
                return jsonify(success=False, message="Telefon numarası zorunludur.")
            user.role = request.form.get('meslek')
            user.gender = request.form.get('gender')
            
            # Doğum tarihi kontrolü ve dönüşümü
            birth_date = request.form.get('birthdate')
            if birth_date:
                try:
                    user.birthdate = datetime.strptime(birth_date, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify(success=False, message="Geçersiz doğum tarihi formatı")
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Profil başarıyla güncellendi',
                'profile_image': user.profile_image
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message=f"Profil güncellenirken bir hata oluştu: {str(e)}")

    return render_template('profile.html')

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'Tüm alanları doldurun.'}), 400
        
        if not current_user.check_password(current_password):
            return jsonify({'success': False, 'message': 'Mevcut şifre yanlış!'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Yeni şifre en az 6 karakter olmalıdır!'}), 400
        
        current_user.set_password(new_password)
        db.session.commit()
        
        # Log oluştur
        log_activity(
            activity_type='sifre_degistirme',
            description='Kullanıcı şifresini değiştirdi',
            user_id=current_user.id
        )
        
        return jsonify({'success': True, 'message': 'Şifreniz başarıyla değiştirildi!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Şifre değiştirme işlemi başarısız: {str(e)}'}), 500

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        password = request.form.get('password')
        
        if not password:
            return jsonify({'success': False, 'message': 'Şifre gereklidir.'}), 400
        
        if not current_user.check_password(password):
            return jsonify({'success': False, 'message': 'Şifre yanlış!'}), 400
        
        # Admin kullanıcısını silemezsiniz
        if current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin hesabı silinemez!'}), 400
        
        user_id = current_user.id
        username = current_user.username
        
        # Log oluştur (kullanıcı silinmeden önce)
        log_activity(
            activity_type='hesap_silme',
            description=f'Kullanıcı hesabını sildi: {username}',
            user_id=current_user.id
        )
        
        # İlişkili verileri temizle
        ActivityLog.query.filter_by(user_id=user_id).delete()
        
        # Kullanıcının dosyalarını, duyurularını vs. başka kullanıcıya aktar veya sil
        # (Bu kısım daha karmaşık, şimdilik basit tutuyoruz)
        
        # Kullanıcıyı sil
        User.query.filter_by(id=user_id).delete()
        db.session.commit()
        
        logout_user()
        
        return jsonify({'success': True, 'message': 'Hesabınız başarıyla silindi!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Hesap silme işlemi başarısız: {str(e)}'}), 500

@app.route('/enable_2fa', methods=['POST'])
@login_required
def enable_2fa():
    """İki faktörlü doğrulamayı etkinleştir/devre dışı bırak"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        user = User.query.get(current_user.id)
        
        # Permissions'ı güncelle
        if not user.permissions:
            user.permissions = {}
        
        user.permissions['two_factor_auth'] = enabled
        db.session.commit()
        
        # Log oluştur
        log_activity(
            activity_type='guvenlik_ayar',
            description=f'İki faktörlü doğrulama {"etkinleştirildi" if enabled else "devre dışı bırakıldı"}',
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True, 
            'message': f'İki faktörlü doğrulama {"etkinleştirildi" if enabled else "devre dışı bırakıldı"}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'İşlem başarısız: {str(e)}'
        }), 500

# Admin paneli için decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Bu sayfaya erişmek için giriş yapmanız gerekiyor.', 'error')
            return redirect(url_for('login', next=request.url))
            
        if not current_user.is_admin:
            flash('Bu sayfa sadece yöneticiler tarafından erişilebilir.', 'error')
            
            # API istekleri için JSON yanıtı
            if request.is_json:
                return jsonify({'success': False, 'error': 'Yönetici yetkisi gerekiyor'}), 403
                
            return redirect(url_for('anasayfa'))
            
        return f(*args, **kwargs)
    return decorated_function

# Protect routes
@app.before_request
def check_user_auth():
    # Giriş gerektirmeyen sayfalar
    public_endpoints = ['login', 'register', 'static']
    
    # Kullanıcı giriş yapmış ama onaylanmamış ise
    if current_user.is_authenticated and not current_user.is_approved and not current_user.is_admin:
        if request.endpoint not in ['logout']:
            flash('Hesabınız henüz onaylanmamış. Lütfen yönetici onayını bekleyin.', 'warning')
            logout_user()
            return redirect(url_for('login'))
    
    # Kullanıcı giriş yapmamış ve korumalı bir sayfaya erişmeye çalışıyorsa
    if not current_user.is_authenticated and request.endpoint not in public_endpoints:
        return redirect(url_for('login'))

# Türkçe tarih için locale ayarı
try:
    locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'tr_TR')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')  # Sistem varsayılanını kullan

@app.context_processor
def inject_datetime():
    try:
        # Türkiye timezone'ını kullan
        import pytz
        turkey_tz = pytz.timezone('Europe/Istanbul')
        now = datetime.now(turkey_tz)
        
        # Türkçe gün adları için manuel çeviri
        turkce_gunler = {
            'Monday': 'Pazartesi',
            'Tuesday': 'Salı', 
            'Wednesday': 'Çarşamba',
            'Thursday': 'Perşembe',
            'Friday': 'Cuma',
            'Saturday': 'Cumartesi',
            'Sunday': 'Pazar'
        }
        
        gun_adi = turkce_gunler.get(now.strftime('%A'), now.strftime('%A'))
        
        current_time = {
            'weekday': gun_adi,  # Türkçe gün adı
            'time': now.strftime('%H:%M'),  # Saat
            'date': now.strftime('%d.%m.%Y')  # Tarih
        }
    except Exception as e:
        print(f"Tarih inject hatası: {e}")
        current_time = {
            'weekday': '',
            'time': '',
            'date': ''
        }
    return dict(current_time=current_time)

def log_activity(activity_type, description, user_id, case_id=None, related_announcement_id=None, related_event_id=None, related_payment_id=None, details=None):
    user = User.query.get(user_id)
    if user:
        activity = ActivityLog(
            activity_type=activity_type,
            description=description.format(user_name=user.get_full_name()), # Kullanıcı adını formatla
            user_id=user_id,
            related_case_id=case_id,
            related_announcement_id=related_announcement_id, # Yeni eklendi
            related_event_id=related_event_id,           # Yeni eklendi
            related_payment_id=related_payment_id,         # Yeni eklendi
            details=details                              # Yeni eklendi
        )
        db.session.add(activity)
        db.session.commit()

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'LawAutomation'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

@app.route('/')
def anasayfa():
    # Kullanıcı giriş yapmamışsa login sayfasına yönlendir
    if not current_user.is_authenticated:
        # landing.html dosyasında duyurular bölümü olmadığı için buraya eklemeyeceğiz.
        return render_template('landing.html', title="Anasayfa")

    # Giriş yapmış kullanıcı için ana sayfa içeriği
    try:
        activities_raw = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
        # Activities timestamp'lerini güvenli şekilde formatla
        activities = []
        for activity in activities_raw:
            # Timestamp'i tamamen formatlanmış string olarak hazırla
            try:
                if activity.timestamp:
                    app.logger.info(f"Processing activity {activity.id}, timestamp: {activity.timestamp}, type: {type(activity.timestamp)}")
                    if hasattr(activity.timestamp, 'tzinfo') and activity.timestamp.tzinfo is not None:
                        # Timezone aware datetime - timezone'u kaldır ve formatla
                        naive_timestamp = activity.timestamp.replace(tzinfo=None)
                        activity.formatted_timestamp_str = naive_timestamp.strftime('%d.%m.%Y %H:%M')
                        app.logger.info(f"Formatted timezone aware: {activity.formatted_timestamp_str}")
                    else:
                        # Naive datetime (eski UTC kayıtlar) - Türkiye saatine çevir
                        utc_time = activity.timestamp.replace(tzinfo=timezone.utc)
                        turkey_tz = timezone(timedelta(hours=3))
                        turkey_time = utc_time.astimezone(turkey_tz).replace(tzinfo=None)
                        activity.formatted_timestamp_str = turkey_time.strftime('%d.%m.%Y %H:%M')
                        app.logger.info(f"Formatted naive (UTC->Turkey): {activity.formatted_timestamp_str}")
                else:
                    app.logger.warning(f"Activity {activity.id} has no timestamp")
                    activity.formatted_timestamp_str = 'Tarih yok'
            except Exception as e:
                app.logger.error(f"Activity {activity.id} timestamp formatlamada hata: {str(e)} - {activity.timestamp}")
                activity.formatted_timestamp_str = f'Format hatası: {str(e)}'
            activities.append(activity)
    except Exception as e:
        app.logger.error(f"Activities yüklenirken hata: {str(e)}")
        activities = []
    
    total_activities = ActivityLog.query.count() # Tüm aktivitelerin sayısını al
    upcoming_hearings = CalendarEvent.query.filter(
        CalendarEvent.date >= date.today(),
        CalendarEvent.event_type.in_(['durusma', 'e-durusma']),
        CalendarEvent.is_completed == False
    ).order_by(CalendarEvent.date.asc(), CalendarEvent.time.asc()).limit(5).all()
    total_hearings = CalendarEvent.query.filter(CalendarEvent.event_type.in_(['durusma', 'e-durusma'])).count() # Tüm duruşmaların sayısını al
    
    # Duyuruları al (yetki kontrolü ile)
    if current_user.has_permission('duyuru_goruntule'):
        announcements_raw = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        
        # Türkçe tarih formatı için ay isimleri
        turkish_months = [
            'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
            'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'
        ]
        
        # Duyurulara Türkçe tarih ekle (UTC'den Türkiye saatine çevir)
        announcements = []
        turkey_tz = timezone(timedelta(hours=3))  # Türkiye UTC+3
        for ann in announcements_raw:
            # UTC saati varsa Türkiye saatine çevir
            if ann.created_at.tzinfo is None:
                # UTC olarak kabul et ve Türkiye saatine çevir
                utc_time = ann.created_at.replace(tzinfo=timezone.utc)
                turkey_time = utc_time.astimezone(turkey_tz)
            else:
                turkey_time = ann.created_at.astimezone(turkey_tz)
            
            ann.turkish_date = f"{turkey_time.day} {turkish_months[turkey_time.month - 1]} {turkey_time.year}, {turkey_time.strftime('%H:%M')}"
            announcements.append(ann)
    else:
        announcements = []  # Yetki yoksa boş liste

    user_cases = CaseFile.query.all() # Kullanıcı filtresi kaldırıldı
    total_cases = len(user_cases)
    total_active_cases = sum(1 for case in user_cases if case.status == 'Aktif') 
    pending_cases = sum(1 for case in user_cases if case.status == 'Beklemede')
    closed_cases = sum(1 for case in user_cases if case.status == 'Kapalı')

    # Dosya türüne göre istatistikler
    hukuk_count = sum(1 for case in user_cases if case.file_type and case.file_type.lower() == 'hukuk')
    ceza_count = sum(1 for case in user_cases if case.file_type and case.file_type.lower() == 'ceza')
    icra_count = sum(1 for case in user_cases if case.file_type and case.file_type.lower() == 'icra')

    # Adliye istatistikleri
    courthouse_stats_dict = {}
    for case in user_cases:
        if case.courthouse and case.courthouse.strip().lower() not in ['', 'uygulanmaz']:
            courthouse_stats_dict[case.courthouse] = courthouse_stats_dict.get(case.courthouse, 0) + 1
    courthouse_stats = [{'courthouse': k, 'total_cases': v} for k, v in courthouse_stats_dict.items()]


    # Ödeme istatistikleri (opsiyonel, gerekirse eklenebilir)
    # total_payments_this_month = db.session.query(func.sum(Payment.amount)).filter(...).scalar()

    return render_template('anasayfa.html', 
                           title="Anasayfa", 
                           activities=activities, # Kullanıcı filtresi kaldırıldı
                           total_activities=total_activities, # Şablona gönder
                           upcoming_hearings=upcoming_hearings, # Kullanıcı filtresi kaldırıldı
                           announcements=announcements,
                           total_hearings=total_hearings, # Şablona gönder
                           user_cases=user_cases, # Dosya istatistikleri için eklendi
                           total_cases=total_cases,
                           total_active_cases=total_active_cases, # active_cases -> total_active_cases
                           pending_cases=pending_cases,
                           closed_cases=closed_cases,
                           hukuk_count=hukuk_count, # Eklendi
                           ceza_count=ceza_count,   # Eklendi
                           icra_count=icra_count,   # Eklendi
                           courthouse_stats=courthouse_stats # Eklendi
                           )

# Daha fazla aktivite yüklemek için yeni endpoint
@app.route('/load_more_activities/<int:offset>')
def load_more_activities(offset):
    try:
        activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).offset(offset).limit(5).all()
        
        activities_data = []
        for activity in activities:
            try:
                user = User.query.get(activity.user_id)
                
                # Timestamp formatting with error handling
                if activity.timestamp:
                    if hasattr(activity.timestamp, 'tzinfo') and activity.timestamp.tzinfo is not None:
                        # Timezone aware datetime - timezone'u kaldır ve formatla
                        timestamp_str = activity.timestamp.replace(tzinfo=None).strftime('%d.%m.%Y %H:%M')
                    else:
                        # Naive datetime (eski UTC kayıtlar) - Türkiye saatine çevir
                        utc_time = activity.timestamp.replace(tzinfo=timezone.utc)
                        turkey_tz = timezone(timedelta(hours=3))
                        turkey_time = utc_time.astimezone(turkey_tz).replace(tzinfo=None)
                        timestamp_str = turkey_time.strftime('%d.%m.%Y %H:%M')
                else:
                    timestamp_str = 'Bilinmeyen tarih'
                
                activity_data = {
                    'type': activity.activity_type,
                    'description': activity.description,
                    'timestamp': timestamp_str,
                    'user': user.get_full_name() if user else 'Bilinmeyen Kullanıcı',
                    'details': activity.details,
                    'profile_image': url_for('static', filename=user.profile_image) if user and user.profile_image else url_for('static', filename='images/pp.png')
                }
                activities_data.append(activity_data)
            except Exception as e:
                app.logger.error(f"Activity işleme hatası: {str(e)}")
                continue
        
        return jsonify(activities=activities_data)
    except Exception as e:
        app.logger.error(f"Load more activities hatası: {str(e)}")
        return jsonify(activities=[], error=str(e))

@app.route('/takvim')
@login_required
@permission_required('takvim_goruntule')
def takvim():
    # Debug mesajları
    print(f"Kullanıcı admin mi: {current_user.is_admin}")
    print(f"Kullanıcı yetkileri: {current_user.permissions}")
    print(f"Takvim görüntüleme yetkisi: {current_user.has_permission('takvim_goruntule')}")
    
    # Etkinlik görüntüleme yetki kontrolü
    if not current_user.has_permission('etkinlik_goruntule'):
        events_data = []  # Yetki yoksa boş liste döndür
    else:
        # Tüm etkinlikleri getir
        events = CalendarEvent.query.all()
        events_data = []
        
        for event in events:
            event_data = {
                'id': event.id,
                'title': event.title,
                'date': event.date.strftime('%Y-%m-%d'),
                'time': event.time.strftime('%H:%M') if event.time else None,
                'event_type': event.event_type,
                'description': event.description,
                'assigned_to': event.assigned_to,
                'file_type': event.file_type,
                'courthouse': event.courthouse,
                'department': event.department,
                'deadline_date': event.deadline_date.strftime('%Y-%m-%d') if event.deadline_date else None,
                'is_completed': event.is_completed,
                'muvekkil_isim': event.muvekkil_isim,
                'muvekkil_telefon': event.muvekkil_telefon
            }
            events_data.append(event_data)
    
    # Debug için dosya türü, adliye ve departman verilerini kontrol et
    for event_data in events_data:
        if event_data['event_type'] in ['durusma', 'e-durusma']:
            print(f"Etkinlik {event_data['id']} - Dosya Türü: {event_data['file_type']}, Adliye: {event_data['courthouse']}, Departman: {event_data['department']}")
    
    # Adli tatil tarihlerini ekle
    current_year = datetime.now().year
    adli_tatil_data = []
    
    # 2024-2027 yılları için adli tatil tarihlerini ekle
    for year in range(2024, 2028):
        adli_tatil_data.append({
            'start': f'{year}-07-20',
            'end': f'{year}-08-31',
            'year': year
        })
    
    # === YENİ: Adliye verisini hazırla ===
    # Adliye listesini dosyadan yükle
    cities_courthouses, cities = parse_adliye_list()
    
    # Kullanıcının yetkilerini template'e gönder
    user_permissions = {
        'can_add': current_user.has_permission('etkinlik_ekle'),
        'can_edit': current_user.has_permission('etkinlik_duzenle'),
        'can_delete': current_user.has_permission('etkinlik_sil'),
        'can_view': current_user.has_permission('etkinlik_goruntule')
    }
    
    # Onaylı kullanıcıların listesini al
    approved_users = User.query.filter_by(is_approved=True).all()
    users_data = []
    for user in approved_users:
        users_data.append({
            'id': user.id,
            'full_name': user.get_full_name(),
            'role': user.role,
            'email': user.email
        })
    
    return render_template('takvim.html', 
                         events=events_data,
                         adli_tatil_data=adli_tatil_data,
                         all_courthouses=cities_courthouses, # Tüm adliye verilerini gönder
                         user_permissions=user_permissions,
                         approved_users=users_data)

@app.route('/dosyalarim')
def dosyalarim():
    # URL parametrelerini al
    file_type = request.args.get('file_type')
    status = request.args.get('status')
    
    # Sorguyu başlat
    query = CaseFile.query
    
    # Filtreler
    if file_type:
        query = query.filter_by(file_type=file_type)
    if status:
        query = query.filter_by(status=status)
    
    # Sonuçları al
    case_files = query.all()
    
    return render_template('dosyalarim.html', 
                         case_files=case_files,
                         selected_type=file_type,
                         selected_status=status)

@app.route('/duyurular', methods=['GET', 'POST'])
@login_required
@permission_required('duyuru_goruntule')
def duyurular():
    if request.method == 'POST':
        if not current_user.has_permission('duyuru_ekle'):
            # AJAX isteği kontrolü
            if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                return jsonify({'success': False, 'error': 'Duyuru ekleme yetkiniz yok.'}), 403
            else:
                flash('Duyuru ekleme yetkiniz yok.', 'error')
                return redirect(url_for('duyurular'))
            
        title = request.form['title']
        content = request.form['content']
        new_announcement = Announcement(title=title, content=content, user_id=current_user.id)
        db.session.add(new_announcement)
        
        # Log kaydı
        log = ActivityLog(
            activity_type='duyuru_ekleme',
            description=f'Yeni duyuru eklendi',
            details={
                'baslik': title,
                'icerik': content[:50] + '...' if len(content) > 50 else content
            },
            user_id=current_user.id,
            related_announcement_id=new_announcement.id
        )
        db.session.add(log)
        db.session.commit()
        
        # AJAX isteği kontrolü
        if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            return jsonify({'success': True, 'message': 'Duyuru başarıyla eklendi.'}), 200
        else:
            flash('Duyuru başarıyla eklendi.', 'success')
            return redirect(url_for('duyurular'))
    
    # Açık SQL hatası: Announcement.created_at sütunu eklenmiş ama 
    # models.py'da tanımlandığını gördük; bu sorgu tüm nesneleri çekiyor
    # Sadece gerekli sütunları belirterek sorunu çözelim
    announcements = db.session.query(
        Announcement.id,
        Announcement.title,
        Announcement.content,
        Announcement.user_id
    ).all()
    
    return render_template('duyurular.html', announcements=announcements)

@app.route('/odemeler', methods=['GET', 'POST'])
@login_required
def odemeler():
    if not current_user.has_permission('odeme_goruntule'):
        flash('Ödeme görüntüleme yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('anasayfa'))
        
    today_date_str = datetime.now().strftime('%Y-%m-%d') # Bugünün tarihini YYYY-MM-DD formatında al

    if request.method == 'POST':
        if not current_user.has_permission('odeme_ekle'):
            # AJAX isteği kontrolü
            if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                return jsonify({'success': False, 'error': 'Ödeme ekleme yetkiniz bulunmamaktadır.'}), 403
            else:
                flash('Ödeme ekleme yetkiniz bulunmamaktadır.', 'error')
                return redirect(url_for('odemeler'))
            
        name = request.form['name']
        surname = request.form['surname']
        tc = request.form['tc']
        currency = request.form['currency']
        installments = request.form['installments']

        try:
            # Frontend'den gelen tutarı direkt olarak çevir, hiçbir temizleme işlemi yapmadan
            amount_str = request.form['amount']
            
            # Sayısal değer kontrolü (herhangi bir formatlama yapmıyoruz)
            try:
                amount_value = float(amount_str)
            except ValueError:
                app.logger.error(f"Tutar dönüşüm hatası: Tutar '{amount_str}' geçerli bir sayı değil")
                return jsonify({'success': False, 'error': 'Geçersiz tutar formatı. Lütfen sadece sayı girin.'}), 400
            
            # Kayıt için kullanılacak değeri log kaydına ekle
            app.logger.info(f"POST /odemeler - Kaydedilen tutar: {amount_value}")
        except Exception as e:
            app.logger.error(f"POST /odemeler - Tutar işleme hatası: {str(e)}")
            return jsonify({'success': False, 'error': 'Tutar işlenirken bir hata oluştu.'}), 400

        # Tarih alanlarını datetime.date nesnelerine dönüştür
        registration_date = None
        due_date = None
        
        if request.form.get('registration_date'):
            registration_date = datetime.strptime(request.form.get('registration_date'), '%Y-%m-%d').date()
        
        if request.form.get('due_date'):
            due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        
        # Yeni client oluştur
        new_client = Client(
            name=name, 
            surname=surname, 
            tc=tc, 
            amount=amount_value,  # Sayısal değeri kullan
            currency=currency, 
            installments=installments, 
            registration_date=registration_date, 
            due_date=due_date
        )
        
        # Kaydet
        db.session.add(new_client)
        
        # Log kaydı
        log = ActivityLog(
            activity_type='odeme_ekleme',
            description=f'Yeni ödeme eklendi: {name} {surname}',
            details={
                'musteri': f'{name} {surname}',
                'tc': tc,
                'tutar': f'{amount_value} {currency}',
                'taksit': installments,
                'borc_kayit_tarihi': request.form.get('registration_date'),
                'son_odeme_tarihi': request.form.get('due_date')
            },
            user_id=current_user.id,
            related_payment_id=new_client.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True})
    
    clients = Client.query.all()
    return render_template('odemeler.html', clients=clients, today_date=today_date_str) # today_date'i template'e gönder

@app.route('/update_client/<int:client_id>', methods=['POST'])
@login_required
def update_client(client_id):
    if not current_user.has_permission('odeme_duzenle'):
        return jsonify({'success': False, 'error': 'Ödeme düzenleme yetkiniz bulunmamaktadır.'}), 403
        
    try:
        data = request.get_json()
        client = Client.query.get_or_404(client_id)
        if client:
            old_status = client.status
            client.name = data['name']
            client.surname = data['surname']
            client.tc = data['tc']
            
            # Frontend'den gelen tutarı doğrudan dönüştür, hiçbir temizleme yapmadan
            try:
                amount_str = data['amount']
                
                # Sayısal değer kontrolü
                try:
                    amount_value = float(amount_str)
                except ValueError:
                    app.logger.error(f"Tutar dönüşüm hatası: Tutar '{amount_str}' geçerli bir sayı değil")
                    return jsonify({'success': False, 'error': 'Geçersiz tutar formatı. Lütfen sadece sayı girin.'}), 400
                    
                # Önceki değer ve yeni değeri karşılaştır
                app.logger.info(f"POST /update_client/{client_id} - Eski tutar: {client.amount}, Yeni tutar: {amount_value}")
                
                # Tutarı güncelle
                client.amount = amount_value
            except Exception as e:
                app.logger.error(f"POST /update_client/{client_id} - Tutar işleme hatası: {str(e)}")
                return jsonify({'success': False, 'error': 'Tutar işlenirken bir hata oluştu.'})
            
            client.currency = data['currency']
            client.installments = data['installments']
            
            # Tarih alanlarını datetime.date nesnesine dönüştür
            if data.get('registration_date'):
                try:
                    client.registration_date = datetime.strptime(data['registration_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'success': False, 'error': 'Geçersiz borç kayıt tarihi formatı'})
            else:
                client.registration_date = None
                
            if data.get('due_date'):
                try:
                    client.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'success': False, 'error': 'Geçersiz son ödeme tarihi formatı'})
            else:
                client.due_date = None
            
            # Status alanını güvenli bir şekilde al ve güncelle
            new_status = data.get('status')
            if new_status is not None:
                client.status = new_status
            
            client.description = data.get('description', '')

            # Ödeme durumu değiştiyse log kaydı ekle
            if old_status != new_status:
                log = ActivityLog(
                    activity_type='odeme_guncelleme',
                    description=f'Ödeme durumu güncellendi: {client.name} {client.surname}',
                    details={
                        'musteri': f'{client.name} {client.surname}',
                        'eski_durum': old_status,
                        'yeni_durum': new_status,
                        'tutar': f'{client.amount} {client.currency}'
                    },
                    user_id=current_user.id,
                    related_payment_id=client.id
                )
                db.session.add(log)
            
            db.session.commit()
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Müşteri bulunamadı'})
    except Exception as e:
        db.session.rollback()
        # Hata ayrıntılarını kaydet
        app.logger.error(f"update_client hatası: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/musteri_yonetimi')
def musteri_yonetimi():
    return render_template('musteri_yonetimi.html')

@app.route('/raporlar')
def raporlar():
    return render_template('raporlar.html')

@app.route('/kullanici_yonetimi')
def kullanici_yonetimi():
    users = User.query.all()
    return render_template('kullanici_yonetimi.html', users=users)

@app.route('/bildirimler')
def bildirimler():
    notifications = Notification.query.filter_by(read=False).all()
    return render_template('bildirimler.html', notifications=notifications)

@app.route('/dosya_sorgula', methods=['GET', 'POST'])
@login_required
@permission_required('dosya_sorgula')
def dosya_sorgula():
    # Form verilerini al (POST veya GET parametrelerinden)
    file_type = request.form.get('file-type') or request.args.get('file_type')
    city = request.form.get('city') or request.args.get('city')
    courthouse = request.form.get('courthouse') or request.args.get('courthouse')
    department = request.form.get('department') or request.args.get('department')
    court_number = request.form.get('court-number') or request.args.get('court_number')
    year = request.form.get('year') or request.args.get('year')
    case_number = request.form.get('case-number') or request.args.get('case_number')
    client_name = request.form.get('client-name') or request.args.get('client_name')
    status = request.form.get('status') or request.args.get('status')
    
    # Eğer herhangi bir filtre varsa sorguyu çalıştır
    if request.method == 'POST' or any([file_type, city, courthouse, department, court_number, year, case_number, client_name, status]):
        # Sorguyu başlat (Kullanıcı filtresi kaldırıldı)
        query = CaseFile.query
        
        # Filtreler
        if file_type:
            query = query.filter_by(file_type=file_type)
        if courthouse:
            query = query.filter_by(courthouse=courthouse)
        if department:
            query = query.filter_by(department=department)
        # Mahkeme numarası filtresi eklendi
        if court_number:
            query = query.filter_by(department=court_number)
        if year:
            query = query.filter_by(year=year)
        if case_number:
            query = query.filter_by(case_number=case_number)
        if client_name:
            query = query.filter(CaseFile.client_name.ilike(f'%{client_name}%'))
        if status:
            query = query.filter_by(status=status)
        
        # Sonuçları al
        case_files = query.all()
    else:
        case_files = []
    
    # Şehir ve adliye verilerini yükle (dosya_ekle ile aynı fonksiyonu kullanıyor)
    cities_courthouses, cities = parse_adliye_list()
    
    return render_template('dosya_sorgula.html', 
                         case_files=case_files,
                         cities=cities,
                         all_courthouses=json.dumps(cities_courthouses, ensure_ascii=False))

@app.route('/dosya_ekle', methods=['GET', 'POST'])
@login_required
@permission_required('dosya_ekle')
@csrf.exempt
def dosya_ekle():
    if request.method == 'POST':
        try:
            # Form data'yı al (JSON değil)
            data = request.form
            file_type = data.get('file-type')

            # Define required fields based on file_type
            required_fields = ['file-type', 'year', 'case-number', 'client-name', 'open-date']

            # Add courthouse/department based on type
            if file_type not in ['ARABULUCULUK', 'AİHM', 'AYM']:
                required_fields.append('courthouse')
                # Only require department if not Savcılık or the others
                if file_type != 'savcilik':
                    required_fields.append('department')

            # Check if all required fields are present and not empty
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return jsonify(success=False, message=f"Eksik alanlar: {', '.join(missing_fields)}"), 400

            # Get courthouse and department, defaulting to None if not applicable/provided
            courthouse = data.get('courthouse')
            department = data.get('department')

            # Dosya türüne göre özel kontroller
            if file_type.upper() in ['ARABULUCULUK', 'AİHM', 'AYM', 'SAVCILIK']:
                if file_type.upper() == 'AİHM':
                    courthouse = "Avrupa İnsan Hakları Mahkemesi"
                    department = "AİHM"
                elif file_type.upper() == 'AYM':
                    courthouse = "Anayasa Mahkemesi"
                    department = "AYM"
                elif file_type.upper() == 'ARABULUCULUK':
                    courthouse = "Arabuluculuk Merkezi"
                    department = "Arabuluculuk"
                elif file_type.upper() == 'SAVCILIK':
                    courthouse = courthouse or "Cumhuriyet Başsavcılığı"
                    department = ""
            else:
                # Numaralı mahkeme/daire seçilmişse onu kullan
                numbered_department = data.get('court-number')
                if numbered_department:
                    department = numbered_department

            new_case_file = CaseFile(
                file_type=file_type,
                courthouse=courthouse,
                department=department,
                year=int(data['year']),
                case_number=data['case-number'],
                client_name=data['client-name'],
                phone_number=data.get('client-phone', ''), # Phone number is now optional
                status='Aktif',
                open_date=datetime.strptime(data['open-date'], '%Y-%m-%d').date(),
                user_id=current_user.id,
                
                # Müvekkil detay bilgileri
                client_entity_type=data.get('client-entity-type', 'person'),
                client_identity_number=data.get('client-id', ''),
                client_capacity=data.get('client-capacity', ''),
                client_address=data.get('client-address', ''),
                
                # Karşı taraf bilgileri
                opponent_entity_type=data.get('opponent-entity-type', 'person'),
                opponent_name=data.get('opponent-name', ''),
                opponent_identity_number=data.get('opponent-id', ''),
                opponent_capacity=data.get('opponent-capacity', ''),
                opponent_phone=data.get('opponent-phone', ''),
                opponent_address=data.get('opponent-address', ''),
                
                # Vekil bilgileri
                opponent_lawyer=data.get('opponent-lawyer', ''),
                opponent_lawyer_bar_number=data.get('opponent-lawyer-bar-number', ''),
                opponent_lawyer_phone=data.get('opponent-lawyer-phone', ''),
                opponent_lawyer_address=data.get('opponent-lawyer-address', ''),
                
                # EK KİŞİLER - YENİ EKLENEN
                additional_clients_json=data.get('additional_clients_json', ''),
                additional_opponents_json=data.get('additional_opponents_json', '')
            )

            db.session.add(new_case_file)
            db.session.commit()

            # İşlem logu ekle
            log_activity(
                activity_type='dosya_ekleme',
                description=f"Yeni dosya eklendi: {data['client-name']} - {data['case-number']}",
                user_id=current_user.id,
                case_id=new_case_file.id
            )

            # Başarılı yanıt için yönlendirme yap
            flash('Dosya başarıyla eklendi!', 'success')
            return redirect(url_for('dosya_sorgula'))

        except Exception as e:
            db.session.rollback()
            print(f"Hata: {str(e)}")
            flash(f"Dosya eklenirken hata oluştu: {str(e)}", 'error')
            return redirect(url_for('dosya_ekle'))

    # GET isteği için şehir ve adliye verilerini yükle
    cities_courthouses, cities = parse_adliye_list()
    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('dosya_ekle.html',
                         today_date=today_date,
                         cities=cities,
                         all_courthouses=json.dumps(cities_courthouses, ensure_ascii=False)) # Pass all data as JSON

@app.route('/case_details/<int:case_id>')
@login_required
def case_details(case_id):
    # Yetki kontrolü - JSON endpoint için
    if not current_user.has_permission('dosya_goruntule'):
        return jsonify({
            'success': False, 
            'message': 'Bu işlemi yapmak için gerekli yetkiye sahip değilsiniz.'
        }), 403
        
    try:
        case_file = CaseFile.query.get_or_404(case_id)
        
        # Belgeleri hazırla
        documents = [{
            'id': doc.id,
            'filename': doc.filename,
            'document_type': doc.document_type,
            'upload_date': doc.upload_date.strftime('%d.%m.%Y')
        } for doc in case_file.documents]
        
        # Dosya numarasını yıl/esas no formatında hazırla
        formatted_case_number = f"{case_file.year}/{case_file.case_number}"
        
        # Duruşma türünü Büyük Harfle başlayacak şekilde biçimlendir
        formatted_hearing_type = "E-Duruşma" if case_file.hearing_type == "e-durusma" else "Duruşma"
        
        # Şehir bilgisini adliye adından çıkar
        city = "Bilinmiyor"
        if case_file.courthouse:
            if case_file.courthouse.startswith("İstanbul"):
                city = "İstanbul"
            else:
                # Adliye adından şehir ismini çıkarmak için adliye listesini kontrol et
                cities_courthouses, cities = parse_adliye_list()
                for city_name, courthouses in cities_courthouses.items():
                    if any(case_file.courthouse in courthouse for courthouse in courthouses):
                        city = city_name
                        break
        
        # Ek müvekkil, karşı taraf ve vekil bilgilerini JSON'dan parse et
        additional_clients = []
        additional_opponents = []
        additional_lawyers = []
        
        if case_file.additional_clients_json:
            try:
                import json
                additional_clients = json.loads(case_file.additional_clients_json)
            except:
                additional_clients = []
                
        if case_file.additional_opponents_json:
            try:
                import json
                additional_opponents = json.loads(case_file.additional_opponents_json)
            except:
                additional_opponents = []
                
        if case_file.additional_lawyers_json:
            try:
                import json
                additional_lawyers = json.loads(case_file.additional_lawyers_json)
            except:
                additional_lawyers = []
        
        return jsonify({
            'success': True,
            'file_type': case_file.file_type,
            'courthouse': case_file.courthouse,
            'city': city,  # Şehir bilgisi eklendi
            'department': case_file.department,
            'year': case_file.year,
            'case_number': formatted_case_number,  # Formatlanmış dosya numarası
            'client_name': case_file.client_name,
            'phone_number': case_file.phone_number,
            'status': case_file.status,
            'open_date': case_file.open_date.strftime('%d.%m.%Y') if case_file.open_date else None,
            'next_hearing': case_file.next_hearing.strftime('%d.%m.%Y') if case_file.next_hearing else None,
            'hearing_time': case_file.hearing_time,  # Eklenen hearing_time alanı
            'hearing_type': case_file.hearing_type, # Duruşma türü
            'event_type': case_file.hearing_type,   # Frontend'de doğru radio button'un seçilmesi için
            'formatted_hearing_type': formatted_hearing_type, # Görüntü için biçimlendirilmiş tür
            
            # Müvekkil detay bilgileri
            'client_entity_type': case_file.client_entity_type,
            'client_identity_number': case_file.client_identity_number,
            'client_capacity': case_file.client_capacity,
            'client_address': case_file.client_address,
            
            # Karşı taraf bilgileri
            'opponent_entity_type': case_file.opponent_entity_type,
            'opponent_name': case_file.opponent_name,
            'opponent_identity_number': case_file.opponent_identity_number,
            'opponent_capacity': case_file.opponent_capacity,
            'opponent_phone': case_file.opponent_phone,
            'opponent_address': case_file.opponent_address,
            
            # Vekil bilgileri
            'opponent_lawyer': case_file.opponent_lawyer,
            'opponent_lawyer_bar_number': case_file.opponent_lawyer_bar_number,
            'opponent_lawyer_phone': case_file.opponent_lawyer_phone,
            'opponent_lawyer_address': case_file.opponent_lawyer_address,
            
            # Ek müvekkiller, karşı taraflar ve vekiller
            'additional_clients': additional_clients,
            'additional_opponents': additional_opponents,
            'additional_lawyers': additional_lawyers,
            
            'expenses': [{
                'id': expense.id,
                'expense_type': expense.expense_type,
                'amount': str(expense.amount),
                'date': expense.date.strftime('%d.%m.%Y'),
                'description': expense.description,
                'is_paid': expense.is_paid
            } for expense in case_file.expenses],
            'documents': documents,
            'description': case_file.description
        })
    except Exception as e:
        print(f"Hata: {str(e)}")
        return jsonify(success=False, message=str(e))

@app.route('/edit_case/<int:case_id>', methods=['POST'])
@login_required
@permission_required('dosya_duzenle')
def edit_case(case_id):
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(success=False, message="Geçersiz veri formatı"), 400
            
        case_file = db.session.get(CaseFile, case_id)
        if not case_file:
            return jsonify(success=False, message="Dosya bulunamadı"), 404
            
        # Zorunlu alanları kontrol et
        if 'client_name' in data and not data['client_name'].strip():
            return jsonify(success=False, message="Müvekkil adı boş olamaz"), 400
            
        # Dosya bilgilerini güncelle
        if os.getenv('DEBUG', 'False').lower() == 'true':
            print(f"DEBUG: edit_case - received file_type: {data.get('file_type')}")
            print(f"DEBUG: edit_case - current case file_type: {case_file.file_type}")
        if 'file_type' in data and data['file_type']:
            case_file.file_type = data['file_type']
            if os.getenv('DEBUG', 'False').lower() == 'true':
                print(f"DEBUG: edit_case - updated file_type to: {case_file.file_type}")
        if 'courthouse' in data and data['courthouse']:
            case_file.courthouse = data['courthouse']
        if 'client_name' in data and data['client_name']:
            case_file.client_name = data['client_name'].strip()
        if 'phone_number' in data:
            case_file.phone_number = data['phone_number']
        if 'status' in data and data['status']:
            case_file.status = data['status']
        if 'description' in data:
            case_file.description = data['description']
        if 'hearing_time' in data:
            case_file.hearing_time = data['hearing_time']
        
        # Müvekkil detay bilgileri
        if 'client_identity_number' in data:
            case_file.client_identity_number = data['client_identity_number']
        if 'client_capacity' in data:
            case_file.client_capacity = data['client_capacity']
        if 'client_address' in data:
            case_file.client_address = data['client_address']
        
        # Karşı taraf bilgileri
        if 'opponent_name' in data:
            case_file.opponent_name = data['opponent_name']
        if 'opponent_identity_number' in data:
            case_file.opponent_identity_number = data['opponent_identity_number']
        if 'opponent_capacity' in data:
            case_file.opponent_capacity = data['opponent_capacity']
        if 'opponent_phone' in data:
            case_file.opponent_phone = data['opponent_phone']
        if 'opponent_address' in data:
            case_file.opponent_address = data['opponent_address']
        
        # Vekil bilgileri
        if 'opponent_lawyer' in data:
            case_file.opponent_lawyer = data['opponent_lawyer']
        if 'opponent_lawyer_bar_number' in data:
            case_file.opponent_lawyer_bar_number = data['opponent_lawyer_bar_number']
        if 'opponent_lawyer_phone' in data:
            case_file.opponent_lawyer_phone = data['opponent_lawyer_phone']
        if 'opponent_lawyer_address' in data:
            case_file.opponent_lawyer_address = data['opponent_lawyer_address']
        
        # Entity type bilgileri
        if 'client_entity_type' in data:
            case_file.client_entity_type = data['client_entity_type']
        if 'opponent_entity_type' in data:
            case_file.opponent_entity_type = data['opponent_entity_type']
        
        # Ek müvekkiller, karşı taraflar ve vekiller JSON formatında
        if 'additional_clients_json' in data:
            import json
            try:
                # Eğer string olarak geliyorsa parse et, liste olarak geliyorsa direk JSON'a çevir
                if isinstance(data['additional_clients_json'], str):
                    additional_clients = json.loads(data['additional_clients_json'])
                else:
                    additional_clients = data['additional_clients_json']
                case_file.additional_clients_json = json.dumps(additional_clients)
            except:
                case_file.additional_clients_json = None
                
        if 'additional_opponents_json' in data:
            import json
            try:
                if isinstance(data['additional_opponents_json'], str):
                    additional_opponents = json.loads(data['additional_opponents_json'])
                else:
                    additional_opponents = data['additional_opponents_json']
                case_file.additional_opponents_json = json.dumps(additional_opponents)
            except:
                case_file.additional_opponents_json = None
                
        if 'additional_lawyers_json' in data:
            import json
            try:
                if isinstance(data['additional_lawyers_json'], str):
                    additional_lawyers = json.loads(data['additional_lawyers_json'])
                else:
                    additional_lawyers = data['additional_lawyers_json']
                case_file.additional_lawyers_json = json.dumps(additional_lawyers)
            except:
                case_file.additional_lawyers_json = None
        
        # Duruşma türünü al ve kaydet
        if 'hearing_type' in data and data['hearing_type']:
            case_file.hearing_type = data['hearing_type']
        
        # Departman bilgisini de güncelle
        if 'department' in data and data['department']:
            case_file.department = data['department']
        
        # Açılış tarihi kontrolü (sadece güncellemeye izin verilen durumlarda)
        if 'open_date' in data and data['open_date']:
            try:
                case_file.open_date = datetime.strptime(data['open_date'], '%Y-%m-%d').date()
            except ValueError:
                print(f"Açılış tarihi çevirme hatası: {data['open_date']}")
                # Açılış tarihinde hata varsa sessizce geç
        
        # Duruşma tarihi ve saati opsiyonel - daha güvenli tarih işleme
        if 'next_hearing' in data:
            next_hearing_str = data['next_hearing']
            if next_hearing_str and next_hearing_str.strip():
                try:
                    case_file.next_hearing = datetime.strptime(next_hearing_str, '%Y-%m-%d').date()
                except ValueError as ve:
                    print(f"Duruşma tarihi çevirme hatası: {ve}")
                    return jsonify(success=False, message=f"Geçersiz duruşma tarihi formatı: {next_hearing_str}"), 400
            else:
                case_file.next_hearing = None
        
        db.session.commit()
        
        log_activity(
            activity_type='dosya_duzenleme',
            description=f"Dosya güncellendi: {case_file.client_name}",
            user_id=current_user.id,
            case_id=case_id
        )
        
        return jsonify(success=True, message="Dosya başarıyla güncellendi")
        
    except Exception as e:
        print(f"Dosya güncelleme hatası: {str(e)}")
        db.session.rollback()
        return jsonify(success=False, message=f"Sunucu hatası: {str(e)}"), 500

@app.route('/delete_case/<int:case_id>', methods=['POST'])
@login_required
@permission_required('dosya_sil')
def delete_case(case_id):
    case_file = CaseFile.query.get(case_id)
    if case_file:
        db.session.delete(case_file)
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False)

# Static dosyalar için özel route
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    results = []
    
    if len(query) >= 2:
        # Dosya araması - müvekkil adı veya esas numarasına göre
        case_files = CaseFile.query.filter(
            db.or_(
                CaseFile.client_name.ilike(f'%{query}%'),
                CaseFile.case_number.ilike(f'%{query}%')
            )
        ).all()
        
        for case in case_files:
            # Başlık formatını güncelle - yıl/esas no formatında
            formatted_case_number = f"{case.year}/{case.case_number}"
            title = f"{case.client_name} - {formatted_case_number} ({case.file_type.title()})"
            results.append({
                'type': 'Dosya',
                'title': title,
                'url': f'#',
                'id': case.id,
                'source': 'case_file'
            })
        
        # Müşteri ödemeleri araması
        clients = Client.query.filter(
            Client.name.ilike(f'%{query}%') | 
            Client.surname.ilike(f'%{query}%')
        ).all()
        
        for client in clients:
            results.append({
                'type': 'Müşteri',
                'title': f"{client.name} {client.surname} - Ödeme Bilgileri",
                'url': f'#',
                'id': client.id,
                'source': 'client'
            })
    
    return jsonify(results)

@app.route('/add_event', methods=['POST'])
@login_required
@csrf.exempt
def add_event():
    if not current_user.has_permission('etkinlik_ekle'):
        return jsonify({'error': 'Takvime etkinlik ekleme yetkiniz bulunmamaktadır.'}), 403
        
    try:
        data = request.get_json()
        
        app.logger.info(f"Etkinlik ekleme isteği alındı: {data}")
        
        # Tarihleri UTC'ye çevirmeden işle
        date_str = data['date']
        time_str = data['time']
        deadline_str = data.get('deadline_date')
        
        # Tarihleri doğrudan string'den date objesine çevir
        event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Günlük Kayıt için saati 00:00 olarak kaydet
        if data['event_type'] == 'gunluk-kayit':
            event_time = datetime.strptime('00:00', '%H:%M').time()
        else:
            event_time = datetime.strptime(time_str, '%H:%M').time()
        
        # deadline_date kontrolü - eğer varsa çevir, yoksa None olarak bırak
        deadline_date = None
        if deadline_str:
            try:
                deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError as e:
                app.logger.error(f"deadline_date çevirme hatası: {e}")
                # Hata durumunda deadline_date None olarak kalır
        
        # Duruşma bilgilerini kontrol et
        event_type = data['event_type']
        file_type = None
        courthouse = None
        department = None
        
        if event_type in ['durusma', 'e-durusma']:
            file_type = data.get('file_type')
            courthouse = data.get('courthouse')
            department = data.get('department')
            
            # Duruşma bilgileri eksikse hata döndür
            if not file_type or not courthouse or not department:
                return jsonify({'error': 'Duruşma/E-Duruşma için dosya türü, adliye ve birim bilgileri gereklidir.'}), 400
        
            # Kullanıcı tarafından girilen açıklama varsa onu kullan
            description = data.get('description', '')
        else:
            description = data.get('description', '')
        
        # Günlük Kayıt için atanan kişi null, diğerleri için normal
        if data['event_type'] == 'gunluk-kayit':
            assigned_to = None  # Günlük Kayıt için atanan kişi kaydedilmez
        else:
            assigned_to = data.get('assigned_to', '')
        
        event = CalendarEvent(
            title=data['title'],
            date=event_date,
            time=event_time,
            event_type=data['event_type'],
            description=description,
            user_id=current_user.id,
            assigned_to=assigned_to,
            deadline_date=deadline_date,
            is_completed=False if data['event_type'] == 'gunluk-kayit' else data.get('is_completed', False),
            file_type=file_type,
            courthouse=courthouse,
            department=department,
            muvekkil_isim=data.get('muvekkil_isim'),
            muvekkil_telefon=data.get('muvekkil_telefon')
        )
        
        db.session.add(event)
        
        # Log kaydı
        log_details = {
            'baslik': data['title'],
            'tarih': date_str,
            'saat': time_str,
            'tur': data['event_type'],
            'aciklama': description,
        }
        
        if file_type:
            log_details['dosya_turu'] = file_type
        if courthouse:
            log_details['adliye'] = courthouse
        if department:
            log_details['birim'] = department
        
        if deadline_str:
            log_details['son_tarih'] = deadline_str
        
        # Son gün etkinliği ekle
        if deadline_date and deadline_date != event_date:
            deadline_event = CalendarEvent(
                title=f"SON GÜN: {event.title}",
                date=deadline_date,
                time=event_time,
                event_type=event.event_type,
                description=description,
                user_id=event.user_id,
                assigned_to=event.assigned_to,
                is_completed=event.is_completed,
                file_type=file_type,
                courthouse=courthouse,
                department=department,
                muvekkil_isim=event.muvekkil_isim,
                muvekkil_telefon=event.muvekkil_telefon
            )
            db.session.add(deadline_event)
        
        db.session.commit()
        
        # Commit sonrası log kaydı oluştur (event.id artık mevcut)
        log = ActivityLog(
            activity_type='etkinlik_ekleme',
            description=f'Yeni etkinlik eklendi: {data["title"]}',
            details=log_details,
            user_id=current_user.id,
            related_event_id=event.id
        )
        db.session.add(log)
        db.session.commit()
        app.logger.info(f"Etkinlik başarıyla eklendi: {event.id}")
        
        # E-posta bildirimi gönder
        if event.assigned_to:
            try:
                # Atanan kişiyi bul
                assigned_user = User.query.filter_by(is_approved=True).filter(
                    User.first_name + ' ' + User.last_name == event.assigned_to.replace('Av. ', '').replace('Stj. Av. ', '').replace('Asst. ', '').replace('Ulşm. ', '').replace('Tkp El. ', '')
                ).first()
                
                if not assigned_user:
                    # Tam isim eşleşmesi yoksa, full_name ile dene
                    for user in User.query.filter_by(is_approved=True).all():
                        if user.get_full_name() == event.assigned_to:
                            assigned_user = user
                            break
                
                if assigned_user:
                    send_calendar_event_assignment_email(
                        user_email=assigned_user.email,
                        user_name=assigned_user.get_full_name(),
                        event_title=event.title,
                        event_date=event_date.strftime('%d.%m.%Y'),
                        event_time=event_time.strftime('%H:%M'),
                        event_type=event.event_type,
                        assigned_by_name=current_user.get_full_name(),
                        courthouse=courthouse,
                        department=department,
                        description=description
                    )
                    app.logger.info(f"Atama e-postası gönderildi: {assigned_user.email}")
                else:
                    app.logger.warning(f"Atanan kullanıcı bulunamadı: {event.assigned_to}")
            except Exception as e:
                app.logger.error(f"E-posta gönderme hatası: {str(e)}")
        
        response_data = {
            'id': event.id,
            'title': event.title,
            'date': event_date.strftime('%Y-%m-%d'),
            'time': event_time.strftime('%H:%M'),
            'event_type': event.event_type,
            'description': description,
            'assigned_to': event.assigned_to,
            'is_completed': event.is_completed,
            'file_type': file_type,
            'courthouse': courthouse,
            'department': department
        }
        
        if deadline_date:
            response_data['deadline_date'] = deadline_date.strftime('%Y-%m-%d')
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Etkinlik ekleme hatası: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400

@app.route('/update_event', methods=['POST'])
@login_required
@csrf.exempt
def update_event():
    app.logger.info(f"/update_event çağrıldı. Kullanıcı: {current_user.email}")
    if not current_user.has_permission('etkinlik_duzenle'):
        app.logger.warning(f"Yetkisiz güncelleme denemesi: Kullanıcı {current_user.email}, Yetki: etkinlik_duzenle")
        return jsonify({"error": "Bu işlem için yetkiniz bulunmamaktadır."}), 403
        
    try:
        data = request.get_json()
        app.logger.info(f"Etkinlik güncelleme isteği alındı (ID: {data.get('id')}): {data}")
        
        # ID kontrolü
        if 'id' not in data:
            app.logger.error("Etkinlik güncelleme hatası: ID eksik.")
            return jsonify({"error": "Etkinlik ID'si belirtilmemiş."}), 400
            
        event_id = data['id']
        event = CalendarEvent.query.get(event_id)
        
        if not event:
            app.logger.error(f"Etkinlik güncelleme hatası: Etkinlik bulunamadı (ID: {event_id})")
            return jsonify({"error": "Etkinlik bulunamadı."}), 404
            
        # Etkinlik düzenleme yetki kontrolü:
        # - Etkinlik düzenleme yetkisi varsa hem kendi hem başkasının etkinliğini düzenleyebilir
        # - Yetkisi yoksa hiç kimsenin etkinliğini düzenleyemez (zaten üstte kontrol ediliyor)
        # Bu kontrol zaten yukarıda has_permission('etkinlik_duzenle') ile yapılıyor, 
        # yani bu satıra gelmiş olan kullanıcının yetkisi var demektir.
            
        # Önceki değerleri kaydet (log için)
        old_values = {
            'title': event.title,
            'date': event.date.strftime('%Y-%m-%d') if event.date else None,
            'time': event.time.strftime('%H:%M') if event.time else None,
            'event_type': event.event_type,
            'description': event.description,
            'assigned_to': event.assigned_to,
            'is_completed': event.is_completed,
            'file_type': event.file_type,
            'courthouse': event.courthouse,
            'department': event.department
        }
        
        # Tarihi ve zamanı güncelle - farklı formatları kontrol et
        if 'date' in data:
            # Yeni format: ayrı date ve time alanları
            try:
                event_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                event.date = event_date
                
                # Time field'ını işle - her zaman bir değer ata
                if data.get('event_type') == 'gunluk-kayit':
                    event_time = datetime.strptime('00:00', '%H:%M').time()
                else:
                    # Eğer time boş, None veya boş string ise varsayılan değer ata
                    time_str = data.get('time', '00:00')
                    if not time_str or not str(time_str).strip() or time_str == 'None':
                        time_str = '00:00'
                    event_time = datetime.strptime(str(time_str), '%H:%M').time()
                
                event.time = event_time
            except ValueError as e:
                app.logger.error(f"Tarih/zaman ayrıştırma hatası: {e}")
                return jsonify({"error": f"Tarih/zaman formatı hatalı: {e}"}), 400
        elif 'start' in data:
            # Eski format: start alanı (ISO formatında string)
            try:
                if isinstance(data['start'], str):
                    start_datetime = datetime.strptime(data['start'], '%Y-%m-%dT%H:%M:%S')
                    event.date = start_datetime.date()
                    event.time = start_datetime.time()
                else:
                    return jsonify({"error": "start alanı geçerli bir ISO datetime string değil"}), 400
            except ValueError as e:
                app.logger.error(f"start alanı ayrıştırma hatası: {e}")
                return jsonify({"error": f"start alanı formatı hatalı: {e}"}), 400
        
        # Diğer alanları güncelle
        if 'title' in data:
            event.title = data['title']
            
        if 'event_type' in data:
            event.event_type = data['event_type']
            
        if 'description' in data:
            event.description = data['description'] or ''  # Boş string yerine None olmayacak
            
        if 'assigned_to' in data:
            event.assigned_to = data['assigned_to'] or None
            
        if 'is_completed' in data:
            event.is_completed = data.get('is_completed', False)
        
        # Time field'ını ayrı olarak güncelle (eğer date ile birlikte gelmemişse)
        if 'time' in data and 'date' not in data:
            try:
                if data.get('event_type') == 'gunluk-kayit':
                    event_time = datetime.strptime('00:00', '%H:%M').time()
                else:
                    # Eğer time boş, None veya boş string ise varsayılan değer ata
                    time_str = data.get('time', '00:00')
                    if not time_str or not str(time_str).strip() or time_str == 'None':
                        time_str = '00:00'
                    event_time = datetime.strptime(str(time_str), '%H:%M').time()
                
                event.time = event_time
            except ValueError as e:
                app.logger.error(f"Time field ayrıştırma hatası: {e}")
                return jsonify({"error": f"Time field formatı hatalı: {e}"}), 400
        
        # Duruşma bilgilerini güncelle
        if event.event_type in ['durusma', 'e-durusma']:
            if 'file_type' in data:
                event.file_type = data['file_type']
                
            if 'courthouse' in data:
                event.courthouse = data['courthouse']
                
            if 'department' in data:
                event.department = data['department']
                
            # Eğer duruşma bilgileri eksikse ve gerekli bir alanda da varsa
            required_fields = ['file_type', 'courthouse', 'department']
            missing_fields = []
            
            for field in required_fields:
                if getattr(event, field) is None:
                    # Veri içinde varsa al
                    if field in data and data[field]:
                        setattr(event, field, data[field])
                    # else: # Eksikse hata vermek yerine boş bırakabiliriz
                    #     missing_fields.append(field)
            
            # if missing_fields:
            #     app.logger.warning(f"Duruşma için eksik alanlar: {missing_fields}")
                
            # --- OTOMATİK AÇIKLAMA OLUŞTURMA KISMI KALDIRILDI ---
            # Kullanıcı tarafından girilen açıklama varsa onu kullan, yoksa standart oluştur
            # if not event.description or (data.get('description') and data['description'] != event.description):
            #     if data.get('description'):
            #         event.description = data['description']
            #     else:
            #         # Dosya bilgilerini içeren standart açıklama oluştur
            #         event.description = f"Dosya Türü: {event.file_type or '-'}\nAdliye: {event.courthouse or '-'}\nBirim: {event.department or '-'}"
        else:
            # Duruşma değilse bu alanları temizle
            event.file_type = None
            event.courthouse = None
            event.department = None
        
        # Günlük Kayıt bilgilerini güncelle
        if event.event_type == 'gunluk-kayit':
            if 'muvekkil_isim' in data:
                event.muvekkil_isim = data['muvekkil_isim']
                
            if 'muvekkil_telefon' in data:
                event.muvekkil_telefon = data['muvekkil_telefon']
                
            # Günlük Kayıt için time'ı 00:00 yap (NULL yerine)
            event.time = datetime.strptime('00:00', '%H:%M').time()
            event.assigned_to = None
            event.is_completed = False
        else:
            # Günlük Kayıt değilse bu alanları temizle
            event.muvekkil_isim = None
            event.muvekkil_telefon = None
        
        # Değişiklikleri kaydet
        db.session.commit()
        
        # Duruşma/E-Duruşma güncellendiğinde dosyaya geri senkronizasyon
        if event.event_type in ['durusma', 'e-durusma'] and event.case_id:
            try:
                case_file = CaseFile.query.get(event.case_id)
                if case_file:
                    # Dosyadaki duruşma tarih ve saatini güncelle
                    case_file.next_hearing = event.date
                    case_file.hearing_time = event.time.strftime('%H:%M') if event.time else None
                    case_file.hearing_type = event.event_type
                    
                    # Dosya bilgilerini de güncelle (eğer takvimde değişmişse)
                    if event.file_type:
                        case_file.file_type = event.file_type
                    if event.courthouse:
                        case_file.courthouse = event.courthouse
                    if event.department:
                        case_file.department = event.department
                    
                    db.session.commit()
                    
                    # Log kaydı
                    log_activity(
                        activity_type='durusma_takvimden_dosyaya_senkronizasyon',
                        description=f"Takvimdeki duruşma güncellemesi dosyaya yansıtıldı: {case_file.client_name} - {event.date.strftime('%d.%m.%Y')} {event.time.strftime('%H:%M') if event.time else ''}",
                        user_id=current_user.id,
                        case_id=event.case_id,
                        related_event_id=event.id
                    )
                    
                    app.logger.info(f"Duruşma dosyaya senkronize edildi: Case ID {event.case_id}")
            except Exception as e:
                app.logger.error(f"Dosya senkronizasyon hatası: {str(e)}")
        
        # E-posta bildirimi gönder (atanan kişi değiştiğinde)
        if 'assigned_to' in data and data['assigned_to'] != old_values.get('assigned_to'):
            if event.assigned_to:
                try:
                    # Atanan kişiyi bul
                    assigned_user = User.query.filter_by(is_approved=True).filter(
                        User.first_name + ' ' + User.last_name == event.assigned_to.replace('Av. ', '').replace('Stj. Av. ', '').replace('Asst. ', '').replace('Ulşm. ', '').replace('Tkp El. ', '')
                    ).first()
                    
                    if not assigned_user:
                        # Tam isim eşleşmesi yoksa, full_name ile dene
                        for user in User.query.filter_by(is_approved=True).all():
                            if user.get_full_name() == event.assigned_to:
                                assigned_user = user
                                break
                    
                    if assigned_user:
                        send_calendar_event_assignment_email(
                            user_email=assigned_user.email,
                            user_name=assigned_user.get_full_name(),
                            event_title=event.title,
                            event_date=event.date.strftime('%d.%m.%Y'),
                            event_time=event.time.strftime('%H:%M'),
                            event_type=event.event_type,
                            assigned_by_name=current_user.get_full_name(),
                            courthouse=event.courthouse,
                            department=event.department,
                            description=event.description
                        )
                        app.logger.info(f"Güncelleme atama e-postası gönderildi: {assigned_user.email}")
                    else:
                        app.logger.warning(f"Atanan kullanıcı bulunamadı: {event.assigned_to}")
                except Exception as e:
                    app.logger.error(f"E-posta gönderme hatası: {str(e)}")
        
        # Değişiklikleri loglama
        changes = []
        for key, old_value in old_values.items():
            new_value = getattr(event, key)

            # Doğrudan değerleri karşılaştır
            if old_value != new_value:
                # Log için değerleri formatla (varsayılan olarak string)
                formatted_log_old = str(old_value) if old_value is not None else "None"
                formatted_log_new = str(new_value) if new_value is not None else "None"

                # new_value formatlama (eğer tarih/saat tipi ise)
                if new_value is not None:
                    if isinstance(new_value, datetime):
                        formatted_log_new = new_value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(new_value, date):
                        formatted_log_new = new_value.strftime('%Y-%m-%d')
                    elif isinstance(new_value, time):
                        formatted_log_new = new_value.strftime('%H:%M')

                # old_value formatlama (eğer tarih/saat tipi ise)
                if old_value is not None:
                    if isinstance(old_value, datetime):
                        formatted_log_old = old_value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(old_value, date):
                        formatted_log_old = old_value.strftime('%Y-%m-%d')
                    elif isinstance(old_value, time):
                        formatted_log_old = old_value.strftime('%H:%M')

                changes.append(f"{key}: {formatted_log_old} -> {formatted_log_new}")
        
        if changes:
            log = ActivityLog(
                activity_type='etkinlik_duzenleme',
                description=f'Etkinlik düzenlendi: {event.title}',
                details={
                    'etkinlik_id': event.id,
                    'degisiklikler': changes
                },
                user_id=current_user.id,
                related_event_id=event.id
            )
            db.session.add(log)
            db.session.commit()
        
        app.logger.info(f"Etkinlik (ID: {event_id}) başarıyla güncellendi. Değişiklikler: {changes}")
        return jsonify({
            "success": True,
            "message": "Etkinlik başarıyla güncellendi",
            "event": {
                "id": event.id,
                "title": event.title,
                "date": event.date.strftime('%Y-%m-%d') if event.date else None,
                "time": event.time.strftime('%H:%M') if event.time else None,
                "event_type": event.event_type,
                "description": event.description,
                "assigned_to": event.assigned_to,
                "is_completed": event.is_completed,
                "file_type": event.file_type,
                "courthouse": event.courthouse,
                "department": event.department
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Etkinlik güncelleme hatası (ID: {data.get('id')}): {str(e)}", exc_info=True)
        # ÖNEMLİ: Hata durumunda HTML yerine JSON döndürdüğümüzden emin olalım.
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500

@app.route('/delete_event/<int:event_id>', methods=['DELETE', 'POST'])
@login_required
@permission_required('etkinlik_sil')
@csrf.exempt
def delete_event(event_id):
    try:
        event = CalendarEvent.query.get_or_404(event_id)
        
        # Log kaydı
        log = ActivityLog(
            activity_type='etkinlik_silme',
            description=f'Etkinlik silindi: {event.title}',
            details={
                'baslik': event.title,
                'tarih': event.date.strftime('%Y-%m-%d'),
                'saat': event.time.strftime('%H:%M'),
                'tur': event.event_type,
                'aciklama': event.description
            },
            user_id=current_user.id
        )
        
        db.session.add(log)
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Etkinlik başarıyla silindi'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Etkinlik silme hatası: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/get_event_details/<int:event_id>')
@login_required
def get_event_details(event_id):
    try:
        event = CalendarEvent.query.get_or_404(event_id)
        
        event_data = {
            "id": event.id,
            "title": event.title,
            "date": event.date.strftime('%Y-%m-%d') if event.date else None,
            "time": event.time.strftime('%H:%M') if event.time else None,
            "event_type": event.event_type,
            "description": event.description,
            "assigned_to": event.assigned_to,
            "is_completed": event.is_completed,
            "file_type": event.file_type,
            "courthouse": event.courthouse,
            "department": event.department
        }
        
        return jsonify(event_data)
    except Exception as e:
        app.logger.error(f"Etkinlik detayları getirme hatası: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/add_expense/<int:case_id>', methods=['POST'])
def add_expense(case_id):
    try:
        data = request.get_json()
        case_file = CaseFile.query.get_or_404(case_id)
        
        new_expense = Expense(
            case_id=case_id,
            expense_type=data['expense_type'],
            amount=data['amount'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            is_paid=data['is_paid'],
            description=data.get('description', '')
        )
        
        db.session.add(new_expense)
        db.session.commit()
        
        log_activity(
            activity_type='masraf_ekleme',
            description=f"Yeni masraf eklendi: {case_file.client_name} - {data['expense_type']} (₺{data['amount']})",
            user_id=1,
            case_id=case_id
        )
        
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e))

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@csrf.exempt
def delete_expense(expense_id):
    try:
        expense = db.session.get(Expense, expense_id)
        if expense:
            db.session.delete(expense)
            db.session.commit()
            return jsonify(success=True)
        return jsonify(success=False, message="Masraf bulunamadı")
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e))

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'udf', 'tiff', 'tif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_document/<int:case_id>', methods=['POST'])
@csrf.exempt
def upload_document(case_id):
    try:
        if 'document' not in request.files:
            return jsonify(success=False, message="Dosya seçilmedi")

        file = request.files['document']
        document_type = request.form.get('document_type')
        custom_name = request.form.get('document_name')
        
        if not document_type:
            return jsonify(success=False, message="Belge türü seçilmedi")

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower()
            
            # Özel isim varsa kullan, yoksa orijinal dosya adını kullan
            display_name = custom_name if custom_name else original_filename.rsplit('.', 1)[0]
            
            # Benzersiz dosya adı oluştur
            unique_filename = f"{case_id}_{int(pytime.time())}_{original_filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'documents', unique_filename)
            
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'documents'), exist_ok=True)
            file.save(file_path)
            
            # PDF path'i başlangıçta None olarak ayarla
            pdf_path = None
            
            # UDF, DOC veya DOCX dosyası ise otomatik PDF dönüşümü yap
            if file_ext.lower() in ['udf', 'doc', 'docx']:
                print(f"{file_ext.upper()} dosyası yüklendi, PDF'e dönüştürülüyor: {file_path}")
                try:
                    pdf_path = convert_udf_to_pdf(file_path)
                    if pdf_path:
                        print(f"Dönüştürme başarılı: {pdf_path}")
                        
                        # PDF dosyasını saklamak için benzersiz isim oluştur
                        pdf_filename = f"{case_id}_{int(pytime.time())}_converted_{display_name}.pdf"
                        permanent_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
                        
                        # Geçici PDF dosyasını kalıcı konuma taşı
                        shutil.copy(pdf_path, permanent_pdf_path)
                        
                        # Geçici dosyayı temizle
                        try:
                            os.remove(pdf_path)
                        except:
                            pass
                        
                        # PDF path'i güncelle
                        pdf_path = pdf_filename
                    else:
                        print(f"Dönüştürme başarısız oldu")
                except Exception as e:
                    print(f"PDF dönüştürme hatası: {str(e)}")
            
            new_document = Document(
                case_id=case_id,
                document_type=document_type,
                filename=f"{display_name}.{file_ext}",  # Görünen isim
                filepath=f"documents/{unique_filename}",  # Gerçek dosya yolu
                upload_date=datetime.now(),
                user_id=current_user.id if current_user.is_authenticated else 1,
                pdf_version=pdf_path  # PDF versiyonu varsa kaydet
            )
            
            db.session.add(new_document)
            db.session.commit()
            
            # İşlem logu ekle
            case_file = CaseFile.query.get(case_id)
            log_activity(
                activity_type='belge_yukleme',
                description=f"Yeni belge yüklendi: {case_file.client_name} - {document_type} ({custom_name or file.filename})",
                user_id=current_user.id if current_user.is_authenticated else 1,
                case_id=case_id
            )
            
            return jsonify(success=True)
            
        return jsonify(success=False, message="Geçersiz dosya türü")
    except Exception as e:
        db.session.rollback()
        print(f"Upload error: {str(e)}")
        return jsonify(success=False, message=str(e))

@app.route('/get_documents/<int:case_id>')
def get_documents(case_id):
    documents = Document.query.filter_by(case_id=case_id).all()
    return jsonify(success=True, documents=[{
        'id': doc.id,
        'filename': doc.filename,
        'document_type': doc.document_type,
        'upload_date': doc.upload_date.strftime('%d.%m.%Y')
    } for doc in documents])

@app.route('/download_document/<int:document_id>')
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
    
    # Backward compatibility: Eski format kontrol et
    if not os.path.exists(filepath):
        # Eski format: documents klasöründe sadece filename
        old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'documents', document.filepath)
        if os.path.exists(old_filepath):
            filepath = old_filepath
    
    return send_file(filepath, as_attachment=True, download_name=document.filename)

@app.route('/delete_document/<int:document_id>', methods=['POST'])
@login_required
@permission_required('dosya_sil')
@csrf.exempt
def delete_document(document_id):
    try:
        document = Document.query.get_or_404(document_id)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
        
        # Backward compatibility: Eski format kontrol et
        if not os.path.exists(file_path):
            # Eski format: documents klasöründe sadece filename
            old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'documents', document.filepath)
            if os.path.exists(old_filepath):
                file_path = old_filepath
        
        # Dosyayı sil
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Veritabanından sil
        db.session.delete(document)
        db.session.commit()
        
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))

def convert_udf_to_pdf(input_path):
    try:
        # Dosya uzantısını al
        _, ext = os.path.splitext(input_path)
        ext = ext.lower()
        
        # Geçici PDF dosyası için path oluştur
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            output_path = tmp_pdf.name
        
        print(f"Dönüştürme başlatılıyor: {input_path} -> {output_path}")
        print(f"Dosya uzantısı: {ext}")
        
        # 1. ÖZEL YÖNTEM: UDF dosyaları için UYAP Editör CLI komutunu dene
        if ext == '.udf':
            try:
                # UYAP Editör'ün muhtemel konumları
                uyap_editor_paths = [
                    r"C:\Program Files\UYAP\UYAP Editor\UYAPEditor.exe",
                    r"C:\Program Files (x86)\UYAP\UYAP Editor\UYAPEditor.exe",
                    r"C:\UYAP\UYAP Editor\UYAPEditor.exe"
                ]
                
                uyap_exe = None
                for path in uyap_editor_paths:
                    if os.path.exists(path):
                        uyap_exe = path
                        break
                
                if uyap_exe:
                    print(f"UYAP Editör bulundu: {uyap_exe}")
                    print("UYAP Editör ile dönüştürme deneniyor...")
                    
                    # Çıktı dizinini hazırla
                    output_dir = os.path.dirname(output_path)
                    
                    # UYAP Editör export komut satırı kullanımı
                    # Not: Bu komut satırı özellikleri UYAPEditor'ün gerçekte böyle bir özelliği
                    # olduğunu varsayar. Gerçek komut satırı seçenekleri farklı olabilir.
                    result = subprocess.run(
                        [uyap_exe, "--export-pdf", input_path, "--output", output_path],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    # LibreOffice çıktı dosyasının adını belirle
                    input_filename = os.path.basename(input_path)
                    input_name, _ = os.path.splitext(input_filename)
                    lo_output_path = os.path.join(output_dir, f"{input_name}.pdf")
                    
                    # Çıktı dosyasını kontrol et
                    if os.path.exists(lo_output_path) and os.path.getsize(lo_output_path) > 0:
                        print(f"LibreOffice ile dönüştürme başarılı: {lo_output_path}")
                        
                        # Çıktıyı istenen yere taşı
                        if lo_output_path != output_path:
                            shutil.move(lo_output_path, output_path)
                            print(f"PDF dosyası taşındı: {lo_output_path} -> {output_path}")
                            
                        return output_path
                    else:
                        print("LibreOffice çıktı dosyası oluşturulamadı veya boş")
                        if result.stderr:
                            print(f"LibreOffice stderr: {result.stderr}")
                else:
                    print("LibreOffice bulunamadı")
            except subprocess.CalledProcessError as e:
                print(f"LibreOffice çalıştırma hatası: {str(e)}")
                if hasattr(e, 'stderr') and e.stderr:
                    print(f"LibreOffice stderr: {e.stderr}")
            except subprocess.TimeoutExpired:
                print("LibreOffice zaman aşımına uğradı")
            except Exception as e:
                print(f"LibreOffice beklenmeyen hata: {str(e)}")
        
        # Her iki yöntem de başarısız oldu
        print("Tüm dönüştürme yöntemleri başarısız oldu")
        return None
            
    except Exception as e:
        print(f"Üst düzey bir hata oluştu: {str(e)}")
        # Çıktı dosyası oluşturulduysa temizle
        if 'output_path' in locals() and os.path.exists(output_path):
            try:
                os.remove(output_path)
                print(f"Geçici dosya temizlendi: {output_path}")
            except:
                pass
        return None

@app.route('/preview_document/<int:document_id>')
def preview_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Önce belgenin PDF sürümü var mı kontrol et
    if document.pdf_version:
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], document.pdf_version)
        if os.path.exists(pdf_path):
            print(f"Belge için hazır PDF sürümü kullanılıyor: {pdf_path}")
            return send_file(pdf_path, mimetype='application/pdf')
    
    # PDF sürümü yoksa, normal işleme devam et
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
    
    # Backward compatibility: Eski format kontrol et
    if not os.path.exists(filepath):
        # Eski format: documents klasöründe sadece filename
        old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'documents', document.filepath)
        if os.path.exists(old_filepath):
            filepath = old_filepath
        else:
            return "Dosya bulunamadı", 404

    _, extension = os.path.splitext(document.filepath)
    extension = extension.lower()

    # UDF dosyaları için özel görüntüleme sayfasına yönlendir
    if extension == '.udf':
        return redirect(url_for('preview_udf', document_id=document_id))

    # PDF dosyaları doğrudan gösterilir
    if extension == '.pdf':
        return send_file(filepath, mimetype='application/pdf')

    # Resim dosyaları doğrudan gösterilir
    elif extension in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp']:
        mimetype = f'image/{extension[1:]}' if extension != '.tif' else 'image/tiff'
        return send_file(filepath, mimetype=mimetype)

    # DOC ve DOCX dosyaları için önizleme
    elif extension in ['.doc', '.docx']:
        try:
            print(f"{extension} dosyası için PDF dönüşümü başlatılıyor...")
            pdf_path = convert_office_to_pdf(filepath)
            if pdf_path:
                # Dönüştürülmüş PDF dosyasını gönder
                response = send_file(pdf_path, mimetype='application/pdf')
                
                # Dönüştürme başarılı olduysa, PDF'i sonraki kullanımlar için kaydet
                try:
                    # PDF dosyasını saklamak için benzersiz isim oluştur
                    pdf_filename = f"{document.case_id}_{int(pytime.time())}_converted_{document.filename}.pdf"
                    permanent_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'documents',  pdf_filename)
                    
                    # Geçici PDF dosyasını kalıcı konuma kopyala
                    shutil.copy(pdf_path, permanent_pdf_path)
                    
                    # Veritabanında belgenin PDF sürümünü güncelle
                    document.pdf_version = pdf_filename
                    db.session.commit()
                    print(f"PDF sürümü kaydedildi: {pdf_filename}")
                except Exception as e:
                    print(f"PDF sürümü kaydedilirken hata: {str(e)}")
                
                return response
            else:
                # Dönüştürme başarısız olursa, dosyayı uygun MIME tipi ile görüntüle
                print(f"PDF dönüşümü başarısız oldu, {extension} dosyası görüntülenecek")
                
                if extension == '.doc':
                    # .doc için uygun MIME tipi
                    return send_file(filepath, mimetype='application/msword')
                else:
                    # .docx için uygun MIME tipi
                    return send_file(filepath, 
                                   mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        except Exception as e:
            print(f"{extension.upper()} önizleme hatası (docId: {document_id}): {e}")
            # Hata durumunda dosyayı indirmeye ver
            return send_file(filepath, as_attachment=True, download_name=document.filename)

    # Diğer dosya türleri için indirme işlemi
    else:
        return send_file(filepath, as_attachment=True, download_name=document.filename)

# Office belgelerini PDF'e dönüştüren yeni fonksiyon
def convert_office_to_pdf(input_path):
    """Office belgelerini (doc, docx) PDF'e dönüştürür"""
    if not os.path.exists(input_path):
        return None
    
    try:
        _, extension = os.path.splitext(input_path)
        extension = extension.lower()
        print(f"Dosya uzantısı: {extension}")
        
        if extension not in ['.doc', '.docx']:
            print("Bu uzantı desteklenmiyor.")
            return None
            
        # Çıktı için geçici dosya oluştur
        output_path = os.path.join(tempfile.gettempdir(), 
                                  f"temp_converted_{int(pytime.time())}.pdf")
        
        # 1. DOCX-PREVIEW modülünü kullanarak HTML'e dönüştür ve sonra PDF'e çevir
        if extension == '.docx':
            try:
                with open(input_path, 'rb') as f:
                    html_content = mammoth.convert_to_html(f).value
                
                # HTML içeriğinden PDF oluştur
                options = {
                    'page-size': 'A4',
                    'margin-top': '20mm',
                    'margin-right': '20mm',
                    'margin-bottom': '20mm',
                    'margin-left': '20mm',
                    'encoding': 'UTF-8',
                }
                
                pdfkit.from_string(html_content, output_path, options=options)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"mammoth ve pdfkit ile dönüştürme başarılı: {output_path}")
                    return output_path
            except Exception as e:
                print(f"mammoth ile dönüştürme hatası: {str(e)}")
        
        # 2. LibreOffice ile dönüştürmeyi dene
        try:
            soffice_path = None
            if os.name == 'nt':  # Windows
                # Windows'da olası LibreOffice konumları
                possible_paths = [
                    "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
                    "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
                    # Program Files dizininde arama
                    *glob.glob("C:\\Program Files\\*\\program\\soffice.exe"),
                    *glob.glob("C:\\Program Files (x86)\\*\\program\\soffice.exe"),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        soffice_path = path
                        break
            else:  # Linux/Mac
                # Linux/Mac'te soffice genellikle PATH içindedir
                soffice_path = "/usr/bin/soffice"
                
            if soffice_path and os.path.exists(soffice_path):
                # Geçici çalışma dizini oluştur
                temp_dir = tempfile.mkdtemp()
                
                # LibreOffice komutu
                cmd = [
                    soffice_path,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', temp_dir,
                    input_path
                ]
                
                print(f"LibreOffice komutu çalıştırılıyor: {' '.join(cmd)}")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    # Dönüştürülen dosyayı bul
                    base_name = os.path.basename(input_path)
                    base_name_without_ext = os.path.splitext(base_name)[0]
                    converted_path = os.path.join(temp_dir, f"{base_name_without_ext}.pdf")
                    
                    if os.path.exists(converted_path):
                        # Geçici konuma taşı
                        shutil.copy(converted_path, output_path)
                        # Geçici dizini temizle
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        
                        print(f"LibreOffice ile dönüştürme başarılı: {output_path}")
                        return output_path
                    else:
                        print(f"LibreOffice çıktı dosyası bulunamadı: {converted_path}")
                else:
                    print(f"LibreOffice hatası: {stderr.decode()}")
                
                # Geçici dizini temizle
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"LibreOffice ile dönüştürme hatası: {str(e)}")
        
        # Tüm dönüştürme yöntemleri başarısız oldu
        print("Tüm dönüştürme yöntemleri başarısız oldu")
        return None
    except Exception as e:
        print(f"Dönüştürme sırasında hata: {str(e)}")
        return None

@app.route('/get_udf_manifest/<int:document_id>')
def get_udf_manifest(document_id):
    document = Document.query.get_or_404(document_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
    
    # UDF dosyası için IIIF manifest oluştur
    manifest = {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@type": "sc:Manifest",
        "@id": f"/get_udf_manifest/{document_id}",
        "label": document.filename,
        "sequences": [{
            "@type": "sc:Sequence",
            "canvases": [{
                "@type": "sc:Canvas",
                "@id": f"/preview_document/{document_id}",
                "label": "p. 1",
                "height": 1000,
                "width": 1000,
                "images": [{
                    "@type": "oa:Annotation",
                    "motivation": "sc:painting",
                    "resource": {
                        "@id": f"/preview_document/{document_id}",
                        "@type": "dctypes:Image",
                        "format": "application/udf",
                        "height": 1000,
                        "width": 1000,
                    },
                    "on": f"/preview_document/{document_id}"
                }]
            }]
        }]
    }
    
    return jsonify(manifest)

@app.route('/sync_hearing_to_calendar', methods=['POST'])
def sync_hearing_to_calendar():
    try:
        data = request.get_json()
        print(f"Takvim senkronizasyonu isteği alındı: {data}")
        
        case_id = data.get('case_id')
        hearing_date_str = data.get('hearing_date') # Tarih string olarak alınır
        hearing_time_str = data.get('hearing_time', '09:00') # Saat string olarak alınır
        status = data.get('status')
        hearing_type = data.get('hearing_type', 'durusma').lower()
        
        print(f"Takvim senkronizasyonu parametreleri: case_id={case_id}, date={hearing_date_str}, time={hearing_time_str}, status={status}, type={hearing_type}")
        
        case_file = CaseFile.query.get(case_id)
        if not case_file:
            print(f"Dosya bulunamadı: case_id={case_id}")
            return jsonify(success=False, message="Dosya bulunamadı")
            
        print(f"Dosya bulundu: {case_file.client_name} - {case_file.case_number}")

        existing_event = CalendarEvent.query.filter_by(
            case_id=case_id,
            # event_type='durusma' # Eski sorgu, hem durusma hem e-durusma olabilir
        ).filter(CalendarEvent.event_type.in_(['durusma', 'e-durusma'])).first()

        if status == 'Kapalı' or not hearing_date_str:
            if existing_event:
                db.session.delete(existing_event)
                db.session.commit()
                log_activity(
                    activity_type='durusma_silme_takvimden',
                    description=f"Takvimden duruşma kaydı silindi (dosya kapalı veya tarih yok): {case_file.client_name}",
                    user_id=current_user.id,
                    case_id=case_id,
                    related_event_id=existing_event.id
                )
            return jsonify(success=True, message="Duruşma takvimden kaldırıldı.")

        event_date = datetime.strptime(hearing_date_str, '%Y-%m-%d').date()
        event_time = datetime.strptime(hearing_time_str, '%H:%M').time()
        
        event_title = f"{case_file.client_name} ({case_file.year}/{case_file.case_number})"
        event_description = '' # Açıklamayı boş bırak

        if existing_event:
            # Tarih değişmişse, eski etkinliği sil ve yenisini oluştur
            if existing_event.date != event_date:
                # Mevcut (eski tarihli) etkinliği sil
                old_event_id = existing_event.id
                db.session.delete(existing_event)
                # Değişikliği veritabanına hemen yansıt ki yeni event eklenebilsin
                # db.session.commit() # Bu commit burada sorun yaratabilir, yeni event eklenmeden silinmemeli
                                    # Ya da silme logunu burada atıp, yeni eklendikten sonra commit etmeli.
                                    # Şimdilik logu atıp, genel commit'e bırakıyorum.
                log_activity(
                    activity_type='durusma_tarih_degisikligi_takvimde',
                    description=f"Takvimde duruşma tarihi değişti, eski silindi: {case_file.client_name}",
                    user_id=current_user.id,
                    case_id=case_id,
                    related_event_id=old_event_id # Silinen eventin ID'si
                )
                # Yeni etkinlik oluştur (aşağıdaki blokta yapılacak)
                existing_event = None # Yeniden oluşturulması için null yap
            else:
                # Tarih aynı, sadece saat veya tür değişmiş olabilir. Mevcut etkinliği güncelle.
                existing_event.time = event_time
                existing_event.title = event_title # Başlık saat veya tür değiştiyse güncellenmeli
                existing_event.event_type = hearing_type 
                existing_event.description = event_description # Güncellerken de boş olacak
                existing_event.courthouse = case_file.courthouse
                existing_event.department = case_file.department
                existing_event.file_type = case_file.file_type
                # Diğer alanlar (örn. user_id, case_id) zaten doğru olmalı
                
                log_activity(
                    activity_type='durusma_saat_tur_guncelleme_takvimde',
                    description=f"Takvimde duruşma saati/türü güncellendi: {case_file.client_name} - {event_date.strftime('%d.%m.%Y')} {event_time.strftime('%H:%M')}",
                    user_id=current_user.id,
                    case_id=case_id,
                    related_event_id=existing_event.id
                )
                db.session.commit()
                return jsonify(success=True, message="Duruşma takvimde güncellendi.")

        # Yeni etkinlik oluşturma (ya hiç yoktu ya da tarihi değiştiği için silindi)
        if not existing_event: # Bu kontrol, yukarıda tarih değişikliği durumunda existing_event'in null yapılmasıyla çalışır.
            new_event = CalendarEvent(
                title=event_title,
                date=event_date,
                time=event_time,
                event_type=hearing_type,
                description=event_description, # Yeni eklerken de boş olacak
                user_id=current_user.id, # Yetkili kullanıcı ID'si
                case_id=case_id,
                courthouse=case_file.courthouse,
                department=case_file.department,
                file_type=case_file.file_type
            )
            db.session.add(new_event)
            db.session.commit() # Yeni event eklendikten sonra commit et
            log_activity(
                activity_type='durusma_ekleme_takvime',
                description=f"Takvime yeni duruşma eklendi: {case_file.client_name} - {event_date.strftime('%d.%m.%Y')} {event_time.strftime('%H:%M')}",
                user_id=current_user.id,
                case_id=case_id,
                related_event_id=new_event.id
            )
            return jsonify(success=True, message="Duruşma takvime eklendi.")
        
        # Eğer buraya gelinirse bir mantık hatası vardır, normalde ya güncellenmeli ya da yeni eklenmeliydi.
        # Ancak mevcut existing_event varsa ve tarihi aynıysa zaten yukarıda güncellenip return edilmiş olmalıydı.
        # Bu yüzden bu jsonify teorik olarak erişilmez olmalı.
        return jsonify(success=False, message="Takvim senkronizasyonunda bilinmeyen bir durum oluştu.") 

    except Exception as e:
        db.session.rollback()
        print(f"Takvim senkronizasyon hatası: {str(e)}")
        return jsonify(success=False, message=f"Takvim senkronizasyonu sırasında bir hata oluştu: {str(e)}"), 500

@app.route('/get_document_info/<int:document_id>')
def get_document_info(document_id):
    try:
        document = Document.query.get_or_404(document_id)
        # Orijinal dosya adını döndür
        return jsonify({
            'success': True,
            'original_filename': document.filepath  # Burada orijinal dosya adı saklanıyor
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/update_description/<int:case_id>', methods=['POST'])
@login_required
@permission_required('dosya_duzenle')
def update_description(case_id):
    try:
        data = request.get_json()
        case_file = db.session.get(CaseFile, case_id)
        if case_file:
            case_file.description = data.get('description', '')
            db.session.commit()
            return jsonify(success=True)
        return jsonify(success=False, message="Dosya bulunamadı")
    except Exception as e:
        print(f"Hata: {str(e)}")
        db.session.rollback()
        return jsonify(success=False, message=str(e))

@app.route('/update_expense/<int:expense_id>', methods=['POST'])
def update_expense(expense_id):
    try:
        data = request.get_json()
        expense = Expense.query.get_or_404(expense_id)
        
        # Tarih formatını kontrol et
        try:
            expense_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify(success=False, message="Geçersiz tarih formatı")
        
        expense.expense_type = data['expense_type']
        expense.amount = data['amount']
        expense.date = expense_date
        expense.is_paid = data['is_paid']
        expense.description = data['description']
        
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e))

@app.route('/iletisim')
@login_required
@permission_required('iletisim')
def iletisim():
    return render_template('iletisim.html')

@app.route('/send_contact_mail', methods=['POST'])
def send_contact_mail():
    try:
        data = request.get_json()
        
        # Türkçe karakter desteği için UTF-8 encoding
        subject = 'Yeni İletişim Formu Mesajı'
        body = f"""
        Yeni bir iletişim formu mesajı alındı:
        
        Gönderen: {data['name']}
        E-posta: {data['email']}
        
        Mesaj:
        {data['message']}
        """
        
        # E-postayı gönder - Güvenli gönderim
        email_sent = False
        
        # Önce smtplib dene (eğer mümkünse)
        try:
            from email_utils import send_email_with_smtplib
            success, result_message = send_email_with_smtplib(
                app.config['MAIL_USERNAME'], 
                subject, 
                body, 
                is_html=False
            )
            if success:
                email_sent = True
                logger.info("İletişim formu e-postası smtplib ile gönderildi")
        except Exception as e:
            logger.warning(f"smtplib ile iletişim formu e-postası gönderilemedi: {e}")
        
        # Başarısız olduysa Flask-Mail dene
        if not email_sent:
            try:
                # Subject ve body'yi UTF-8 olarak encode et
                if isinstance(subject, str):
                    subject = subject.encode('utf-8').decode('utf-8')
                if isinstance(body, str):
                    body = body.encode('utf-8').decode('utf-8')
                
                msg = Message(
                    subject=subject,
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[app.config['MAIL_USERNAME']],
                    body=body,
                    charset='utf-8'
                )
                
                # Message header'larını UTF-8 olarak ayarla
                msg.extra_headers = {'Content-Type': 'text/plain; charset=utf-8'}
                
                mail.send(msg)
                email_sent = True
                logger.info("İletişim formu e-postası Flask-Mail ile gönderildi")
            except Exception as e:
                logger.error(f"İletişim formu e-postası Flask-Mail ile de gönderilemedi: {e}")
                raise Exception(f"E-posta gönderim hatası: {str(e)}")
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))

def get_current_rates():
    try:
        # TCMB'den güncel faiz oranlarını çek
        url = "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/Reeskont+ve+Avans+Faiz+Oranlari"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Faiz oranlarını parse et
        rates = {
            'reeskont': float(soup.find('reeskont').text),
            'avans': float(soup.find('avans').text),
            'temerrut': float(soup.find('temerrut').text),
            'yasal': 24.0,  # Yasal faiz oranı
            'mevduat': 45.0  # En yüksek mevduat faizi
        }
        return rates
    except:
        # Hata durumunda varsayılan değerleri döndür
        return {
            'reeskont': 13.75,
            'avans': 14.75,
            'temerrut': 19.0,
            'yasal': 24.0,
            'mevduat': 45.0
        }

@app.route('/hesaplamalar/<type>')
@login_required  
def hesaplamalar(type):
    # Her hesaplama türü için spesifik yetki kontrolleri
    permission_map = {
        'faiz': 'faiz_hesaplama',
        'harc': 'harc_hesaplama', 
        'isci': 'isci_hesaplama',
        'vekalet': 'vekalet_hesaplama',
        'ceza_infaz': 'ceza_infaz_hesaplama'
    }
    
    required_permission = permission_map.get(type)
    if not required_permission:
        abort(404)
    
    # Yetki kontrolü
    if not current_user.has_permission(required_permission):
        flash(f'Bu işlemi yapmak için gerekli yetkiye sahip değilsiniz. {required_permission} yetkisi gereklidir.', 'error')
        return redirect(url_for('anasayfa'))
    
    if type == 'faiz':
        current_rates = get_current_rates()
        return render_template('faiz_hesaplama.html', rates=current_rates)
    elif type == 'harc':
        return render_template('harc_hesaplama.html')
    elif type == 'isci':
        return render_template('isci_alacagi_hesaplama.html')
    elif type == 'vekalet':
        return render_template('vekalet_hesaplama.html')
    elif type == 'ceza_infaz':
        return render_template('ceza_infaz_hesaplama.html')

@app.route("/isci-alacagi-hesaplama")
def isci_alacagi_hesaplama():
    return render_template("isci_alacagi_hesaplama.html")

@app.route('/update_theme_preference', methods=['POST'])
@login_required
@csrf.exempt
def update_theme_preference():
    try:
        data = request.get_json()
        theme = data.get('theme')
        
        if theme in ['light', 'dark']:
            user = User.query.get(current_user.id)
            user.theme_preference = theme
            db.session.commit()
            return jsonify(success=True)
        
        return jsonify(success=False, message="Geçersiz tema tercihi")
    except Exception as e:
        return jsonify(success=False, message=str(e))

@app.route('/update_settings', methods=['POST'])
@login_required
@csrf.exempt
def update_settings():
    try:
        data = request.get_json()
        user = User.query.get(current_user.id)
        
        if 'fontSize' in data:
            user.font_size = data['fontSize']
            
        if 'theme' in data:
            user.theme_preference = data['theme']
            
        # Bildirim ayarları ve 2FA ayarları
        if 'emailNotifications' in data or 'systemNotifications' in data or 'twoFactorEnabled' in data:
            # User modelinde böyle alanlar yok, permissions JSON'ında saklayabiliriz
            if not user.permissions:
                user.permissions = {}
            
            if 'emailNotifications' in data:
                user.permissions['email_notifications'] = data['emailNotifications']
            
            if 'systemNotifications' in data:
                user.permissions['system_notifications'] = data['systemNotifications']
                
            if 'twoFactorEnabled' in data:
                user.permissions['two_factor_auth'] = data['twoFactorEnabled']
            
            # JSON field değişikliğini SQLAlchemy'ye bildir
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(user, 'permissions')
        
        db.session.commit()
        
        # Log oluştur
        log_activity(
            activity_type='ayar_guncelleme',
            description='Kullanıcı ayarları güncellendi',
            user_id=current_user.id,
            details=data
        )
        
        return jsonify({
            'success': True,
            'message': 'Ayarlar başarıyla güncellendi'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/get_user_settings', methods=['GET'])
@login_required
def get_user_settings():
    """Kullanıcının mevcut ayarlarını getir"""
    try:
        user = User.query.get(current_user.id)
        
        # Kullanıcının mevcut ayarları
        settings = {
            'theme': user.theme_preference or 'light',
            'fontSize': user.font_size or 'medium',
            'emailNotifications': user.permissions.get('email_notifications', True) if user.permissions else True,
            'systemNotifications': user.permissions.get('system_notifications', True) if user.permissions else True,
            'twoFactorEnabled': user.permissions.get('two_factor_auth', False) if user.permissions else False
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500



@app.route('/veritabani_yonetimi')
@login_required
@permission_required('veritabani_yonetimi')
def veritabani_yonetimi():
    """Veritabanı yönetimi sayfası - Tüm sistem tablolarını yönet"""
    # Veritabanı istatistikleri - Tüm tabloların kayıt sayıları
    stats = {
        # Temel istatistikler
        'kullanici_sayisi': User.query.count(),
        'onaysiz_kullanici_sayisi': User.query.filter_by(is_approved=False).count(),
        'dosya_sayisi': CaseFile.query.count(),
        'aktif_dosya_sayisi': CaseFile.query.filter_by(status='Aktif').count(),
        'etkinlik_sayisi': CalendarEvent.query.count(),
        'duyuru_sayisi': Announcement.query.count(),
        
        # Detaylı tablo istatistikleri
        'odeme_sayisi': Client.query.count(),  # Müşteri ödemeler tablosu
        'belge_sayisi': Document.query.count(),
        'masraf_sayisi': Expense.query.count(),
        'bildirim_sayisi': Notification.query.count(),
        'aktivite_sayisi': ActivityLog.query.count(),
        
        # İşçi ve işgören tabloları
        'isci_gorusme_sayisi': IsciGorusmeTutanagi.query.count(),
        'worker_interview_sayisi': WorkerInterview.query.count(),
        
        # Dilekçe ve sözleşme tabloları
        'ornek_dilekce_sayisi': OrnekDilekce.query.count(),
        'ornek_sozlesme_sayisi': OrnekSozlesme.query.count(),
        'dilekce_kategori_sayisi': DilekceKategori.query.count(),
        
        # Ödeme tablosu (Client tablosu müşteriler için kullanılıyor)
        'musteri_sayisi': Client.query.count(),
        'payment_sayisi': Payment.query.count() if hasattr(globals(), 'Payment') else 0,
    }
    
    # Son aktiviteler
    try:
        recent_activities_raw = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
        recent_activities = []
        for activity in recent_activities_raw:
            # Timestamp'i tamamen formatlanmış string olarak hazırla
            if activity.timestamp:
                try:
                    if hasattr(activity.timestamp, 'tzinfo') and activity.timestamp.tzinfo is not None:
                        # Timezone aware datetime - timezone'u kaldır ve formatla
                        naive_timestamp = activity.timestamp.replace(tzinfo=None)
                        activity.formatted_timestamp_str = naive_timestamp.strftime('%d.%m.%Y %H:%M')
                    else:
                        # Naive datetime (eski UTC kayıtlar) - Türkiye saatine çevir
                        utc_time = activity.timestamp.replace(tzinfo=timezone.utc)
                        turkey_tz = timezone(timedelta(hours=3))
                        turkey_time = utc_time.astimezone(turkey_tz).replace(tzinfo=None)
                        activity.formatted_timestamp_str = turkey_time.strftime('%d.%m.%Y %H:%M')
                except Exception as e:
                    app.logger.error(f"Timestamp formatlamada hata: {str(e)} - {activity.timestamp}")
                    activity.formatted_timestamp_str = 'Format hatası'
            else:
                activity.formatted_timestamp_str = 'Tarih yok'
            recent_activities.append(activity)
    except Exception as e:
        app.logger.error(f"Recent activities yüklenirken hata: {str(e)}")
        recent_activities = []
    
    return render_template('veritabani_yonetimi.html', 
                         stats=stats, 
                         recent_activities=recent_activities)

@app.route('/api/veritabani/temizle', methods=['POST'])
@login_required
@permission_required('veritabani_yonetimi')
def api_veritabani_temizle():
    """Veritabanını temizleme işlemleri"""
    try:
        data = request.get_json()
        temizlik_turu = data.get('temizlik_turu')
        
        if temizlik_turu == 'eski_loglar':
            # 30 günden eski logları sil
            cutoff_date = datetime.now() - timedelta(days=30)
            deleted_count = ActivityLog.query.filter(ActivityLog.timestamp < cutoff_date).delete()
            db.session.commit()
            log_activity('Veritabanı Temizlik', f'{deleted_count} eski log kaydı silindi', current_user.id)
            return jsonify({'success': True, 'message': f'{deleted_count} eski log kaydı silindi'})
            
        elif temizlik_turu == 'onaysiz_kullanicilar':
            # 7 günden eski onaysız kullanıcıları sil
            cutoff_date = datetime.now() - timedelta(days=7)
            deleted_count = User.query.filter(
                User.is_approved == False,
                User.created_at < cutoff_date
            ).delete()
            db.session.commit()
            log_activity('Veritabanı Temizlik', f'{deleted_count} onaysız kullanıcı silindi', current_user.id)
            return jsonify({'success': True, 'message': f'{deleted_count} onaysız kullanıcı silindi'})
            
        elif temizlik_turu == 'gecmis_etkinlikler':
            # 1 yıldan eski etkinlikleri sil
            cutoff_date = datetime.now().date() - timedelta(days=365)
            deleted_count = CalendarEvent.query.filter(CalendarEvent.date < cutoff_date).delete()
            db.session.commit()
            log_activity('Veritabanı Temizlik', f'{deleted_count} eski etkinlik silindi', current_user.id)
            return jsonify({'success': True, 'message': f'{deleted_count} eski etkinlik silindi'})
            
        elif temizlik_turu == 'tam_sifirla':
            # TÜM VERİTABANINI SIL (kullanıcılar hariç - sadece admin kullanıcı kalacak)
            from models import (ActivityLog, Client, Payment, Document, Notification, 
                               Expense, CaseFile, Announcement, CalendarEvent, 
                               WorkerInterview, IsciGorusmeTutanagi, DilekceKategori, 
                               OrnekDilekce, OrnekSozlesme, AISohbetGecmisi, User)
            
            # Her tabloyu sil (admin hariç kullanıcılar da silinecek)
            tables_to_clear = [
                ActivityLog, Client, Payment, Document, Notification,
                Expense, CaseFile, Announcement, CalendarEvent,
                WorkerInterview, IsciGorusmeTutanagi, DilekceKategori,
                OrnekDilekce, OrnekSozlesme, AISohbetGecmisi
            ]
            
            total_deleted = 0
            for table in tables_to_clear:
                deleted_count = table.query.delete()
                total_deleted += deleted_count
                
            # Admin olmayan tüm kullanıcıları sil (admin kullanıcıyı koru)
            deleted_users = User.query.filter(User.is_admin == False).delete()
            total_deleted += deleted_users
            
            db.session.commit()
            log_activity('Veritabanı Tam Sıfırlama', f'Toplam {total_deleted} kayıt silindi - Veritabanı sıfırlandı', current_user.id)
            return jsonify({'success': True, 'message': f'Veritabanı başarıyla sıfırlandı! Toplam {total_deleted} kayıt silindi.'})
            
        else:
            return jsonify({'success': False, 'message': 'Geçersiz temizlik türü'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/veritabani/yedekle', methods=['POST'])
@login_required
@permission_required('veritabani_yonetimi')
def api_veritabani_yedekle():
    """Veritabanı yedekleme ve indirme"""
    try:
        import shutil
        import tempfile
        from datetime import datetime
        from flask import send_file
        import io
        
        # Geçici yedek dosyası oluştur
        # Türkiye saatiyle yedek dosyası adı oluştur
        turkey_tz = timezone(timedelta(hours=3))
        turkey_time = datetime.now(turkey_tz)
        backup_filename = f"veritabani_yedek_{turkey_time.strftime('%Y-%m-%d_%H-%M-%S')}.db"
        
        # Mevcut veritabanının yolunu bul
        possible_db_paths = [
            os.path.join(current_app.instance_path, 'database.db'),  # Instance path
            os.path.join(current_app.root_path, 'database.db'),     # Root path
            os.path.join(current_app.root_path, 'instance', 'database.db'),  # Instance klasörü
            'database.db',  # Mevcut dizin
            os.path.join(os.path.dirname(__file__), 'database.db'),  # Uygulama dizini
            os.path.join(os.path.dirname(__file__), 'instance', 'database.db')  # Instance alt klasörü
        ]
        
        db_path = None
        for path in possible_db_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if not db_path:
            return jsonify({'success': False, 'message': 'Veritabanı dosyası bulunamadı. Mevcut dizinler kontrol edildi.'})
        
        try:
            # Memory'de dosya oluştur (disk yazma izni gerekmez)
            memory_file = io.BytesIO()
            
            # Veritabanını memory'e oku
            with open(db_path, 'rb') as db_file:
                memory_file.write(db_file.read())
            
            memory_file.seek(0)
            
            log_activity('Veritabanı Yedek', f'Veritabanı yedeği oluşturuldu ve indirildi: {backup_filename}', current_user.id)
            
            # Memory'den dosyayı indirme olarak gönder
            return send_file(
                memory_file,
                as_attachment=True,
                download_name=backup_filename,
                mimetype='application/octet-stream'
            )
        except Exception as memory_error:
            # Memory yöntemi başarısızsa, geçici dosya yöntemini dene
            try:
                # Geçici dosya oluştur
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
                
                # Veritabanını geçici dosyaya kopyala
                shutil.copy2(db_path, temp_file.name)
                temp_file.close()
                
                log_activity('Veritabanı Yedek', f'Veritabanı yedeği oluşturuldu ve indirildi: {backup_filename}', current_user.id)
                
                # Dosyayı indirme olarak gönder
                return send_file(
                    temp_file.name,
                    as_attachment=True,
                    download_name=backup_filename,
                    mimetype='application/octet-stream'
                )
            except Exception as temp_error:
                # Her iki yöntem de başarısızsa, orijinal hata ile detaylı hata ver
                raise Exception(f'Memory hatası: {str(memory_error)} | Temp file hatası: {str(temp_error)}')
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({'success': False, 'message': f'Yedekleme hatası: {str(e)}', 'detail': error_detail})

@app.route('/api/veritabani/geri_yukle', methods=['POST'])
@login_required
@permission_required('veritabani_yonetimi')
def api_veritabani_geri_yukle():
    """Veritabanı geri yükleme"""
    try:
        # Dosya yükleme kontrolü
        if 'backup_file' not in request.files:
            return jsonify({'success': False, 'message': 'Yedek dosyası seçilmedi'})
        
        file = request.files['backup_file']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Dosya seçilmedi'})
        
        # Dosya uzantısı kontrolü
        if not file.filename.lower().endswith('.db'):
            return jsonify({'success': False, 'message': 'Sadece .db dosyaları kabul edilir'})
        
        # Dosya boyutu kontrolü (max 100MB)
        file.seek(0, 2)  # Dosya sonuna git
        file_size = file.tell()
        file.seek(0)  # Başa dön
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            return jsonify({'success': False, 'message': 'Dosya çok büyük (max 100MB)'})
        
        import shutil
        import tempfile
        from datetime import datetime
        
        # Mevcut veritabanının yolunu bul
        possible_db_paths = [
            os.path.join(current_app.instance_path, 'database.db'),
            os.path.join(current_app.root_path, 'database.db'),
            os.path.join(current_app.root_path, 'instance', 'database.db'),
            'database.db',
            os.path.join(os.path.dirname(__file__), 'database.db'),
            os.path.join(os.path.dirname(__file__), 'instance', 'database.db')
        ]
        
        current_db_path = None
        for path in possible_db_paths:
            if os.path.exists(path):
                current_db_path = path
                break
        
        if not current_db_path:
            return jsonify({'success': False, 'message': 'Mevcut veritabanı dosyası bulunamadı'})
        
        # Acil durum yedeği için güvenli yol (Türkiye saati)
        turkey_tz = timezone(timedelta(hours=3))
        turkey_time = datetime.now(turkey_tz)
        backup_timestamp = turkey_time.strftime('%Y%m%d_%H%M%S')
        db_dir = os.path.dirname(current_db_path)
        emergency_backup_path = os.path.join(db_dir, f'emergency_backup_{backup_timestamp}.db')
        
        if os.path.exists(current_db_path):
            shutil.copy2(current_db_path, emergency_backup_path)
        
        # Geçici dosya oluştur
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        file.save(temp_file.name)
        temp_file.close()
        
        # Basit SQLite dosyası kontrolü (magic number kontrolü)
        with open(temp_file.name, 'rb') as f:
            header = f.read(16)
            if not header.startswith(b'SQLite format 3\x00'):
                os.unlink(temp_file.name)
                return jsonify({'success': False, 'message': 'Geçersiz SQLite dosyası'})
        
        # Veritabanı bağlantısını kapat
        db.engine.dispose()
        
        # Yedek dosyayı ana konuma taşı
        shutil.move(temp_file.name, current_db_path)
        
        # Veritabanı bağlantısını yeniden başlat
        db.create_all()
        
        log_activity('Veritabanı Geri Yükleme', f'Veritabanı geri yüklendi. Acil durum yedeği: {emergency_backup_path}', current_user.id)
        
        return jsonify({
            'success': True, 
            'message': 'Veritabanı başarıyla geri yüklendi!',
            'emergency_backup': f'emergency_backup_{backup_timestamp}.db'
        })
        
    except Exception as e:
        # Hata durumunda acil durum yedeğini geri yükle
        if 'emergency_backup_path' in locals() and 'current_db_path' in locals() and os.path.exists(emergency_backup_path):
            try:
                shutil.copy2(emergency_backup_path, current_db_path)
            except:
                pass
        
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({'success': False, 'message': f'Geri yükleme hatası: {str(e)}', 'detail': error_detail})

@app.route('/api/veritabani/istatistikler')
@login_required
@permission_required('veritabani_yonetimi')
def api_veritabani_istatistikler():
    """Veritabanı istatistiklerini JSON olarak döndür"""
    try:
        # Aynı istatistikleri ana fonksiyonla senkronize et
        stats = {
            # Temel istatistikler
            'kullanici_sayisi': User.query.count(),
            'onaysiz_kullanici_sayisi': User.query.filter_by(is_approved=False).count(),
            'dosya_sayisi': CaseFile.query.count(),
            'aktif_dosya_sayisi': CaseFile.query.filter_by(status='Aktif').count(),
            'etkinlik_sayisi': CalendarEvent.query.count(),
            'duyuru_sayisi': Announcement.query.count(),
            
            # Detaylı tablo istatistikleri
            'odeme_sayisi': Client.query.count(),  # Müşteri/ödeme ilişkili kayıtlar
            'belge_sayisi': Document.query.count(),
            'masraf_sayisi': Expense.query.count(),
            'bildirim_sayisi': Notification.query.count(),
            'aktivite_sayisi': ActivityLog.query.count(),
            
            # İşçi ve işgören tabloları
            'isci_gorusme_sayisi': IsciGorusmeTutanagi.query.count(),
            
            # Dilekçe ve sözleşme tabloları
            'ornek_dilekce_sayisi': OrnekDilekce.query.count(),
            'ornek_sozlesme_sayisi': OrnekSozlesme.query.count(),
            'dilekce_kategori_sayisi': DilekceKategori.query.count(),
            
            # Ödeme tablosu (Client tablosu müşteriler için kullanılıyor)
            'musteri_sayisi': Client.query.count(),
        }
        
        # Detaylı sistem bilgileri
        import os
        database_path = os.path.join(current_app.instance_path, 'database.db')
        database_size = 'N/A'
        if os.path.exists(database_path):
            size_bytes = os.path.getsize(database_path)
            if size_bytes >= 1024*1024:
                database_size = f"{size_bytes / (1024*1024):.1f} MB"
            elif size_bytes >= 1024:
                database_size = f"{size_bytes / 1024:.1f} KB"
            else:
                database_size = f"{size_bytes} bytes"
        
        # Tablo istatistikleri - Türkçe, okunur etiketlerle
        pretty_labels = {
            'kullanici_sayisi': 'Kullanıcı',
            'onaysiz_kullanici_sayisi': 'Onaysız Kullanıcı',
            'dosya_sayisi': 'Dosya',
            'aktif_dosya_sayisi': 'Aktif Dosya',
            'etkinlik_sayisi': 'Etkinlik',
            'duyuru_sayisi': 'Duyuru',
            'odeme_sayisi': 'Ödeme Kaydı',
            'belge_sayisi': 'Belge',
            'masraf_sayisi': 'Masraf',
            'bildirim_sayisi': 'Bildirim',
            'aktivite_sayisi': 'Aktivite',
            'isci_gorusme_sayisi': 'İşçi Görüşmesi',
            'ornek_dilekce_sayisi': 'Örnek Dilekçe',
            'ornek_sozlesme_sayisi': 'Örnek Sözleşme',
            'dilekce_kategori_sayisi': 'Dilekçe Kategorisi',
            'musteri_sayisi': 'Müşteri'
        }
        # Kaldırılan anahtarları ve 0 olanları filtrele (tercihen)
        hide_keys = set(['payment_sayisi', 'worker_interview_sayisi'])
        table_stats = {}
        for key, value in stats.items():
            if key in hide_keys:
                continue
            if key.endswith('_sayisi') and key in pretty_labels:
                table_stats[pretty_labels[key]] = value
        
        return jsonify({
            'success': True, 
            'stats': stats,
            'database_size': database_size,
            'last_update': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'active_connections': 1,
            'table_stats': table_stats
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/veritabani/export/<table_name>')
@login_required
@permission_required('veritabani_yonetimi')
def api_veritabani_export(table_name):
    """Belirtilen tablo için CSV export"""
    try:
        import csv
        import io
        from flask import make_response
        
        # Tablo adına göre model ve alanlar (mevcut modellere göre güncellendi)
        table_mapping = {
            'kullanicilar': (User, ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'is_approved', 'created_at']),
            'dosyalar': (CaseFile, ['id', 'file_type', 'courthouse', 'department', 'year', 'case_number', 'client_name', 'phone_number', 'status', 'open_date', 'next_hearing', 'hearing_time', 'hearing_type', 'description', 'user_id']),
            'musteriler': (Client, ['id', 'name', 'surname', 'tc', 'amount', 'currency', 'installments', 'registration_date', 'due_date', 'status', 'description']),
            'odemeler': (Payment, ['id', 'amount', 'date', 'client_id', 'user_id']) if hasattr(globals(), 'Payment') else None,
            'etkinlikler': (CalendarEvent, ['id', 'title', 'date', 'time', 'event_type', 'description', 'user_id', 'case_id', 'assigned_to', 'deadline_date', 'is_completed']),
            'belgeler': (Document, ['id', 'case_id', 'document_type', 'filename', 'upload_date', 'user_id', 'pdf_version']),
            'duyurular': (Announcement, ['id', 'title', 'content', 'user_id', 'created_at']),
            'masraflar': (Expense, ['id', 'case_id', 'expense_type', 'amount', 'date', 'is_paid', 'description']),
            'bildirimler': (Notification, ['id', 'message', 'user_id', 'read']),
            'aktivite_loglari': (ActivityLog, ['id', 'activity_type', 'description', 'user_id', 'timestamp']),
            'isci_gorusmeleri': (IsciGorusmeTutanagi, ['id', 'name', 'tcNo', 'phone', 'startDate', 'endDate', 'position', 'insuranceStatus', 'salary', 'workingHours', 'overtime', 'weeklyHoliday', 'annualLeave', 'terminationReason', 'severancePay', 'noticePay', 'unpaidWages', 'overtimePay', 'annualLeavePay', 'created_at']),
            'is_gorusmeleri': (WorkerInterview, ['id', 'fullName', 'tcNo', 'phone', 'address', 'startDate', 'insuranceDate', 'endDate', 'endReason', 'companyName', 'position', 'salary', 'created_at', 'user_id']),
            'ornek_dilekceler': (OrnekDilekce, ['id', 'ad', 'kategori_id', 'yuklenme_tarihi', 'user_id', 'dosya_yolu']),
            'ornek_sozlesmeler': (OrnekSozlesme, ['id', 'sozlesme_adi', 'muvekkil_adi', 'sozlesme_tarihi', 'olusturulma_tarihi', 'user_id']),
            'dilekce_kategorileri': (DilekceKategori, ['id', 'ad'])
        }
        
        if table_name not in table_mapping or table_mapping[table_name] is None:
            return jsonify({'success': False, 'message': 'Geçersiz tablo adı'}), 400
        
        model_class, columns = table_mapping[table_name]
        
        # Verileri çek
        records = model_class.query.all()
        
        # CSV dosyasını oluştur
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        
        # Türkçe header isimleri
        turkish_headers = {
            'id': 'ID',
            'username': 'Kullanıcı Adı',
            'email': 'E-posta',
            'first_name': 'Ad',
            'last_name': 'Soyad',
            'phone': 'Telefon',
            'role': 'Rol',
            'is_approved': 'Onaylandı',
            'created_at': 'Oluşturma Tarihi',
            'title': 'Başlık',
            'description': 'Açıklama',
            'status': 'Durum',
            'case_number': 'Dosya Numarası',
            'file_type': 'Dosya Türü',
            'courthouse': 'Adliye',
            'department': 'Birim',
            'year': 'Yıl',
            'client_name': 'Müvekkil',
            'phone_number': 'Telefon',
            'open_date': 'Açılış Tarihi',
            'next_hearing': 'Sonraki Duruşma',
            'hearing_time': 'Duruşma Saati',
            'hearing_type': 'Duruşma Türü',
            'name': 'Ad',
            'surname': 'Soyad',
            'tc': 'TC',
            'amount': 'Tutar',
            'date': 'Tarih',
            'currency': 'Para Birimi',
            'installments': 'Taksit',
            'registration_date': 'Kayıt Tarihi',
            'due_date': 'Vade',
            'address': 'Adres',
            'client_id': 'Müşteri ID',
            'user_id': 'Kullanıcı ID',
            'start_date': 'Başlangıç Tarihi',
            'end_date': 'Bitiş Tarihi',
            'content': 'İçerik',
            'document_type': 'Belge Türü',
            'filename': 'Dosya Adı',
            'upload_date': 'Yüklenme Tarihi',
            'priority': 'Öncelik',
            'category': 'Kategori',
            'message': 'Mesaj',
            'read': 'Okundu',
            'activity_type': 'İşlem',
            'timestamp': 'Zaman',
            'insuranceStatus': 'Sigorta Durumu',
            'workingHours': 'Çalışma Saatleri',
            'terminationReason': 'Ayrılma Nedeni',
            'severancePay': 'Kıdem',
            'noticePay': 'İhbar',
            'unpaidWages': 'Ödenmeyen Ücret',
            'overtimePay': 'Fazla Mesai',
            'annualLeavePay': 'Yıllık İzin Ücreti',
            'fullName': 'Ad Soyad',
            'companyName': 'Şirket',
            'insuranceDate': 'Sigorta Başlangıç',
            'sozlesme_adi': 'Sözleşme Adı',
            'muvekkil_adi': 'Müvekkil',
            'sozlesme_tarihi': 'Sözleşme Tarihi',
            'olusturulma_tarihi': 'Oluşturma Tarihi',
            'ad': 'Ad',
        }
        
        # Header'ları yaz
        headers = [turkish_headers.get(col, col.replace('_', ' ').title()) for col in columns]
        writer.writerow(headers)
        
        # Verileri yaz
        for record in records:
            row = []
            for col in columns:
                try:
                    value = getattr(record, col, '')
                    # Özel türetmeler
                    if table_name == 'kullanicilar' and col in ('first_name','last_name'):
                        # düz geç
                        pass
                    if value is None:
                        value = ''
                    elif hasattr(value, 'strftime'):
                        # Tarih/saat formatı
                        fmt = '%d.%m.%Y %H:%M' if 'Time' in type(value).__name__ or 'DateTime' in type(value).__name__ else '%d.%m.%Y'
                        try:
                            value = value.strftime(fmt)
                        except:
                            value = str(value)
                    elif isinstance(value, bool):
                        value = 'Evet' if value else 'Hayır'
                    elif isinstance(value, (int, float)) and col != 'id':
                        value = str(value).replace('.', ',')
                except Exception:
                    value = ''
                row.append(str(value))
            writer.writerow(row)
        
        # Response oluştur
        output.seek(0)
        csv_content = output.getvalue()
        
        response = make_response(csv_content.encode('utf-8-sig'))  # BOM ekle
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = f'attachment; filename="{table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'CSV export hatası: {str(e)}'}), 500

@app.route('/admin_panel')
@login_required
@admin_required
def admin_panel():
    # Onay bekleyen kullanıcıları al
    pending_users = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    
    # Onaylanmış kullanıcıları al (active_users olarak gönder)
    active_users = User.query.filter_by(is_approved=True).order_by(User.created_at.desc()).all()
    
    return render_template('admin_panel.html', 
                         pending_users=pending_users,
                         active_users=active_users)

@app.route('/admin/approve_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        user.is_approved = True
        user.approval_date = datetime.now()
        user.approved_by = current_user.id
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e))

@app.route('/admin/reject_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e))

@app.route('/admin/delete_user/<int:user_id>', methods=['DELETE', 'POST'])
@login_required
@admin_required
@csrf.exempt
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # Admin kullanıcısını silemezsiniz
        if user.is_admin:
            return jsonify(success=False, message='Admin kullanıcısı silinemez!')
        
        # Kullanıcının kendisini silemez
        if user.id == current_user.id:
            return jsonify(success=False, message='Kendi hesabınızı silemezsiniz!')
        
        # Log kaydı oluştur (kullanıcı silinmeden önce)
        log_activity(
            activity_type='kullanici_silme',
            description=f'Kullanıcı silindi: {user.username}',
            user_id=current_user.id,
            details={
                'silinen_kullanici': user.username,
                'silinen_kullanici_email': user.email,
                'silinen_kullanici_rol': user.role
            }
        )
        
        # Kullanıcının tüm activity log kayıtlarını sil (foreign key constraint hatasını önlemek için)
        ActivityLog.query.filter_by(user_id=user_id).delete()
        
        # Kullanıcının tüm dosyalarını başka bir yöneticiye aktar veya sil
        # Dosyaları silinecek kullanıcıdan current_user'a aktar
        user_cases = CaseFile.query.filter_by(user_id=user_id).all()
        for case in user_cases:
            case.user_id = current_user.id
        
        # Kullanıcının tüm duyurularını sil veya başka kullanıcıya aktar
        user_announcements = Announcement.query.filter_by(user_id=user_id).all()
        for announcement in user_announcements:
            announcement.user_id = current_user.id
        
        # Kullanıcının tüm etkinliklerini sil veya başka kullanıcıya aktar
        user_events = CalendarEvent.query.filter_by(user_id=user_id).all()
        for event in user_events:
            event.user_id = current_user.id
        
        # Kullanıcının tüm ödemelerini sil veya başka kullanıcıya aktar
        user_payments = Payment.query.filter_by(user_id=user_id).all()
        for payment in user_payments:
            payment.user_id = current_user.id
        
        # Kullanıcının tüm dökümanlarını başka kullanıcıya aktar
        user_documents = Document.query.filter_by(user_id=user_id).all()
        for document in user_documents:
            document.user_id = current_user.id
        
        # Kullanıcının tüm işçi görüşme formlarını başka kullanıcıya aktar
        user_interviews = WorkerInterview.query.filter_by(user_id=user_id).all()
        for interview in user_interviews:
            interview.user_id = current_user.id
        
        # Kullanıcının tüm işçi görüşme tutanaklarını başka kullanıcıya aktar
        user_tutanaks = IsciGorusmeTutanagi.query.filter_by(user_id=user_id).all()
        for tutanak in user_tutanaks:
            tutanak.user_id = current_user.id
        
        # Kullanıcının tüm örnek dilekçelerini başka kullanıcıya aktar
        user_dilekceler = OrnekDilekce.query.filter_by(user_id=user_id).all()
        for dilekce in user_dilekceler:
            dilekce.user_id = current_user.id
        
        # Kullanıcının tüm örnek sözleşmelerini başka kullanıcıya aktar
        user_sozlesmeler = OrnekSozlesme.query.filter_by(user_id=user_id).all()
        for sozlesme in user_sozlesmeler:
            sozlesme.user_id = current_user.id
        
        # Kullanıcının bildirimlerini sil
        Notification.query.filter_by(user_id=user_id).delete()
        
        # Tüm değişiklikleri kaydet
        db.session.commit()
        
        # Son olarak kullanıcıyı sil
        db.session.delete(user)
        db.session.commit()
        
        return jsonify(success=True, message='Kullanıcı ve tüm verileri başarıyla aktarıldı/silindi')
    except Exception as e:
        db.session.rollback()
        print(f"Kullanıcı silme hatası: {str(e)}")  # Debug için log ekle
        return jsonify(success=False, message=f'Kullanıcı silinirken hata oluştu: {str(e)}')

@app.route('/admin/get_user_details/<int:user_id>')
@login_required
@admin_required
def get_user_details(user_id):
    """Kullanıcı detaylarını JSON formatında döndürür"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'phone': user.phone,
                'is_admin': user.is_admin,
                'is_approved': user.is_approved,
                'created_at': user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else 'Bilinmiyor',
                'approval_date': user.approval_date.strftime('%d.%m.%Y %H:%M') if user.approval_date else 'Bilinmiyor'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Kullanıcı detayları alınamadı: {str(e)}'
        }), 500

@app.route('/admin/approve_multiple_users', methods=['POST'])
@login_required
@admin_required
def approve_multiple_users():
    """Birden fazla kullanıcıyı aynı anda onaylar"""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'message': 'Hiç kullanıcı seçilmedi'})
        
        approved_count = 0
        for user_id in user_ids:
            user = User.query.get(user_id)
            if user and not user.is_approved:
                user.is_approved = True
                user.approval_date = datetime.now()
                user.approved_by = current_user.id
                approved_count += 1
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{approved_count} kullanıcı başarıyla onaylandı'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Kullanıcılar onaylanırken hata oluştu: {str(e)}'
        }), 500

@app.route('/admin/get_user_permissions/<int:user_id>')
@login_required
@admin_required
def get_user_permissions(user_id):
    """Kullanıcı yetkilerini JSON formatında döndürür"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Kullanıcının mevcut yetkilerini al - None olabilir
        permissions = user.permissions if user.permissions is not None else {}
        
        # Eğer permissions string formatında ise parse et (eski veriler için)
        if isinstance(permissions, str):
            try:
                permissions = json.loads(permissions)
            except:
                permissions = {}
        
        # Tüm mevcut yetki anahtarlarının tam listesi
        all_permissions = [
            # Temel erişim
            'panel_goruntule', 'takvim_goruntule', 'duyuru_goruntule', 'odeme_goruntule', 'ayarlar', 'iletisim',
            
            # Dosya yönetimi  
            'dosya_sorgula', 'dosya_ekle', 'dosya_duzenle', 'dosya_sil', 'dosyalarim',
            
            # Etkinlik yönetimi
            'etkinlik_goruntule', 'etkinlik_ekle', 'etkinlik_duzenle', 'etkinlik_sil',
            
            # İçerik yönetimi
            'duyuru_ekle', 'duyuru_duzenle', 'duyuru_sil',
            
            # Finansal işlemler
            'odeme_ekle', 'odeme_duzenle', 'odeme_sil', 'odeme_istatistik_goruntule',
            
            # Hesaplamalar
            'faiz_hesaplama', 'harc_hesaplama', 'isci_hesaplama', 'vekalet_hesaplama', 'ceza_infaz_hesaplama',
            
            # Araçlar ve kaynaklar
            'ornek_dilekceler', 'ornek_sozlesmeler', 'yargi_kararlari_arama', 'ucret_tarifeleri', 'ai_avukat',
            
            # İnsan kaynakları
            'isci_gorusme_goruntule', 'isci_gorusme_ekle', 'isci_gorusme_duzenle', 'isci_gorusme_sil',
            
            # Müşteri yönetimi
            'musteri_goruntule', 'musteri_ekle', 'musteri_duzenle', 'musteri_sil',
            
            # Raporlar ve istatistikler
            'rapor_goruntule', 'rapor_olustur', 'kullanici_yonetimi', 'bildirimler',
            
            # Sistem yönetimi
            'veritabani_yonetimi', 'admin_panel', 'kullanici_onaylama'
        ]
        
        # Eksik izinleri False olarak ekle
        for permission in all_permissions:
            if permission not in permissions:
                permissions[permission] = False
        
        return jsonify({
            'success': True,
            'permissions': permissions
        })
        
    except Exception as e:
        app.logger.error(f"get_user_permissions hatası (user_id: {user_id}): {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Kullanıcı yetkileri alınamadı: {str(e)}'
        }), 500

@app.route('/admin/update_user_permissions/<int:user_id>', methods=['POST'])
@login_required
@admin_required
@csrf.exempt
def update_user_permissions(user_id):
    """Kullanıcı yetkilerini günceller"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Rol güncelleme
        if 'role' in data:
            user.role = data['role']
        
        # Admin yetkisi güncelleme
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        
        # Yetkileri güncelle (JSON formatında)
        if 'permissions' in data:
            user.permissions = data['permissions']  # JSON field olduğu için dumps gerekmez
        else:
            # Eğer yetki listesi gönderilmemişse, role göre otomatik ata
            permissions = get_simple_role_permissions(user.role)
            user.permissions = permissions  # JSON field olduğu için dumps gerekmez
        
        db.session.commit()
        
        # Log oluştur
        log_activity(
            activity_type='kullanici_guncelleme',
            description=f'Kullanıcı güncellendi: {user.username} - {user.role}',
            user_id=current_user.id,
            details={
                'updated_user': user.get_full_name(),
                'role': user.role,
                'is_admin': user.is_admin,
                'updated_by': current_user.get_full_name()
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Kullanıcı başarıyla güncellendi'
        })
            
    except Exception as e:
        db.session.rollback()
        print(f"Yetki güncelleme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Kullanıcı yetkileri güncellenirken hata oluştu: {str(e)}'
        }), 500

def get_simple_role_permissions(role):
    """Basit rol bazlı yetki sistemi"""
    base_permissions = {
        'takvim_goruntule': False,
        'duyuru_goruntule': False,
        'duyuru_ekle': False,
        'duyuru_duzenle': False,
        'duyuru_sil': False,
        'odeme_goruntule': False,
        'odeme_ekle': False,
        'odeme_duzenle': False,
        'odeme_sil': False,
        'dosya_sorgula': False,
        'dosya_ekle': False,
        'dosya_duzenle': False,
        'dosya_sil': False,
        'etkinlik_ekle': False,
        'etkinlik_duzenle': False,
        'etkinlik_sil': False,
        'faiz_hesaplama': False,
        'harc_hesaplama': False,
        'vekalet_hesaplama': False,
        'isci_hesaplama': False,
        'ornek_dilekceler': False,
        'ornek_sozlesmeler': False,
        'yargi_kararlari_arama': False,
        'ucret_tarifeleri': False,
        'isci_gorusme_ekle': False,
        'veritabani_yonetimi': False
    }
    
    if role == 'Sekreter':
        base_permissions.update({
            'takvim_goruntule': True,
            'duyuru_goruntule': True,
            'odeme_goruntule': True,
            'dosya_sorgula': True,
            'faiz_hesaplama': True,
            'harc_hesaplama': True,
            'ornek_dilekceler': True,
            'ucret_tarifeleri': True
        })
    elif role == 'Takip Elemanı':
        base_permissions.update({
            'takvim_goruntule': True,
            'duyuru_goruntule': True,
            'odeme_goruntule': True,
            'odeme_ekle': True,
            'odeme_duzenle': True,
            'dosya_sorgula': True,
            'dosya_ekle': True,
            'etkinlik_ekle': True,
            'faiz_hesaplama': True,
            'harc_hesaplama': True,
            'vekalet_hesaplama': True,
            'ornek_dilekceler': True,
            'ucret_tarifeleri': True
        })
    elif role == 'Muhasebe':
        base_permissions.update({
            'takvim_goruntule': True,
            'duyuru_goruntule': True,
            'odeme_goruntule': True,
            'odeme_ekle': True,
            'odeme_duzenle': True,
            'odeme_sil': True,
            'dosya_sorgula': True,
            'faiz_hesaplama': True,
            'harc_hesaplama': True,
            'vekalet_hesaplama': True,
            'isci_hesaplama': True,
            'ucret_tarifeleri': True
        })
    elif role == 'Ulaşım':
        base_permissions.update({
            'takvim_goruntule': True,
            'duyuru_goruntule': True,
            'etkinlik_ekle': True,
            'etkinlik_duzenle': True,
            'dosya_sorgula': True,
            'ucret_tarifeleri': True
        })
    elif role == 'Stajyer Avukat':
        base_permissions.update({
            'takvim_goruntule': True,
            'duyuru_goruntule': True,
            'odeme_goruntule': True,
            'dosya_sorgula': True,
            'dosya_ekle': True,
            'etkinlik_ekle': True,
            'faiz_hesaplama': True,
            'harc_hesaplama': True,
            'vekalet_hesaplama': True,
            'isci_hesaplama': True,
            'ornek_dilekceler': True,
            'ornek_sozlesmeler': True,
            'yargi_kararlari_arama': True,
            'ucret_tarifeleri': True
        })
    elif role == 'Avukat':
        base_permissions.update({
            'takvim_goruntule': True,
            'duyuru_goruntule': True,
            'duyuru_ekle': True,
            'duyuru_duzenle': True,
            'odeme_goruntule': True,
            'odeme_ekle': True,
            'odeme_duzenle': True,
            'dosya_sorgula': True,
            'dosya_ekle': True,
            'dosya_duzenle': True,
            'dosya_sil': True,
            'etkinlik_ekle': True,
            'etkinlik_duzenle': True,
            'etkinlik_sil': True,
            'faiz_hesaplama': True,
            'harc_hesaplama': True,
            'vekalet_hesaplama': True,
            'isci_hesaplama': True,
            'ornek_dilekceler': True,
            'ornek_sozlesmeler': True,
            'yargi_kararlari_arama': True,
            'ucret_tarifeleri': True,
            'isci_gorusme_ekle': True
        })
    elif role == 'Yönetici Avukat':
        # Tüm yetkiler
        for key in base_permissions:
            base_permissions[key] = True
    
    return base_permissions

def get_role_permissions_template(role):
    """Role göre yetki şablonunu döndürür"""
    templates = {
        'Sekreter': {
            'takvim_goruntule': True,
            'etkinlik_goruntule': True,
            'etkinlik_ekle': False,
            'etkinlik_duzenle': False,
            'etkinlik_sil': False,
            'duyuru_goruntule': True,
            'duyuru_ekle': False,
            'duyuru_duzenle': False,
            'duyuru_sil': False,
            'odeme_goruntule': True,
            'odeme_ekle': True,
            'odeme_duzenle': True,
            'odeme_sil': False,
            'dosya_sorgula': True,
            'dosya_ekle': False,
            'dosya_duzenle': False,
            'dosya_sil': False,
            'faiz_hesaplama': True,
            'harc_hesaplama': True,
            'isci_hesaplama': True,
            'vekalet_hesaplama': False,
            'ceza_infaz_hesaplama': False,
            'ornek_dilekceler': True,
            'ornek_sozlesmeler': False,
            'ucret_tarifeleri': True,
            'yargi_kararlari_arama': False,
            'veritabani_yonetimi': False,
            'isci_gorusme_goruntule': True,
            'isci_gorusme_ekle': True,
            'isci_gorusme_duzenle': False,
            'isci_gorusme_sil': False
        },
        'Stajyer Avukat': {
            'takvim_goruntule': True,
            'etkinlik_goruntule': True,
            'etkinlik_ekle': True,
            'etkinlik_duzenle': True,
            'etkinlik_sil': False,
            'duyuru_goruntule': True,
            'duyuru_ekle': False,
            'duyuru_duzenle': False,
            'duyuru_sil': False,
            'odeme_goruntule': True,
            'odeme_ekle': True,
            'odeme_duzenle': True,
            'odeme_sil': False,
            'dosya_sorgula': True,
            'dosya_ekle': True,
            'dosya_duzenle': True,
            'dosya_sil': False,
            'faiz_hesaplama': True,
            'harc_hesaplama': True,
            'isci_hesaplama': True,
            'vekalet_hesaplama': True,
            'ceza_infaz_hesaplama': True,
            'ornek_dilekceler': True,
            'ornek_sozlesmeler': True,
            'ucret_tarifeleri': True,
            'yargi_kararlari_arama': True,
            'veritabani_yonetimi': False,
            'isci_gorusme_goruntule': True,
            'isci_gorusme_ekle': True,
            'isci_gorusme_duzenle': True,
            'isci_gorusme_sil': False
        },
        'Avukat': {
            'takvim_goruntule': True,
            'etkinlik_goruntule': True,
            'etkinlik_ekle': True,
            'etkinlik_duzenle': True,
            'etkinlik_sil': True,
            'duyuru_goruntule': True,
            'duyuru_ekle': True,
            'duyuru_duzenle': True,
            'duyuru_sil': False,
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
            'ornek_dilekceler': True,
            'ornek_sozlesmeler': True,
            'ucret_tarifeleri': True,
            'yargi_kararlari_arama': True,
            'veritabani_yonetimi': False,
            'isci_gorusme_goruntule': True,
            'isci_gorusme_ekle': True,
            'isci_gorusme_duzenle': True,
            'isci_gorusme_sil': True
        },
        'Yönetici Avukat': {
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
            'ornek_dilekceler': True,
            'ornek_sozlesmeler': True,
            'ucret_tarifeleri': True,
            'yargi_kararlari_arama': True,
            'veritabani_yonetimi': True,
            'isci_gorusme_goruntule': True,
            'isci_gorusme_ekle': True,
            'isci_gorusme_duzenle': True,
            'isci_gorusme_sil': True
        }
    }
    
    return templates.get(role, {})

def get_all_permissions_template():
    """Admin için tüm yetkileri döndürür"""
    return {
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
        'ornek_dilekceler': True,
        'ornek_sozlesmeler': True,
        'ucret_tarifeleri': True,
        'yargi_kararlari_arama': True,
        'veritabani_yonetimi': True,
        'isci_gorusme_goruntule': True,
        'isci_gorusme_ekle': True,
        'isci_gorusme_duzenle': True,
        'isci_gorusme_sil': True
    }

@app.route('/duyuru_duzenle/<int:duyuru_id>', methods=['POST'])
@login_required
@permission_required('duyuru_duzenle')
def duyuru_duzenle(duyuru_id):
    try:
        data = request.get_json()
        duyuru = Announcement.query.get_or_404(duyuru_id)
        
        old_title = duyuru.title
        old_content = duyuru.content
        
        duyuru.title = data['title']
        duyuru.content = data['content']
        
        # Log kaydı
        log = ActivityLog(
            activity_type='duyuru_duzenleme',
            description=f'Duyuru düzenlendi: {old_title}',
            details={
                'eski_baslik': old_title,
                'yeni_baslik': duyuru.title,
                'eski_icerik': old_content,
                'yeni_icerik': duyuru.content
            },
            user_id=current_user.id,
            related_announcement_id=duyuru.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/duyuru_sil/<int:duyuru_id>', methods=['POST'])
@login_required
@permission_required('duyuru_sil')
def duyuru_sil(duyuru_id):
    try:
        duyuru = Announcement.query.get_or_404(duyuru_id)
        
        # Log kaydı
        log = ActivityLog(
            activity_type='duyuru_silme',
            description=f'Duyuru silindi: {duyuru.title}',
            details={
                'baslik': duyuru.title,
                'icerik': duyuru.content
            },
            user_id=current_user.id
        )
        
        db.session.delete(duyuru)
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/isci_gorusme', endpoint='isci_gorusme')
@login_required
@permission_required('isci_gorusme_goruntule')
def worker_interview():
    return render_template('isci_gorusme.html')

@app.route('/save_isci_gorusme', methods=['POST'])
@login_required
@permission_required('isci_gorusme_ekle')
@csrf.exempt
def save_isci_gorusme():
    try:
        print("Form kaydetme işlemi başlatılıyor...")
        form_data = request.form.to_dict()
        print(f"Gelen form verileri: {form_data}")
        
        # Gerekli alanları kontrol et
        required_fields = ['name', 'tcNo']
        for field in required_fields:
            if field not in form_data or not form_data[field].strip():
                print(f"Gerekli alan eksik: {field}")
                return jsonify({'success': False, 'error': f'{field} alanı zorunludur'}), 400
        
        # Tanık durumunu kontrol et
        witness_option = form_data.get('witnessOption', 'no')
        print(f"Tanık seçeneği: {witness_option}")
        
        # Tarih alanlarını kontrol et - formatı değiştirmeden olduğu gibi kaydet
        date_fields = ['startDate', 'endDate']
        for field in date_fields:
            if field in form_data and form_data[field]:
                # Tarih formatını kontrol et (GG.AA.YYYY veya GG.AA.YYYY/GG.AA.YYYY)
                date_str = form_data[field]
                single_date_regex = r'^\d{2}\.\d{2}\.\d{4}$'
                dual_date_regex = r'^\d{2}\.\d{2}\.\d{4}/\d{2}\.\d{2}\.\d{4}$'
                
                if not (re.match(single_date_regex, date_str) or re.match(dual_date_regex, date_str)):
                    print(f"Geçersiz tarih formatı: {field} = {date_str}")
                    return jsonify({'success': False, 'error': f'Geçersiz tarih formatı: {field}. Lütfen GG.AA.YYYY veya GG.AA.YYYY/GG.AA.YYYY formatında girin.'}), 400
            else:
                # Tarih alanı boş ise hata döndür
                print(f"Tarih alanı boş: {field}")
                return jsonify({'success': False, 'error': f'{field} alanı boş olamaz'}), 400
        
        # Form ID'si varsa güncelle, yoksa yeni kayıt oluştur
        form_id = form_data.get('id')
        if form_id:
            print(f"Mevcut form güncelleniyor: {form_id}")
            form = IsciGorusmeTutanagi.query.get(int(form_id))
            if not form:
                return jsonify({'success': False, 'error': 'Form bulunamadı'}), 404
        else:
            print("Yeni form oluşturuluyor")
            form = IsciGorusmeTutanagi()
            form.user_id = current_user.id
        
        # Form verilerini modele aktar
        for key, value in form_data.items():
            if key != 'id' and hasattr(form, key):
                print(f"Ayarlanıyor: {key} = {value}")
                setattr(form, key, value)
        
        # Tanık bilgilerini işle
        if witness_option == 'yes':
            # Tanık sayısını al
            witness_count = int(form_data.get('witnessCount', 0))
            witnesses = []
            
            # Tanıkları ekle
            for i in range(1, witness_count + 1):
                witness_name_key = f'witness{i}Name'
                witness_info_key = f'witness{i}Info'
                
                if witness_name_key in form_data:
                    witness_name = form_data.get(witness_name_key, '').strip()
                    witness_info = form_data.get(witness_info_key, '').strip()
                    
                    if witness_name:  # Sadece adı dolu olan tanıkları ekle
                        witnesses.append({
                            'name': witness_name,
                            'info': witness_info
                        })
            
            # Tanık bilgilerini JSON olarak kaydet
            form.witnesses = json.dumps({
                'count': len(witnesses),
                'witnesses': witnesses
            })
            print(f"Tanık bilgileri kaydedildi: {form.witnesses}")
        else:
            # Tanık seçeneği "yok" ise boş liste olarak ayarla
            form.witnesses = json.dumps({'count': 0, 'witnesses': []})
            print("Tanık bilgisi yok olarak ayarlandı")
        
        # Veritabanına kaydet
        print("Veritabanına kaydediliyor...")
        db.session.add(form)
        db.session.commit()
        print("Form başarıyla kaydedildi")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Form kaydetme hatası: {str(e)}")
        import traceback
        print(f"Hata detayı: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/save_isci_gorusme_json', methods=['POST'])
@login_required
@permission_required('isci_gorusme_goruntule')
def save_isci_gorusme_json():
    try:
        data = request.get_json()
        print(f"DEBUG - Gelen form verisi: {data}")  # DEBUG LOG
        
        # Tarih işleme fonksiyonu - esnek format desteği
        def parse_date_flexible(date_str):
            if not date_str or not date_str.strip():
                return None

            date_str = date_str.strip()

            # YYYY-MM-DD formatı
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

            # DD.MM.YYYY formatı
            try:
                return datetime.strptime(date_str, '%d.%m.%Y').date()
            except ValueError:
                pass

            # DD/MM/YYYY formatı
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                pass

            # Tarih çevrilemezse None döndür
            return None

        # Tarihleri esnek şekilde çevir
        start_date = parse_date_flexible(data.get('startDate'))
        end_date = parse_date_flexible(data.get('endDate'))
        insurance_date = parse_date_flexible(data.get('insuranceDate'))

        # Sayı değerlerini güvenli şekilde çevir
        def safe_float(value, default=0):
            if not value or str(value).strip() == '':
                return default
            try:
                return float(str(value).strip())
            except (ValueError, TypeError):
                return default
        
        # HTML form alanlarından DB alanlarına tam mapping
        def get_field_value(field_name, default=''):
            """HTML form alanından değer al, boşsa default döndür"""
            value = data.get(field_name, default)
            if value is None or str(value).strip() == '':
                return default
            return str(value).strip()

        # Form ID kontrolü - düzenleme mi yoksa yeni kayıt mı?
        form_id = data.get('id')

        if form_id:
            # MEVCUT FORMU GÜNCELLE
            interview = WorkerInterview.query.get(form_id)
            if not interview:
                return jsonify({'success': False, 'message': 'Düzenlenecek form bulunamadı.'}), 404

            # Yetki kontrolü
            if not current_user.has_permission('isci_gorusme_goruntule') and not current_user.is_admin and interview.user_id != current_user.id:
                return jsonify({'success': False, 'message': 'Bu formu düzenleme yetkiniz yok.'}), 403

            # Mevcut formun alanlarını güncelle
            interview.fullName = get_field_value('name', 'Belirtilmemiş')
            interview.tcNo = get_field_value('tcNo', '00000000000')
            interview.phone = get_field_value('phone', '0000000000')
            interview.address = get_field_value('address', 'Belirtilmemiş')
            interview.startDate = start_date or datetime.now().date()
            interview.insuranceDate = insurance_date or start_date or datetime.now().date()
            interview.endDate = end_date or datetime.now().date()
            interview.endReason = get_field_value('terminationReason', 'Belirtilmemiş')
            interview.companyName = get_field_value('insuranceStatus', 'Belirtilmemiş')
            interview.businessType = get_field_value('salary', 'Belirtilmemiş')  # İşyeri Faaliyeti/Konusu
            interview.companyAddress = get_field_value('insuranceDate', 'Belirtilmemiş')
            interview.registryNumber = get_field_value('insuranceNo', 'Belirtilmemiş')  # Mersis/Vergi/Ticaret Sicil No
            interview.position = get_field_value('position', 'Belirtilmemiş')
            interview.workHours = get_field_value('workingHours', 'Belirtilmemiş')
            interview.overtime = get_field_value('overtime', 'Belirtilmemiş')
            interview.salary = get_field_value('department', 'Belirtilmemiş')  # Ücret alanı (HTML'de department field)
            interview.transportation = safe_float(data.get('transportation'), 0) if data.get('transportation') else None
            interview.food = safe_float(data.get('food'), 0) if data.get('food') else None
            interview.benefits = get_field_value('benefits', 'Belirtilmemiş')
            interview.weeklyHoliday = get_field_value('weeklyHoliday', 'Belirtilmemiş')
            interview.holidays = get_field_value('holidays', 'Belirtilmemiş')
            interview.annualLeave = get_field_value('annualLeave', 'Belirtilmemiş')
            interview.unpaidSalary = get_field_value('unpaidSalary', 'Belirtilmemiş')
            interview.witness1 = get_field_value('witness1Name')
            interview.witness1Info = get_field_value('witness1Info')
            interview.witness2 = get_field_value('witness2Name')
            interview.witness2Info = get_field_value('witness2Info')
            interview.witness3 = get_field_value('witness3Name')
            interview.witness3Info = get_field_value('witness3Info')
            interview.witness4 = get_field_value('witness4Name')
            interview.witness4Info = get_field_value('witness4Info')

            # Radio button seçimlerini güncelle
            interview.severancePayOption = get_field_value('severancePayOption', 'no')
            interview.noticePayOption = get_field_value('noticePayOption', 'no')
            interview.unpaidWagesOption = get_field_value('unpaidWagesOption', 'no')
            interview.overtimePayOption = get_field_value('overtimePayOption', 'no')
            interview.annualLeavePayOption = get_field_value('annualLeavePayOption', 'no')
            interview.ubgtPayOption = get_field_value('ubgtPayOption', 'no')
            interview.witnessOption = get_field_value('witnessOption', 'no')

            # UPDATE için add() gerekmez, sadece commit()
            message = 'Form başarıyla güncellendi.'
        else:
            # YENİ FORM OLUŞTUR
            interview = WorkerInterview(
                # Kişisel Bilgiler
                fullName=get_field_value('name', 'Belirtilmemiş'),
                tcNo=get_field_value('tcNo', '00000000000'),
                phone=get_field_value('phone', '0000000000'),
                address=get_field_value('address', 'Belirtilmemiş'),

                # Tarih Bilgileri
                startDate=start_date or datetime.now().date(),
                insuranceDate=insurance_date or start_date or datetime.now().date(),
                endDate=end_date or datetime.now().date(),

                # İş Bilgileri
                endReason=get_field_value('terminationReason', 'Belirtilmemiş'),
                companyName=get_field_value('insuranceStatus', 'Belirtilmemiş'),
                businessType=get_field_value('salary', 'Belirtilmemiş'),  # İşyeri Faaliyeti/Konusu
                companyAddress=get_field_value('insuranceDate', 'Belirtilmemiş'),
                registryNumber=get_field_value('insuranceNo', 'Belirtilmemiş'),  # Mersis/Vergi/Ticaret Sicil No
                position=get_field_value('position', 'Belirtilmemiş'),

                # Çalışma Bilgileri
                workHours=get_field_value('workingHours', 'Belirtilmemiş'),
                overtime=get_field_value('overtime', 'Belirtilmemiş'),

                # Ücret Bilgileri
                salary=get_field_value('department', 'Belirtilmemiş'),  # Ücret alanı (HTML'de department field)
                transportation=safe_float(data.get('transportation'), 0) if data.get('transportation') else None,
                food=safe_float(data.get('food'), 0) if data.get('food') else None,
                benefits=get_field_value('benefits', 'Belirtilmemiş'),

                # Tatil Bilgileri
                weeklyHoliday=get_field_value('weeklyHoliday', 'Belirtilmemiş'),
                holidays=get_field_value('holidays', 'Belirtilmemiş'),
                annualLeave=get_field_value('annualLeave', 'Belirtilmemiş'),
                unpaidSalary=get_field_value('unpaidSalary', 'Belirtilmemiş'),

                # Tanıklar
                witness1=get_field_value('witness1Name'),
                witness1Info=get_field_value('witness1Info'),
                witness2=get_field_value('witness2Name'),
                witness2Info=get_field_value('witness2Info'),
                witness3=get_field_value('witness3Name'),
                witness3Info=get_field_value('witness3Info'),
                witness4=get_field_value('witness4Name'),
                witness4Info=get_field_value('witness4Info'),

                # Radio button seçimleri
                severancePayOption=get_field_value('severancePayOption', 'no'),
                noticePayOption=get_field_value('noticePayOption', 'no'),
                unpaidWagesOption=get_field_value('unpaidWagesOption', 'no'),
                overtimePayOption=get_field_value('overtimePayOption', 'no'),
                annualLeavePayOption=get_field_value('annualLeavePayOption', 'no'),
                ubgtPayOption=get_field_value('ubgtPayOption', 'no'),
                witnessOption=get_field_value('witnessOption', 'no'),

                user_id=current_user.id
            )

            db.session.add(interview)
            message = 'Form başarıyla kaydedildi.'

        db.session.commit()

        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        print(f"Hata: {str(e)}")  # Hatayı konsola yazdır
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Form kaydedilirken bir hata oluştu: {str(e)}'})

@app.route('/get_worker_interviews')
@login_required
def get_worker_interviews():
    try:
        # Yetki kontrolü - isci_gorusme_goruntule yetkisi olanlar tüm formları görebilir
        if current_user.has_permission('isci_gorusme_goruntule') or current_user.is_admin:
            interviews = WorkerInterview.query.order_by(WorkerInterview.created_at.desc()).all()
        else:
            interviews = WorkerInterview.query.filter_by(user_id=current_user.id).order_by(WorkerInterview.created_at.desc()).all()

        # Frontend'e uygun format oluştur
        forms_data = []
        for interview in interviews:
            forms_data.append({
                'id': interview.id,
                'name': interview.fullName or 'İsimsiz Form',  # HTML'de 'name' alanı bekleniyor
                'date': interview.created_at.strftime('%d.%m.%Y') if interview.created_at else 'Tarih yok'
            })

        return jsonify({
            'success': True,
            'forms': forms_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_worker_interview/<int:interview_id>')
@login_required
def get_worker_interview(interview_id):
    try:
        interview = WorkerInterview.query.get_or_404(interview_id)
        # Yetki kontrolü - isci_gorusme_goruntule yetkisi olanlar erişebilir
        if not current_user.has_permission('isci_gorusme_goruntule') and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Yetkisiz erişim'}), 403

        # HTML form alanlarına uygun format oluştur - doğru field mapping
        form_data = {
            # Kişisel Bilgiler
            'name': interview.fullName or 'Belirtilmemiş',
            'tcNo': interview.tcNo or 'Belirtilmemiş',
            'phone': interview.phone or 'Belirtilmemiş',
            'address': interview.address or 'Belirtilmemiş',

            # Tarih Bilgileri - DD.MM.YYYY formatında
            'startDate': interview.startDate.strftime('%d.%m.%Y') if interview.startDate else 'Belirtilmemiş',
            'endDate': interview.endDate.strftime('%d.%m.%Y') if interview.endDate else 'Belirtilmemiş',

            # İş Bilgileri - DOĞRU FIELD MAPPING
            'position': interview.position or 'Belirtilmemiş',
            'salary': interview.businessType or 'Belirtilmemiş',  # İşyeri Faaliyeti/Konusu (HTML'de salary field)
            'insuranceStatus': interview.companyName or 'Belirtilmemiş',  # Şirket İsmi
            'department': interview.salary or 'Belirtilmemiş',  # Ücret (HTML'de department field)
            'insuranceNo': interview.registryNumber or 'Belirtilmemiş',  # Mersis/Vergi/Ticaret Sicil No
            'insuranceDate': interview.companyAddress or 'Belirtilmemiş',  # Şirket Adresi-Telefonu

            # Çalışma Bilgileri
            'workingHours': interview.workHours or 'Belirtilmemiş',
            'overtime': interview.overtime or 'Belirtilmemiş',
            'weeklyHoliday': interview.weeklyHoliday or 'Belirtilmemiş',
            'annualLeave': interview.annualLeave or 'Belirtilmemiş',

            # İşten Ayrılma
            'terminationReason': interview.endReason or 'Belirtilmemiş',

            # Radio button seçimleri
            'severancePayOption': interview.severancePayOption or 'no',
            'noticePayOption': interview.noticePayOption or 'no',
            'unpaidWagesOption': interview.unpaidWagesOption or 'no',
            'overtimePayOption': interview.overtimePayOption or 'no',
            'annualLeavePayOption': interview.annualLeavePayOption or 'no',
            'ubgtPayOption': interview.ubgtPayOption or 'no',
            'witnessOption': interview.witnessOption or 'no',

            # Tanık bilgileri
            'witness1': interview.witness1 or '',
            'witness1Info': interview.witness1Info or '',
            'witness2': interview.witness2 or '',
            'witness2Info': interview.witness2Info or '',
            'witness3': interview.witness3 or '',
            'witness3Info': interview.witness3Info or '',
            'witness4': interview.witness4 or '',
            'witness4Info': interview.witness4Info or '',

            # Tanık sayısını hesapla ve ekle
            'witnessCount': sum(1 for w in [interview.witness1, interview.witness2, interview.witness3, interview.witness4] if w and w.strip()),

            # Tanık bilgilerini JSON formatında da sağla
            'witnesses': json.dumps({
                'count': sum(1 for w in [interview.witness1, interview.witness2, interview.witness3, interview.witness4] if w and w.strip()),
                'witnesses': [
                    {'name': w[0], 'info': w[1] or ''} for w in [
                        (interview.witness1, interview.witness1Info),
                        (interview.witness2, interview.witness2Info),
                        (interview.witness3, interview.witness3Info),
                        (interview.witness4, interview.witness4Info)
                    ] if w[0] and w[0].strip()
                ]
            }),
        }

        print(f"DEBUG - Dönen form verisi: witness1='{form_data.get('witness1')}', witness1Info='{form_data.get('witness1Info')}'")
        return jsonify({
            'success': True,
            'form': form_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_worker_interview/<int:interview_id>', methods=['DELETE'])
@login_required
def delete_worker_interview(interview_id):
    try:
        interview = WorkerInterview.query.get_or_404(interview_id)
        # Yetki kontrolü - isci_gorusme_sil yetkisi olanlar silebilir
        if not current_user.has_permission('isci_gorusme_sil') and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Yetkisiz erişim'}), 403

        db.session.delete(interview)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate_worker_interview_pdf', methods=['POST'])
@login_required
def generate_worker_interview_pdf():
    # Bu fonksiyon artık kullanılmıyor, PDF oluşturma işlemi tamamen client-side yapılacak
    return jsonify({'success': True, 'message': 'PDF oluşturma işlemi artık client-side yapılıyor'})



@app.route('/save_isci_gorusme_form', methods=['POST'])
@login_required
@permission_required('isci_gorusme_ekle')
def save_isci_gorusme_form():
    try:
        form_data = request.form.to_dict()
        
        # Tanık durumunu kontrol et
        witness_option = form_data.get('witnessOption', 'no')
        
        # Tarih alanlarını kontrol et - formatı değiştirmeden olduğu gibi kaydet
        date_fields = ['startDate', 'endDate']
        for field in date_fields:
            if field in form_data and form_data[field]:
                # Tarih formatını kontrol et (GG.AA.YYYY veya GG.AA.YYYY/GG.AA.YYYY)
                date_str = form_data[field]
                single_date_regex = r'^\d{2}\.\d{2}\.\d{4}$'
                dual_date_regex = r'^\d{2}\.\d{2}\.\d{4}/\d{2}\.\d{2}\.\d{4}$'
                
                if not (re.match(single_date_regex, date_str) or re.match(dual_date_regex, date_str)):
                    return jsonify({'success': False, 'error': f'Geçersiz tarih formatı: {field}. Lütfen GG.AA.YYYY veya GG.AA.YYYY/GG.AA.YYYY formatında girin.'})
            else:
                # Tarih alanı boş ise hata döndür
                return jsonify({'success': False, 'error': f'{field} alanı boş olamaz'})
        
        # Form ID'si varsa güncelle, yoksa yeni kayıt oluştur
        form_id = form_data.get('id')
        if form_id:
            form = IsciGorusmeTutanagi.query.get(int(form_id))
            if not form:
                return jsonify({'success': False, 'error': 'Form bulunamadı'})
        else:
            form = IsciGorusmeTutanagi()
            form.user_id = current_user.id
        
        # Form verilerini modele aktar
        for key, value in form_data.items():
            if key != 'id' and hasattr(form, key):
                # Tarih alanlarını string olarak sakla
                if key in date_fields:
                    # Tarih alanlarını string olarak bırak, dönüştürme yapma
                    setattr(form, key, value)
                else:
                    setattr(form, key, value)
        
        # Tanık bilgilerini işle
        if witness_option == 'yes':
            # Tanık sayısını al
            witness_count = int(form_data.get('witnessCount', 0))
            witnesses = []
            
            # Tanıkları ekle
            for i in range(1, witness_count + 1):
                witness_name_key = f'witness{i}Name'
                witness_info_key = f'witness{i}Info'
                
                if witness_name_key in form_data:
                    witness_name = form_data.get(witness_name_key, '').strip()
                    witness_info = form_data.get(witness_info_key, '').strip()
                    
                    if witness_name:  # Sadece adı dolu olan tanıkları ekle
                        witnesses.append({
                            'name': witness_name,
                            'info': witness_info
                        })
            
            # Tanık bilgilerini JSON olarak kaydet
            form.witnesses = json.dumps({
                'count': len(witnesses),
                'witnesses': witnesses
            })
        else:
            # Tanık seçeneği "yok" ise boş liste olarak ayarla
            form.witnesses = json.dumps({'count': 0, 'witnesses': []})
        
        # Veritabanına kaydet
        db.session.add(form)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Form kaydetme hatası: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# Kaydedilmiş formları getirme
@app.route('/get_isci_gorusme_forms')
@login_required
@permission_required('isci_gorusme_goruntule')
def get_isci_gorusme_forms():
    try:
        # Yetki kontrolü - isci_gorusme_goruntule yetkisi olanlar tüm formları görebilir
        if current_user.has_permission('isci_gorusme_goruntule') or current_user.is_admin:
            forms = IsciGorusmeTutanagi.query.order_by(IsciGorusmeTutanagi.created_at.desc()).all()
        else:
            forms = IsciGorusmeTutanagi.query.filter_by(user_id=current_user.id).order_by(IsciGorusmeTutanagi.created_at.desc()).all()

        forms_data = []

        for form in forms:
            # Kullanıcı bilgisini al
            user = User.query.get(form.user_id)
            username = user.username if user else 'Bilinmeyen'
            
            forms_data.append({
                'id': form.id,
                'name': form.name or 'İsimsiz Form',
                'date': form.created_at.strftime('%d.%m.%Y'),
                'created_by': username
            })
        
        return jsonify({'success': True, 'forms': forms_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Belirli bir formu getirme
@app.route('/get_isci_gorusme_form/<int:form_id>')
@login_required
@permission_required('isci_gorusme_goruntule')
def get_isci_gorusme_form(form_id):
    try:
        form = IsciGorusmeTutanagi.query.get(form_id)
        if not form:
            return jsonify({'success': False, 'error': 'Form bulunamadı'})
        
        # Yetki kontrolü - isci_gorusme_goruntule yetkisi olanlar erişebilir
        if not current_user.has_permission('isci_gorusme_goruntule') and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Bu forma erişim izniniz yok'})
        
        form_data = form.to_dict()
        
        return jsonify({'success': True, 'form': form_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Form silme
@app.route('/delete_isci_gorusme_form/<int:form_id>', methods=['DELETE'])
@login_required
@permission_required('isci_gorusme_sil')
def delete_isci_gorusme_form(form_id):
    try:
        form = IsciGorusmeTutanagi.query.get(form_id)
        if not form:
            return jsonify({'success': False, 'error': 'Form bulunamadı'})
        
        # Yetki kontrolü - isci_gorusme_sil yetkisi olanlar silebilir
        if not current_user.has_permission('isci_gorusme_sil') and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Bu formu silme izniniz yok'})
        
        db.session.delete(form)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/worker_interview', endpoint='worker_interview_alt')
@login_required
def worker_interview():
    return render_template('worker_interview.html')

@app.route('/worker_interview_page')
@login_required
def worker_interview_page():
    return render_template('worker_interview.html')

def create_admin_user():
    """Admin kullanıcısı oluşturur (daha önce yoksa)"""
    admin_exists = User.query.filter_by(username='admin').first()
    if not admin_exists:
        admin_user = User(
            username='admin',
            email='admin@lawautomation.com',
            first_name='Admin',
            last_name='Kullanıcısı',
            role='Yönetici Avukat',
            gender='erkek',
            phone='5555555555',
            birthdate=datetime(1990, 1, 1).date(),
            is_admin=True,
            is_approved=True,
            approval_date=datetime.now(),
            permissions={
                'takvim_goruntule': True,
                'etkinlik_ekle': True,
                'etkinlik_duzenle': True,
                'etkinlik_sil': True,
                'etkinlik_goruntule': True,
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
                'ornek_dilekceler': True,
                'ornek_sozlesmeler': True,
                'ucret_tarifeleri': True,
                'yargi_kararlari_arama': True,
                'veritabani_yonetimi': True
            }
        )
        admin_user.set_password('Pemus3458')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin kullanıcısı oluşturuldu!")
    else:
        print("Admin kullanıcısı zaten mevcut.")

@app.route('/admin/get_user_info/<int:user_id>')
@login_required
@admin_required
def get_user_info(user_id):
    """Kullanıcı bilgilerini JSON formatında döndürür"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_admin': user.is_admin,
                'is_approved': user.is_approved,
                'created_at': user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else None,
                'approval_date': user.approval_date.strftime('%d.%m.%Y %H:%M') if user.approval_date else None
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Kullanıcı bilgileri alınamadı: {str(e)}'
        }), 500



# User model için permission bağımlılıklarını güncelleyelim
def get_permission_dependencies():
    """Yetkiler arasındaki bağımlılıkları döndürür"""
    return {
        # Dosya işlemleri
        'dosya_ekle': ['dosya_sorgula'],
        'dosya_duzenle': ['dosya_sorgula'],
        'dosya_sil': ['dosya_sorgula'],
        
        # Takvim işlemleri
        'etkinlik_ekle': ['takvim_goruntule'],
        'etkinlik_duzenle': ['takvim_goruntule'],
        'etkinlik_sil': ['takvim_goruntule'],
        
        # Duyuru işlemleri
        'duyuru_ekle': ['duyuru_goruntule'],
        'duyuru_duzenle': ['duyuru_goruntule'],
        'duyuru_sil': ['duyuru_goruntule'],
        
        # Ödeme işlemleri
        'odeme_ekle': ['odeme_goruntule'],
        'odeme_duzenle': ['odeme_goruntule'],
        'odeme_sil': ['odeme_goruntule'],
        'odeme_istatistik_goruntule': ['odeme_goruntule'],
        
        # Müşteri işlemleri
        'musteri_ekle': ['musteri_goruntule'],
        'musteri_duzenle': ['musteri_goruntule'],
        'musteri_sil': ['musteri_goruntule'],
        
        # Rapor işlemleri
        'rapor_olustur': ['rapor_goruntule']
    }

# Müşteri silme route'u ekleyelim
@app.route('/delete_client/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    # Login kontrolü - JSON endpoint için
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Oturum açmanız gereklidir.'}), 401
        
    if not current_user.has_permission('odeme_sil'):
        return jsonify({'success': False, 'error': 'Ödeme silme yetkiniz bulunmamaktadır.'}), 403
        
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'success': False, 'error': 'Ödeme kaydı bulunamadı.'}), 404
    
    # Log kaydı
    log = ActivityLog(
        activity_type='odeme_silme',
        description=f'Ödeme silindi: {client.name} {client.surname}',
        details={
            'musteri': f'{client.name} {client.surname}',
            'tc': client.tc,
            'tutar': f'{client.amount} {client.currency}'
        },
        user_id=current_user.id
    )
    
    try:
        # İlişkili payment kayıtlarını önce sil
        deleted_payments = Payment.query.filter_by(client_id=client_id).delete()
        logger.info(f"Silinen payment kayıt sayısı: {deleted_payments}")
        
        # Log kaydını ekle
        db.session.add(log)
        
        # Client'ı sil
        db.session.delete(client)
        db.session.commit()
        
        logger.info(f"Client başarıyla silindi: {client_id}")
        return jsonify({'success': True, 'message': 'Ödeme başarıyla silindi'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Client silme hatası: {str(e)}")
        return jsonify({'success': False, 'error': f'Silme işlemi başarısız: {str(e)}'}), 500

@app.route('/preview_udf/<int:document_id>')
def preview_udf(document_id):
    """UDF dosyaları için özel önizleme sayfası"""
    try:
        document = Document.query.get_or_404(document_id)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
        
        if not os.path.exists(filepath):
            return "Dosya bulunamadı", 404
            
        _, extension = os.path.splitext(document.filepath)
        if extension.lower() != '.udf':
            return "Bu dosya .udf uzantılı değil, önizlenemez", 400
        
        # 1. Dosyanın PDF versiyonu varsa onu göster
        if document.pdf_version:
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], document.pdf_version)
            if os.path.exists(pdf_path):
                print(f"UDF için hazır PDF sürümü kullanılıyor: {pdf_path}")
                return send_file(pdf_path, mimetype='application/pdf')
        
        # 2. PDF dönüşümü dene
        try:
            print(f"UDF dosyasını PDF'e dönüştürme deneniyor...")
            pdf_path = convert_udf_to_pdf(filepath)
            if pdf_path:
                print(f"UDF dosyası PDF'e dönüştürüldü: {pdf_path}")
                # Dönüştürülmüş PDF dosyasını kaydet
                pdf_filename = f"{document.case_id}_{int(pytime.time())}_converted_{document.filename}.pdf"
                permanent_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
                
                # Geçici PDF dosyasını kalıcı konuma kopyala
                shutil.copy(pdf_path, permanent_pdf_path)
                
                # Veritabanında belgenin PDF sürümünü güncelle
                document.pdf_version = pdf_filename
                db.session.commit()
                
                return send_file(permanent_pdf_path, mimetype='application/pdf')
        except Exception as e:
            print(f"UDF dosyasını PDF'e dönüştürürken hata: {str(e)}")
            # PDF dönüşümü başarısız olduysa bilgilendirme sayfasını göster
            pass
        
        # İndirme bağlantısını oluştur
        download_link = url_for('download_document', document_id=document_id)
        
        # İçerik görüntüleme bağlantısını oluştur (HTML ayrıştırma)
        view_link = url_for('direct_view_udf', document_id=document_id)
        
        # Önizleme sayfasını göster
        return render_template('udf_preview.html', download_link=download_link, view_link=view_link)
    except Exception as e:
        print(f"UDF önizleme hatası: {str(e)}")
        return f"UDF dosyasını açarken bir hata oluştu: {str(e)}", 500

def parse_udf_content(input_path):
    """UDF dosyasını ayrıştırıp içeriği çıkarır"""
    try:
        print(f"UDF dosyası ayrıştırılıyor: {input_path}")
        
        # UDF dosyasını ikili modda aç
        with open(input_path, 'rb') as f:
            content = f.read()
        
        # UDF formatını analiz et
        # 1. Magic bytes kontrolü
        if content.startswith(b'PK'):
            # ZIP formatındaysa, ZIP olarak açmayı dene
            import zipfile
            from io import BytesIO
            import re
            
            print("UDF ZIP formatında olabilir, ZIP olarak açılıyor...")
            
            try:
                with zipfile.ZipFile(BytesIO(content)) as zip_ref:
                    file_list = zip_ref.namelist()
                    print(f"ZIP içerisindeki dosyalar: {file_list}")
                    
                    # Sadece content.xml dosyasını ara ve içeriğini al
                    actual_content = ""
                    
                    for file_name in file_list:
                        if file_name == 'content.xml' or file_name.endswith('/content.xml'):
                            content_xml = zip_ref.read(file_name).decode('utf-8', errors='ignore')
                            
                            # CDATA içeriğini çıkar
                            cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', content_xml, re.DOTALL)
                            if cdata_match:
                                # CDATA içeriğini direkt kullan
                                actual_content = cdata_match.group(1)
                            else:
                                # Eğer CDATA yoksa, metin içeriğini çıkar
                                actual_content = re.sub(r'<[^>]+>', ' ', content_xml)
                                actual_content = re.sub(r'\s+', ' ', actual_content).strip()
                    
                    # İçerik bulunamadıysa boş dönme, ham içeriği temizleyerek göster
                    if not actual_content:
                        for file_name in file_list:
                            if file_name.endswith('.xml') and not file_name.startswith('document'):
                                try:
                                    file_content = zip_ref.read(file_name).decode('utf-8', errors='ignore')
                                    # XML etiketlerini kaldır
                                    text_only = re.sub(r'<[^>]+>', ' ', file_content)
                                    # Gereksiz boşlukları temizle
                                    text_only = re.sub(r'\s+', ' ', text_only).strip()
                                    
                                    if len(text_only) > 100:  # Anlamlı içerik kontrolü
                                        actual_content = text_only
                                        break
                                except:
                                    pass
                
                # Daha temiz bir HTML gösterim
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>UDF Dosya İçeriği</title>
                    <style>
                        body {{ 
                            font-family: Arial, sans-serif; 
                            margin: 0; 
                            padding: 0;
                            line-height: 1.6;
                            color: #333;
                        }}
                        .content {{ 
                            background: #fff; 
                            padding: 30px; 
                            border-radius: 8px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            white-space: pre-wrap;
                            max-width: 100%;
                            margin: 0;
                            text-align: left;
                        }}
                    </style>
                </head>
                <body>
                    <div class="content">{escape(actual_content)}</div>
                </body>
                </html>
                """
                
                # HTML içeriğini geçici dosyaya kaydet
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_html:
                    tmp_html.write(html_content.encode('utf-8'))
                    html_path = tmp_html.name
                
                print(f"UDF içeriği HTML olarak kaydedildi: {html_path}")
                return html_path
                
            except zipfile.BadZipFile:
                print("UDF dosyası geçerli bir ZIP formatında değil")
        
        # 2. XML formatı kontrolü
        if b'<?xml' in content or b'<UYAP' in content:
            print("UDF XML formatında olabilir, XML olarak ayrıştırılıyor...")
            import re
            
            # XML içeriğini text olarak decode et
            text_content = content.decode('utf-8', errors='ignore')
            
            # CDATA içeriğini arama
            cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', text_content, re.DOTALL)
            if cdata_match:
                # CDATA içeriğini direkt kullan
                text_only = cdata_match.group(1)
            else:
                # XML etiketlerini kaldırarak sadece metin içeriğini al
                try:
                    # XML etiketlerini kaldır
                    text_only = re.sub(r'<[^>]+>', ' ', text_content)
                    # Gereksiz boşlukları temizle
                    text_only = re.sub(r'\s+', ' ', text_only).strip()
                except:
                    text_only = text_content
            
            # Daha temiz bir HTML gösterim
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>UDF Dosya İçeriği</title>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        margin: 0;
                        padding: 0;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .content {{ 
                        background: #fff; 
                        padding: 30px; 
                        border-radius: 8px; 
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        white-space: pre-wrap;
                        max-width: 100%;
                        margin: 0;
                        text-align: left;
                    }}
                </style>
            </head>
            <body>
                <div class="content">{escape(text_only)}</div>
            </body>
            </html>
            """
            
            # HTML içeriğini geçici dosyaya kaydet
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_html:
                tmp_html.write(html_content.encode('utf-8'))
                html_path = tmp_html.name
            
            print(f"UDF içeriği HTML olarak kaydedildi: {html_path}")
            return html_path
        
        # 3. Metin formatı kontrolü
        try:
            # Dosyayı text olarak decode etmeyi dene
            text_content = content.decode('utf-8', errors='ignore')
            
            # Minimum anlamlı içerik kontrolü
            if len(text_content) > 10:
                print("UDF metin formatında olabilir, metin olarak işleniyor...")
                
                # HTML dönüşümü - daha temiz metin formatlaması
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>UDF Dosya İçeriği</title>
                    <style>
                        body {{ 
                            font-family: Arial, sans-serif; 
                            margin: 0;
                            padding: 0;
                            line-height: 1.6;
                            color: #333;
                        }}
                        .content {{ 
                            background: #fff; 
                            padding: 30px; 
                            border-radius: 8px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            white-space: pre-wrap;
                            max-width: 100%;
                            margin: 0;
                            text-align: left;
                        }}
                    </style>
                </head>
                <body>
                    <div class="content">{escape(text_content)}</div>
                </body>
                </html>
                """
                
                # HTML içeriğini geçici dosyaya kaydet
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_html:
                    tmp_html.write(html_content.encode('utf-8'))
                    html_path = tmp_html.name
                
                print(f"UDF içeriği HTML olarak kaydedildi: {html_path}")
                return html_path
        except:
            pass
        
        # 4. İkili içerik olarak göster - son çare
        print("UDF formatı tanınamadı, ikili içerik olarak gösteriliyor...")
        
        # Bilgilendirici hata mesajı göster
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>UDF Dosya İçeriği</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    color: #333;
                    text-align: center;
                }}
                .warning {{ 
                    background-color: #fff3cd; 
                    padding: 25px; 
                    border-radius: 8px; 
                    margin: 40px auto;
                    max-width: 600px;
                    border-left: 5px solid #ffc107;
                    text-align: left;
                }}
                h1 {{
                    color: #2c3e50;
                }}
                .btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>UDF Dosya İçeriği</h1>
            
            <div class="warning">
                <h2>Bu UDF dosyasının içeriği görüntülenemiyor</h2>
                <p>Bu UDF dosyası görüntülenebilir metin içeriğine sahip değil veya tanımlanamayan bir formatta.</p>
                <p>Dosyayı bilgisayarınıza indirip UYAP Editör ile açmanız önerilir.</p>
            </div>
        </body>
        </html>
        """
        
        # HTML içeriğini geçici dosyaya kaydet
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_html:
            tmp_html.write(html_content.encode('utf-8'))
            html_path = tmp_html.name
        
        print(f"UDF içeriği ikili formatta HTML olarak kaydedildi: {html_path}")
        return html_path
        
    except Exception as e:
        print(f"UDF dosyası ayrıştırma hatası: {str(e)}")
        return None

def convert_udf_to_pdf(input_path):
    """UDF dosyasını PDF'e dönüştürür"""
    try:
        print(f"UDF dosyasını PDF'e dönüştürme başlatılıyor: {input_path}")
        
        # Çıktı için geçici dosya oluştur
        output_path = os.path.join(tempfile.gettempdir(), 
                                  f"temp_converted_{int(pytime.time())}.pdf")
        
        # 1. YÖNTEM: UYAP Editör CLI komutunu dene
        try:
            print("UYAP Editör CLI ile dönüştürme deneniyor...")
            # UYAP Editör'ün muhtemel konumları
            uyap_editor_paths = [
                r"C:\Program Files\UYAP\UYAP Editor\UYAPEditor.exe",
                r"C:\Program Files (x86)\UYAP\UYAP Editor\UYAPEditor.exe",
                r"C:\UYAP\UYAP Editor\UYAPEditor.exe"
            ]
            
            uyap_exe = None
            for path in uyap_editor_paths:
                if os.path.exists(path):
                    uyap_exe = path
                    break
            
            if uyap_exe:
                print(f"UYAP Editör bulundu: {uyap_exe}")
                # UYAP Editör export komut satırı kullanımı (teorik)
                # UYAP Editör gerçekte böyle bir komut satırı arayüzü sağlamıyor olabilir
                try:
                    result = subprocess.run(
                        [uyap_exe, "--export-pdf", input_path, "--output", output_path],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0 and os.path.exists(output_path):
                        print("UYAP Editör ile dönüştürme başarılı")
                        return output_path
                except:
                    print("UYAP Editör komut satırı dönüştürmesi başarısız")
        except Exception as e:
            print(f"UYAP Editör dönüştürme hatası: {str(e)}")
        
        # 2. YÖNTEM: LibreOffice ile dönüştürmeyi dene
        try:
            print("LibreOffice ile dönüştürme deneniyor...")
            soffice_path = None
            if os.name == 'nt':  # Windows
                # Windows'da olası LibreOffice konumları
                possible_paths = [
                    "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
                    "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
                    # Program Files dizininde arama
                    *glob.glob("C:\\Program Files\\*\\program\\soffice.exe"),
                    *glob.glob("C:\\Program Files (x86)\\*\\program\\soffice.exe"),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        soffice_path = path
                        break
            else:  # Linux/Mac
                # Linux/Mac'te soffice genellikle PATH içindedir
                soffice_path = "/usr/bin/soffice"
                
            if soffice_path and os.path.exists(soffice_path):
                # Geçici çalışma dizini oluştur
                temp_dir = tempfile.mkdtemp()
                
                # LibreOffice komutu
                cmd = [
                    soffice_path,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', temp_dir,
                    input_path
                ]
                
                print(f"LibreOffice komutu çalıştırılıyor: {' '.join(cmd)}")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    # Dönüştürülen dosyayı bul
                    base_name = os.path.basename(input_path)
                    base_name_without_ext = os.path.splitext(base_name)[0]
                    converted_path = os.path.join(temp_dir, f"{base_name_without_ext}.pdf")
                    
                    if os.path.exists(converted_path):
                        # Geçici konuma taşı
                        shutil.copy(converted_path, output_path)
                        # Geçici dizini temizle
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        
                        print(f"LibreOffice ile dönüştürme başarılı: {output_path}")
                        return output_path
                    else:
                        print(f"LibreOffice çıktı dosyası bulunamadı: {converted_path}")
                else:
                    print(f"LibreOffice hatası: {stderr.decode()}")
                
                # Geçici dizini temizle
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"LibreOffice ile dönüştürme hatası: {str(e)}")
        
        # 3. YÖNTEM: UDF içeriğini HTML olarak ayrıştırıp PDF'e dönüştür
        try:
            print("UDF içeriğini ayrıştırıp PDF'e dönüştürme deneniyor...")
            html_path = parse_udf_content(input_path)
            
            if html_path:
                try:
                    # HTML'i PDF'e dönüştürme için wkhtmltopdf kullanan pdfkit'i dene
                    # Bu kısmın çalışması için wkhtmltopdf yüklü olmalı
                    import pdfkit
                    pdfkit_options = {
                        'page-size': 'A4',
                        'margin-top': '10mm',
                        'margin-right': '10mm',
                        'margin-bottom': '10mm',
                        'margin-left': '10mm',
                        'encoding': 'UTF-8',
                    }
                    
                    pdfkit.from_file(html_path, output_path, options=pdfkit_options)
                    
                    # HTML dosyasını temizle
                    os.remove(html_path)
                    
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"HTML->PDF dönüşümü başarılı: {output_path}")
                        return output_path
                except Exception as e:
                    print(f"HTML->PDF dönüşüm hatası: {str(e)}")
        except Exception as e:
            print(f"İçerik ayrıştırma ve PDF dönüşüm hatası: {str(e)}")
        
        print("Tüm dönüştürme yöntemleri başarısız oldu")
        return None
    except Exception as e:
        print(f"Dönüştürme hatası: {str(e)}")
        return None

@app.route('/view_udf_content/<int:document_id>')
def view_udf_content(document_id):
    """UDF içeriğini doğrudan tarayıcıda gösterir"""
    try:
        document = Document.query.get_or_404(document_id)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
        
        if not os.path.exists(filepath):
            return "Dosya bulunamadı", 404
            
        _, extension = os.path.splitext(document.filepath)
        if extension.lower() != '.udf':
            return "Bu dosya .udf uzantılı değil, görüntülenemez", 400
            
        # UDF içeriğini HTML olarak ayrıştır
        html_path = parse_udf_content(filepath)
        if html_path:
            # HTML içeriğini doğrudan döndür
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # HTML dosyasını temizle
            try:
                os.remove(html_path)
            except:
                pass
                
            return html_content
            
        return "UDF içeriği ayrıştırılamadı", 500
    except Exception as e:
        return f"UDF içeriği görüntüleme hatası: {str(e)}", 500

# UDF içeriğini doğrudan göster - bu yeni bir endpoint
@app.route('/direct_view_udf/<int:document_id>')
def direct_view_udf(document_id):
    """UDF içeriğini doğrudan tarayıcıda göster"""
    try:
        document = Document.query.get_or_404(document_id)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
        
        if not os.path.exists(filepath):
            return "Dosya bulunamadı", 404
            
        # UDF dosyasını ayrıştır ve HTML olarak göster
        print(f"UDF içeriği doğrudan ayrıştırılıyor: {filepath}")
        html_path = parse_udf_content(filepath)
        
        if html_path:
            # HTML içeriğini oku
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # HTML dosyasını temizle
            try:
                os.remove(html_path)
            except:
                pass
                
            # HTML içeriğini doğrudan döndür
            return Response(html_content, mimetype='text/html')
        else:
            return "UDF içeriği ayrıştırılamadı", 500
    except Exception as e:
        print(f"UDF içeriği doğrudan görüntüleme hatası: {str(e)}")
        return f"UDF dosyası görüntülenirken hata oluştu: {str(e)}", 500

@app.route('/direct_view_udf_dilekce/<int:dilekce_id>')
def direct_view_udf_dilekce(dilekce_id):
    """UDF dilekçe içeriğini doğrudan tarayıcıda göster"""
    try:
        dilekce = OrnekDilekce.query.get_or_404(dilekce_id)
        filepath = os.path.join(app.config['ORNEK_DILEKCE_UPLOAD_FOLDER'], dilekce.dosya_yolu)
        
        if not os.path.exists(filepath):
            return "Dosya bulunamadı", 404
            
        # UDF dosyasını ayrıştır ve HTML olarak göster
        print(f"UDF dilekçe içeriği doğrudan ayrıştırılıyor: {filepath}")
        html_path = parse_udf_content(filepath)
        
        if html_path:
            # HTML içeriğini oku
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # HTML dosyasını temizle
            try:
                os.remove(html_path)
            except:
                pass
                
            # HTML içeriğini doğrudan döndür
            return Response(html_content, mimetype='text/html')
        else:
            return "UDF içeriği ayrıştırılamadı", 500
    except Exception as e:
        print(f"UDF dilekçe içeriği doğrudan görüntüleme hatası: {str(e)}")
        return f"UDF dosyası görüntülenirken hata oluştu: {str(e)}", 500

def parse_tarifeler():
    # Dosya yolunu güvenli şekilde ayarla - önce firstwebsite klasörü içinde dene
    firstwebsite_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tarifeler.txt')
    parent_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tarifeler.txt')
    
    # Önce firstwebsite klasöründe dosya var mı kontrol et
    if os.path.exists(firstwebsite_filepath):
        filepath = firstwebsite_filepath
    elif os.path.exists(parent_filepath):
        filepath = parent_filepath  
    else:
        # Dosya hiç yoksa varsayılan parent yolunu kullan
        filepath = parent_filepath
    
    # Varsayılan olarak boş ve geçerli bir yapı
    tarifeler = {
        "İstanbul Barosu": [],
        "TBB": [],
        "kaplan_danismanlik_tarifesi": {"kategoriler": []}
    }
    
    grup_map = {
        "ISTBARO_2025": "İstanbul Barosu",
        "TBB_2025": "TBB"
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        kaplan_danismanlik_json_str = ""
        in_kaplan_danismanlik_json_block = False

        for line_num, line_content_raw in enumerate(lines):
            line_content = line_content_raw.strip()

            if line_content.startswith("KAPLAN HUKUK DANIŞMANLIK ÜCRET TARİFESİ START"):
                in_kaplan_danismanlik_json_block = True
                kaplan_danismanlik_json_str = ""  # Bloğa girildiğinde önceki içeriği sıfırla
                continue
            elif line_content.startswith("KAPLAN HUKUK DANIŞMANLIK ÜCRET TARİFESİ END"):
                in_kaplan_danismanlik_json_block = False
                if kaplan_danismanlik_json_str:
                    try:
                        parsed_json = json.loads(kaplan_danismanlik_json_str)
                        if isinstance(parsed_json, dict) and "kategoriler" in parsed_json and isinstance(parsed_json["kategoriler"], list):
                            tarifeler["kaplan_danismanlik_tarifesi"] = parsed_json
                        else:
                            logging.warning(
                                f"Kaplan Danışmanlık JSON formatı beklenmiyor (kategoriler listesi yok) tarifeler.txt okunurken. Satır: ~{line_num}. "
                                f"İçerik başlangıcı: {kaplan_danismanlik_json_str[:200]}..."
                            )
                            # Varsayılan boş değer zaten atanmış durumda
                    except json.JSONDecodeError as e:
                        logging.error(
                            f"Kaplan Danışmanlık JSON parse edilemedi tarifeler.txt okunurken: {e}. Satır: ~{line_num}. "
                            f"İçerik başlangıcı: {kaplan_danismanlik_json_str[:200]}..."
                        )
                        # Varsayılan boş değer zaten atanmış durumda
                kaplan_danismanlik_json_str = "" # Bloğun sonunda string'i temizle
                continue

            if in_kaplan_danismanlik_json_block:
                kaplan_danismanlik_json_str += line_content_raw # Orijinal satırları (newline dahil) birleştir
                continue

            # START/END bloğu dışındaki satırlar (Yorumlar ve boş satırlar hariç)
            if not line_content or line_content.startswith("#"):
                continue

            parts = [part.strip() for part in line_content.split('|')]
            if len(parts) < 7:
                logging.warning(f"Uyarı: Satır {line_num + 1} ({filepath}) yetersiz bölüm içeriyor ({len(parts)}), atlanıyor: {line_content}")
                continue

            tarife_grubu_txt, kategori_adi_txt, _, hizmet_adi_txt, temel_ucret_txt, _, birim_txt, *ek_not_parts = parts
            ek_not_txt = ek_not_parts[0] if ek_not_parts and ek_not_parts[0] else None
            
            current_group_key = grup_map.get(tarife_grubu_txt)
            if not current_group_key:
                # KAPLAN_OZEL satırları artık START/END bloğunda JSON olarak yönetildiği için burada işlenmemeli.
                if tarife_grubu_txt.upper() != 'KAPLAN_OZEL':
                     logging.warning(f"Uyarı: Satır {line_num + 1} ({filepath})'deki tarife grubu '{tarife_grubu_txt}' tanınmıyor, atlanıyor.")
                continue

            kategori_obj = next((kat for kat in tarifeler[current_group_key] if kat["kategori"] == kategori_adi_txt), None)
            
            if kategori_obj is None:
                kategori_obj = {"kategori": kategori_adi_txt, "items": []}
                tarifeler[current_group_key].append(kategori_obj)

            item = {
                "hizmet_adi": hizmet_adi_txt,
                "temel_ucret": temel_ucret_txt,
                "original_ucret_str": temel_ucret_txt # JS'nin parse etmesi için orijinal string
            }
            if birim_txt and birim_txt.upper() not in ["TL", "TRY", ""]:
                item["birim"] = birim_txt
            if ek_not_txt:
                item["ek_not"] = ek_not_txt
            
            kategori_obj["items"].append(item)

    except FileNotFoundError:
        logging.error(f"Hata: Tarife dosyası bulunamadı: {filepath}")
    except Exception as e:
        import traceback
        logging.error(f"Hata: Tarife dosyası okunurken/işlenirken genel bir hata oluştu ({filepath}): {e}\\n{traceback.format_exc()}")
    
    return tarifeler

@app.route('/api/tarifeler')
@login_required
@permission_required('ucret_tarifeleri')
def api_tarifeler():
    data = parse_tarifeler()
    # parse_tarifeler artık her zaman bir dict döndürdüğü için error kontrolüne gerek yok,
    # en kötü ihtimalle boş tarifeler döner.
    return jsonify(data)

@app.route('/api/kaydet_kaplan_danismanlik_tarife', methods=['POST'])
@login_required
def kaydet_kaplan_danismanlik_tarife():
    if not current_user.has_permission('ucret_tarifeleri'): 
        return jsonify({"success": False, "error": "Ücret tarifelerine erişim yetkiniz yok."}), 403

    try:
        new_kaplan_data = request.get_json()
        if not isinstance(new_kaplan_data, dict) or "kategoriler" not in new_kaplan_data or not isinstance(new_kaplan_data["kategoriler"], list):
            logging.error(f"Geçersiz Kaplan Danışmanlık tarife verisi alındı: {new_kaplan_data}")
            return jsonify({"success": False, "error": "Geçersiz veri formatı. 'kategoriler' listesi içeren bir JSON objesi bekleniyor."}), 400

        # Dosya yolunu güvenli şekilde ayarla - önce firstwebsite klasörü içinde dene
        firstwebsite_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tarifeler.txt')
        parent_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tarifeler.txt')
        
        # Önce firstwebsite klasöründe dosya var mı kontrol et
        if os.path.exists(firstwebsite_filepath):
            filepath = firstwebsite_filepath
        elif os.path.exists(parent_filepath):
            filepath = parent_filepath
        else:
            # Dosya hiç yoksa firstwebsite içinde oluştur (yazma yetkisi daha muhtemel)
            filepath = firstwebsite_filepath
        
        raw_lines = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_lines = f.readlines()
        else: 
            logging.warning(f"Tarife dosyası bulunamadı: {filepath}. Yeni dosya oluşturulacak.")

        start_marker = "KAPLAN HUKUK DANIŞMANLIK ÜCRET TARİFESİ START"
        end_marker = "KAPLAN HUKUK DANIŞMANLIK ÜCRET TARİFESİ END"
        
        new_json_content_str = json.dumps(new_kaplan_data, ensure_ascii=False, indent=2)

        output_lines = []
        start_index = -1
        end_index = -1

        for i, line_raw in enumerate(raw_lines):
            line_stripped = line_raw.strip()
            if line_stripped == start_marker:
                start_index = i
            elif line_stripped == end_marker and start_index != -1: # START daha önce bulunduysa
                end_index = i
                break # İlk tam bloğu bulduk, işlemi bitir
        
        if start_index != -1: # START marker'ı bulundu
            # START'a kadar olan kısmı al
            output_lines.extend(raw_lines[:start_index])
            
            # Yeni bloğu ekle
            output_lines.append(start_marker + '\n')
            output_lines.append(new_json_content_str + '\n')
            output_lines.append(end_marker + '\n')
            
            if end_index != -1: # Hem START hem END bulundu (normal durum)
                # END'den sonraki kısmı ekle
                output_lines.extend(raw_lines[end_index + 1:])
            else: # Sadece START bulundu, END yok (hatalı dosya veya tek START marker'ı vardı)
                logging.warning(f"Tarife dosyasında ('{filepath}') '{start_marker}' bulundu ancak takip eden bir '{end_marker}' bulunamadı. Mevcut START sonrası atlanacak.")
                # Bu durumda, eski START sonrasını atlamamak, veri kaybını önleyebilir veya 
                # kullanıcının amacına göre farklı bir strateji izlenebilir.
                # Şimdilik, eski START sonrasını atlayıp yeni bloğu yazdık.
        else: # START marker'ı hiç bulunamadı, tüm eski içeriği koru ve bloğu sona ekle
            output_lines = list(raw_lines) # Tüm eski satırları al
            if output_lines and not output_lines[-1].endswith('\n'):
                output_lines.append('\n')
            elif not output_lines and raw_lines: # Dosya sadece boş satırlardan oluşuyorsa
                 output_lines.append('\n')
            
            output_lines.append(start_marker + '\n')
            output_lines.append(new_json_content_str + '\n')
            output_lines.append(end_marker + '\n')

        # Dosya yazma yetkisi kontrolü
        dir_path = os.path.dirname(filepath)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
                logging.info(f"Dizin oluşturuldu: {dir_path}")
            except Exception as dir_error:
                logging.error(f"Dizin oluşturulamadı: {dir_path}, Hata: {dir_error}")
                return jsonify({"success": False, "error": f"Dizin oluşturulamadı: {str(dir_error)}"}), 500
        
        # Yazma yetkisi kontrolü
        if not os.access(dir_path, os.W_OK):
            logging.error(f"Dizin yazma yetkisi yok: {dir_path}")
            return jsonify({"success": False, "error": f"Dizin yazma yetkisi yok: {dir_path}"}), 403
            
        # Dosya yazma işlemi
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(output_lines)
            logging.info(f"Tarife dosyası başarıyla kaydedildi: {filepath}")
        except PermissionError as perm_error:
            logging.error(f"Dosya yazma yetkisi hatası: {filepath}, Hata: {perm_error}")
            return jsonify({"success": False, "error": f"Dosya yazma yetkisi yok: {str(perm_error)}"}), 403
        except Exception as write_error:
            logging.error(f"Dosya yazma hatası: {filepath}, Hata: {write_error}")
            return jsonify({"success": False, "error": f"Dosya yazma hatası: {str(write_error)}"}), 500

        log_activity("Tarife Güncelleme", f"Kaplan Hukuk Danışmanlık Ücret Tarifesi güncellendi.", current_user.id)
        return jsonify({"success": True, "message": "Kaplan Hukuk Danışmanlık Tarifesi başarıyla güncellendi."})

    except Exception as e: 
        logging.error(f"Kaplan Danışmanlık Tarifesi kaydedilirken genel bir hata oluştu: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Sunucu hatası: {str(e)}"}), 500

@app.route('/ucret-tarifeleri')
@login_required
@permission_required('ucret_tarifeleri')
def ucret_tarifeleri_page():
    """
    Ücret tarifeleri sayfasını render eder.
    """
    # Eğer @login_required kullanmıyorsanız ve kullanıcı bilgisi template'e göndermeniz gerekmiyorsa,
    # bu kısımları silebilirsiniz.
    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    profile_image_url = url_for('static', filename='profile_pics/' + user.profile_image) if user.profile_image else url_for('static', filename='profile_pics/default.jpg')
    
    return render_template('ucret_tarifeleri.html', title="Ücret Tarifeleri", profile_image_url=profile_image_url, current_user=current_user)

@app.route('/api/odeme_detay/<int:client_id>')
@login_required
def get_odeme_detay(client_id):
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'error': 'Ödeme kaydı bulunamadı'}), 404

    # Payment modelindeki doğru alan adlarını kullanıyoruz:
    # Tarih için: date
    # Tutar için: amount
    taksitler = Payment.query.filter_by(client_id=client.id).order_by(Payment.date.asc()).all() 
    
    odeme_gecmisi_data = []
    for taksit in taksitler:
        odeme_gecmisi_data.append({
            'tarih': taksit.date.strftime('%Y-%m-%d') if taksit.date else None,
            'tutar': taksit.amount, 
            'aciklama': "Ödeme Kaydı" # Payment modelinde özel bir açıklama alanı olmadığı için genel bir ifade
        })

    data = {
        'id': client.id,
        'name': client.name,
        'surname': client.surname,
        'tc': client.tc,
        'amount': client.amount, 
        'currency': client.currency,
        'installments': client.installments, 
        'registration_date': client.registration_date.strftime('%Y-%m-%d') if client.registration_date else None,
        'due_date': client.due_date.strftime('%Y-%m-%d') if client.due_date else None,
        'status': client.status,
        'description': client.description, 
        'odeme_gecmisi': odeme_gecmisi_data
    }
    return jsonify(data)

@login_required
@permission_required('isci_gorusme_sil')
def delete_isci_gorusme_form(form_id):
    form = IsciGorusmeTutanagi.query.get_or_404(form_id)
    db.session.delete(form)
    db.session.commit()
    # Aktivite loglama
    log_activity(
        activity_type='İşçi Görüşme Formu Silindi',
        description=f'{form.name} adlı işçi görüşme formu silindi.',
        user_id=current_user.id
    )
    return jsonify(success=True)

@app.route('/ornek_dilekceler')
@login_required
@permission_required('ornek_dilekceler')
def ornek_dilekceler():
    return render_template('ornek_dilekceler.html')

@app.route('/ornek_sozlesme_formu')
@login_required
@permission_required('ornek_sozlesmeler')
def ornek_sozlesme_formu():
    return render_template('ornek_sozlesme_formu.html')

@app.route('/api/contract_template', methods=['GET'])
@login_required
def get_contract_template():
    """Aktif sözleşme taslağını getir"""
    try:
        template = ContractTemplate.query.filter_by(is_active=True).first()
        if not template:
            # Eğer hiç taslak yoksa default bir tane oluştur
            template = ContractTemplate(
                template_name='Varsayılan Taslak',
                avukat_adi='Av. Mustafa KAPLAN',
                avukat_adres='Güneşli Meydanı Cumhuriyet Cd. No.47 K.3 D.8 (AKBANK ÜSTÜ) GÜNEŞLİ/İST.',
                banka_bilgisi='Garanti Bankası Güneşli Şubesi',
                iban_no='TR930006200029500006684655',
                yetkili_mahkeme='Bakırköy Mahkemesi ve İcra Daireleri',
                kanun_no='1136 sayılı Avukatlık Kanunu 171 ve 172',
                giris_metni='Yukarıda adı, soyadı (veya ünvanı) ile tebligata elverişli adresleri belirtilen taraflar arasında aşağıda yazılı şartlarla AVUKATLIK ÜCRET SÖZLEŞMESİ yapılmıştır. Bu sözleşmede iş sahibi MÜVEKKİL ve işi üzerine alan AVUKAT diye adlandırılmıştır.',
                madde2='MADDE 2) Sözleşme konusu olan işten dolayı, Avukat\'a {avukatlikUcreti} avukatlık ücreti ödenecektir.\nBu ücret {avukatAdi}\'a ait {bankaBilgisi} {ibanNo} İban nolu hesaba ödenecektir. Belirli sürelerde yapılması gereken ödemelerden herhangi biri yapılmadığı takdirde ücretin tamamı muaccel olur. İş sahibinin birden çok olması halinde sözleşmeyi birlikte imzalayanlar, Avukatlık Ücretinin ödenmesinde Avukata karşı müteselsilen borçlu ve sorumludurlar.',
                madde3='Tespit olunan ücret yalnız bu sözleşmede yazılı işin ve işlerin karşılığıdır. Bunlar dışında kalacak takipler ve bu işle ilgili bağlantılı bulunsa dahi karşı taraf veya üçüncü bir şahıs tarafından karşılıklı dava veya ayrı davalar şeklinde açılacak davalar bu sözleşme ücretin dışındadır. Avukat, bu sözleşmeye göre peşin verilmesi gerekli ücret ve aşağıda yazılı gider avansı kendisine ödenmediği sürece işe başlamak zorunluluğunda değildir. İş sahibi ile ilgili yapılacak hukuki, idari ve adli işlemlerden kaynaklanacak masraflar iş sahibine aittir.',
                updated_by=current_user.id
            )
            db.session.add(template)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'template': {
                'avukatAdi': template.avukat_adi,
                'avukatAdres': template.avukat_adres,
                'bankaBilgisi': template.banka_bilgisi,
                'ibanNo': template.iban_no,
                'yetkiliMahkeme': template.yetkili_mahkeme,
                'kanunNo': template.kanun_no,
                'girisMetni': template.giris_metni,
                'madde2': template.madde2,
                'madde3': template.madde3,
                'madde4': template.madde4,
                'madde5': template.madde5,
                'madde6': template.madde6,
                'madde7': template.madde7,
                'madde8': template.madde8,
                'madde9': template.madde9,
                'madde10': template.madde10
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/contract_template', methods=['POST'])
@login_required
def save_contract_template():
    """Sözleşme taslağını kaydet/güncelle"""
    try:
        data = request.get_json()
        
        # Mevcut aktif taslağı bul veya yeni oluştur
        template = ContractTemplate.query.filter_by(is_active=True).first()
        if not template:
            template = ContractTemplate()
            db.session.add(template)
        
        # Verileri güncelle
        template.avukat_adi = data.get('avukatAdi', '')
        template.avukat_adres = data.get('avukatAdres', '')
        template.banka_bilgisi = data.get('bankaBilgisi', '')
        template.iban_no = data.get('ibanNo', '')
        template.yetkili_mahkeme = data.get('yetkiliMahkeme', '')
        template.kanun_no = data.get('kanunNo', '')
        template.giris_metni = data.get('girisMetni', '')
        template.madde2 = data.get('madde2', '')
        template.madde3 = data.get('madde3', '')
        template.madde4 = data.get('madde4', '')
        template.madde5 = data.get('madde5', '')
        template.madde6 = data.get('madde6', '')
        template.madde7 = data.get('madde7', '')
        template.madde8 = data.get('madde8', '')
        template.madde9 = data.get('madde9', '')
        template.madde10 = data.get('madde10', '')
        template.updated_by = current_user.id
        template.is_active = True
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Taslak başarıyla kaydedildi'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/kayitli_ornek_sozlesmeler')
@login_required
@permission_required('ornek_sozlesmeler')
def kayitli_ornek_sozlesmeler_sayfasi():
    return render_template('kayitli_sozlesmeler.html')

# --- Örnek Sözleşme Kaydetme ve Listeleme API Route'ları ---
@app.route('/api/ornek_sozlesmeler/kaydet', methods=['POST'])
@login_required
@permission_required('ornek_sozlesmeler')
def api_ornek_sozlesme_kaydet():
    data = request.get_json()
    
    # JavaScript'ten gelen alan adlarını kontrol et (both old and new field names supported)
    muvekkil_adi = data.get('muvekkil_adi') or data.get('muvekkil_adresi')  # fallback for old name
    sozlesme_tarihi_str = data.get('sozlesme_tarihi_str') or data.get('sozlesme_tarihi')
    icerik_json = data.get('icerik_json')
    
    # Sözleşme adını müvekkil adından otomatik oluştur
    sozlesme_adi = f"{muvekkil_adi}_Avukatlik_Sozlesmesi_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if muvekkil_adi else None
    
    if not data or not icerik_json or not muvekkil_adi or not sozlesme_tarihi_str:
        return jsonify({'success': False, 'message': 'Eksik veri: İçerik, müvekkil adı ve sözleşme tarihi gereklidir.'}), 400

    if not sozlesme_adi:
        return jsonify({'success': False, 'message': 'Sözleşme adı oluşturulamadı.'}), 400
    
    try:
        sozlesme_tarihi_dt = datetime.strptime(sozlesme_tarihi_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'message': 'Geçersiz sözleşme tarihi formatı. YYYY-AA-GG şeklinde olmalıdır.'}), 400

    try:
        yeni_sozlesme = OrnekSozlesme(
            sozlesme_adi=sozlesme_adi,
            muvekkil_adi=muvekkil_adi,
            sozlesme_tarihi=sozlesme_tarihi_dt,
            icerik_json=json.dumps(icerik_json), # pdfmake içeriğini JSON string olarak sakla
            user_id=current_user.id
        )
        db.session.add(yeni_sozlesme)
        db.session.commit()
        log_activity(
            activity_type='Örnek Sözleşme Kaydedildi',
            description=f'Yeni örnek sözleşme sisteme kaydedildi: {yeni_sozlesme.sozlesme_adi}',
            user_id=current_user.id
        )
        return jsonify({'success': True, 'message': 'Sözleşme başarıyla kaydedildi.', 'sozlesme_id': yeni_sozlesme.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ornek_sozlesmeler/kayitli', methods=['GET'])
@login_required
@permission_required('ornek_sozlesmeler')
def api_kayitli_ornek_sozlesmeleri_listele():
    try:
        # Yetki kontrolü - ornek_sozlesmeler yetkisi olanlar tüm sözleşmeleri görebilir
        if current_user.has_permission('ornek_sozlesmeler') or current_user.is_admin:
            sozlesmeler = OrnekSozlesme.query.order_by(OrnekSozlesme.olusturulma_tarihi.desc()).all()
        else:
            sozlesmeler = OrnekSozlesme.query.filter_by(user_id=current_user.id).order_by(OrnekSozlesme.olusturulma_tarihi.desc()).all()
        data = [{
            'id': sozlesme.id,
            'muvekkil_adi': sozlesme.muvekkil_adi, # Doğru alan adı ve anahtar
            'sozlesme_adi': sozlesme.sozlesme_adi, # Eklendi
            'sozlesme_tarihi': sozlesme.sozlesme_tarihi.strftime('%d.%m.%Y') if sozlesme.sozlesme_tarihi else None, # Display format
            'icerik_json': json.loads(sozlesme.icerik_json) if sozlesme.icerik_json else None # JSON string'i parse et
        } for sozlesme in sozlesmeler]
        return jsonify({'success': True, 'sozlesmeler': data})
    except Exception as e:
        app.logger.error(f"Kayıtlı örnek sözleşmeler listelenirken hata oluştu: {e}")
        app.logger.error(traceback.format_exc()) # Hata detaylarını logla
        return jsonify({'success': False, 'message': f'Kayıtlı örnek sözleşmeler listelenirken bir hata oluştu: {str(e)}'}), 500

@app.route('/api/ornek_sozlesmeler/guncelle/<int:sozlesme_id>', methods=['PUT'])
@login_required
@permission_required('ornek_sozlesmeler')
def api_ornek_sozlesme_guncelle(sozlesme_id):
    try:
        data = request.get_json()
        # Yetki kontrolü - ornek_sozlesmeler yetkisi olanlar tüm sözleşmelere erişebilir
        if current_user.has_permission('ornek_sozlesmeler') or current_user.is_admin:
            sozlesme = OrnekSozlesme.query.get_or_404(sozlesme_id)
        else:
            sozlesme = OrnekSozlesme.query.filter_by(id=sozlesme_id, user_id=current_user.id).first_or_404()
        
        # JavaScript'ten gelen alan adlarını kontrol et
        muvekkil_adi = data.get('muvekkil_adi') or data.get('muvekkil_adresi')
        sozlesme_tarihi_str = data.get('sozlesme_tarihi_str') or data.get('sozlesme_tarihi')
        icerik_json = data.get('icerik_json')
        
        if muvekkil_adi:
            sozlesme.muvekkil_adi = muvekkil_adi
        if sozlesme_tarihi_str:
            sozlesme.sozlesme_tarihi = datetime.strptime(sozlesme_tarihi_str, '%Y-%m-%d').date()
        if icerik_json:
            sozlesme.icerik_json = json.dumps(icerik_json)
        
        db.session.commit()
        log_activity(
            activity_type='Örnek Sözleşme Güncellendi',
            description=f'{sozlesme.sozlesme_adi} adlı sözleşme güncellendi.',
            user_id=current_user.id
        )
        return jsonify({"success": True, "message": "Sözleşme başarıyla güncellendi."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ornek_sozlesmeler/kayitli/<int:sozlesme_id>', methods=['GET'])
@login_required
# @permission_required('kayitli_ornek_sozlesmeleri_goruntule') # İzin eklenebilir
def api_kayitli_ornek_sozlesme_detay(sozlesme_id):
    try:
        # Yetki kontrolü - ornek_sozlesmeler yetkisi olanlar tüm sözleşmelere erişebilir
        if current_user.has_permission('ornek_sozlesmeler') or current_user.is_admin:
            sozlesme = OrnekSozlesme.query.get_or_404(sozlesme_id)
        else:
            sozlesme = OrnekSozlesme.query.filter_by(id=sozlesme_id, user_id=current_user.id).first_or_404()
        return jsonify({
            'success': True, 
            'sozlesme': {
                'id': sozlesme.id, 
                'sozlesme_adi': sozlesme.sozlesme_adi, 
                'muvekkil_adi': sozlesme.muvekkil_adi,
                'sozlesme_tarihi': sozlesme.sozlesme_tarihi.strftime('%Y-%m-%d') if sozlesme.sozlesme_tarihi else None, # Form için YYYY-AA-GG
                'sozlesme_tarihi_str': sozlesme.sozlesme_tarihi.strftime('%Y-%m-%d') if sozlesme.sozlesme_tarihi else None, # Alternative format
                'icerik_json': json.loads(sozlesme.icerik_json) if sozlesme.icerik_json else None, # JSON string'i parse et
                'olusturulma_tarihi': sozlesme.olusturulma_tarihi.strftime('%d.%m.%Y %H:%M')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ornek_sozlesmeler/kayitli/<int:sozlesme_id>', methods=['DELETE'])
@login_required
# @permission_required('kayitli_ornek_sozlesme_sil') # İzin eklenebilir
def api_kayitli_ornek_sozlesme_sil(sozlesme_id):
    try:
        # Yetki kontrolü - ornek_sozlesmeler yetkisi olanlar tüm sözleşmelere erişebilir
        if current_user.has_permission('ornek_sozlesmeler') or current_user.is_admin:
            sozlesme = OrnekSozlesme.query.get_or_404(sozlesme_id)
        else:
            sozlesme = OrnekSozlesme.query.filter_by(id=sozlesme_id, user_id=current_user.id).first_or_404()
        sozlesme_adi_log = sozlesme.sozlesme_adi
        db.session.delete(sozlesme)
        db.session.commit()
        log_activity(
            activity_type='Örnek Sözleşme Silindi',
            description=f'Kaydedilmiş örnek sözleşme silindi: {sozlesme_adi_log}',
            user_id=current_user.id
        )
        return jsonify({'success': True, 'message': 'Sözleşme başarıyla silindi.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sozlesme_pdf/<int:sozlesme_id>')
@login_required
def api_sozlesme_pdf(sozlesme_id):
    """Sözleşmeyi PDF olarak döndür"""
    try:
        # Yetki kontrolü - ornek_sozlesmeler yetkisi olanlar tüm sözleşmelere erişebilir
        if current_user.has_permission('ornek_sozlesmeler') or current_user.is_admin:
            sozlesme = OrnekSozlesme.query.get_or_404(sozlesme_id)
        else:
            sozlesme = OrnekSozlesme.query.filter_by(id=sozlesme_id, user_id=current_user.id).first_or_404()
        
        # JSON içeriğini parse et
        icerik = json.loads(sozlesme.icerik_json) if sozlesme.icerik_json else {}
        
        # PDF HTML içeriği
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{sozlesme.sozlesme_adi}</title>
            <style>
                body {{ font-family: 'Arial', sans-serif; margin: 40px; line-height: 1.6; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .title {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
                .subtitle {{ font-size: 14px; color: #7f8c8d; margin-top: 10px; }}
                .content {{ margin: 20px 0; }}
                .field {{ margin: 15px 0; padding: 10px; border-left: 3px solid #3498db; }}
                .field-label {{ font-weight: bold; color: #2c3e50; }}
                .field-value {{ color: #34495e; margin-top: 5px; }}
                .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #95a5a6; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">{sozlesme.sozlesme_adi}</div>
                <div class="subtitle">Kaplan Hukuk Bürosu</div>
                <div class="subtitle">Müvekkil: {sozlesme.muvekkil_adi or 'Belirtilmemiş'}</div>
                <div class="subtitle">Sözleşme Tarihi: {sozlesme.sozlesme_tarihi.strftime('%d.%m.%Y') if sozlesme.sozlesme_tarihi else 'Belirtilmemiş'}</div>
            </div>
            
            <div class="content">
        """
        
        # İçerikteki her alanı ekle
        for key, value in icerik.items():
            if value and str(value).strip():
                # Anahtar ismini daha okunabilir hale getir
                label = key.replace('_', ' ').title()
                html_content += f"""
                <div class="field">
                    <div class="field-label">{label}:</div>
                    <div class="field-value">{value}</div>
                </div>
                """
        
        html_content += f"""
            </div>
            
            <div class="footer">
                <p>Bu belge Kaplan Hukuk Bürosu tarafından oluşturulmuştur.</p>
                <p>Oluşturma Tarihi: {sozlesme.olusturulma_tarihi.strftime('%d.%m.%Y %H:%M')}</p>
            </div>
        </body>
        </html>
        """
        
        # HTML'i Response olarak döndür
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        print(f"Sözleşme PDF oluşturma hatası: {str(e)}")
        return f"PDF oluşturulurken hata oluştu: {str(e)}", 500

# --- Örnek Sözleşme Kaydetme ve Listeleme API Route'ları SONU ---

# --- Örnek Dilekçe Kategori API Route'ları ---
@app.route('/api/dilekce_kategorileri', methods=['POST'])
@login_required
# @permission_required('ornek_dilekce_kategori_ekle') # İzin eklenebilir
def api_dilekce_kategori_ekle():
    data = request.get_json()
    if not data or not data.get('ad'):
        return jsonify({'success': False, 'message': 'Kategori adı gerekli.'}), 400
    
    kategori_adi = data['ad'].strip()
    if not kategori_adi:
        return jsonify({'success': False, 'message': 'Kategori adı boş olamaz.'}), 400

    if DilekceKategori.query.filter_by(ad=kategori_adi).first():
        return jsonify({'success': False, 'message': 'Bu kategori adı zaten mevcut.'}), 400
    
    try:
        yeni_kategori = DilekceKategori(ad=kategori_adi)
        db.session.add(yeni_kategori)
        db.session.commit()
        log_activity(
            activity_type='Örnek Dilekçe Kategorisi Eklendi',
            description=f'Yeni örnek dilekçe kategorisi eklendi: {yeni_kategori.ad}',
            user_id=current_user.id
        )
        return jsonify({'success': True, 'kategori': {'id': yeni_kategori.id, 'ad': yeni_kategori.ad}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dilekce_kategorileri', methods=['GET'])
@login_required
# @permission_required('ornek_dilekce_kategori_goruntule') # İzin eklenebilir
def api_dilekce_kategorileri_listele():
    try:
        kategoriler = DilekceKategori.query.order_by(DilekceKategori.ad).all()
        return jsonify({'success': True, 'kategoriler': [{'id': kat.id, 'ad': kat.ad} for kat in kategoriler]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dilekce_kategorileri/<int:kategori_id>', methods=['DELETE'])
@login_required
# @permission_required('ornek_dilekce_kategori_sil') # İzin eklenebilir
def api_dilekce_kategori_sil(kategori_id):
    try:
        kategori = DilekceKategori.query.get_or_404(kategori_id)
        
        if OrnekDilekce.query.filter_by(kategori_id=kategori_id).first():
            return jsonify({'success': False, 'message': 'Bu kategoriye ait dilekçeler bulunduğu için silinemez. Önce dilekçeleri silin veya başka bir kategoriye taşıyın.'}), 400

        kategori_adi = kategori.ad
        db.session.delete(kategori)
        db.session.commit()
        log_activity(
            activity_type='Örnek Dilekçe Kategorisi Silindi',
            description=f'Örnek dilekçe kategorisi silindi: {kategori_adi}',
            user_id=current_user.id
        )
        return jsonify({'success': True, 'message': 'Kategori başarıyla silindi.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dilekce_kategorileri/<int:kategori_id>', methods=['PUT'])
@login_required
# @permission_required('ornek_dilekce_kategori_duzenle') # İzin eklenebilir
def api_dilekce_kategori_duzenle(kategori_id):
    data = request.get_json()
    if not data or not data.get('ad'):
        return jsonify({'success': False, 'message': 'Kategori adı gerekli.'}), 400
    
    kategori_adi = data['ad'].strip()
    if not kategori_adi:
        return jsonify({'success': False, 'message': 'Kategori adı boş olamaz.'}), 400

    try:
        kategori = DilekceKategori.query.get_or_404(kategori_id)
        
        # Aynı isimde başka kategori var mı kontrol et
        existing_kategori = DilekceKategori.query.filter(
            DilekceKategori.ad == kategori_adi, 
            DilekceKategori.id != kategori_id
        ).first()
        if existing_kategori:
            return jsonify({'success': False, 'message': 'Bu kategori adı zaten mevcut.'}), 400
        
        eski_ad = kategori.ad
        kategori.ad = kategori_adi
        db.session.commit()
        
        log_activity(
            activity_type='Örnek Dilekçe Kategorisi Güncellendi',
            description=f'Örnek dilekçe kategorisi güncellendi: {eski_ad} → {kategori.ad}',
            user_id=current_user.id
        )
        
        return jsonify({'success': True, 'kategori': {'id': kategori.id, 'ad': kategori.ad}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- Örnek Dilekçe Kategori API Route'ları SONU ---

# --- Örnek Dilekçe CRUD API Route'ları ---
@app.route('/api/ornek_dilekceler', methods=['POST'])
@login_required
# @permission_required('ornek_dilekce_ekle') # İzin eklenebilir
def api_ornek_dilekce_ekle():
    if 'dilekceDosyasi' not in request.files:
        return jsonify({'success': False, 'message': 'Dosya seçilmedi.'}), 400
    
    file = request.files['dilekceDosyasi']
    kategori_id = request.form.get('kategoriId')
    dilekce_adi = request.form.get('dilekceAdi', file.filename) # İsim verilmezse dosya adını kullan

    if not kategori_id:
        return jsonify({'success': False, 'message': 'Kategori seçilmedi.'}), 400
    
    if not dilekce_adi.strip(): # Dosya adı da boş gelebilir diye kontrol
        dilekce_adi = file.filename # Eğer kullanıcı boş yollarsa yine dosya adını kullan
        if not dilekce_adi.strip(): # Dosya adı da boşsa hata ver
             return jsonify({'success': False, 'message': 'Dilekçe adı boş olamaz.'}), 400


    if file.filename == '':
        return jsonify({'success': False, 'message': 'Geçerli bir dosya seçilmedi.'}), 400

    if not allowed_file(file.filename): # ALLOWED_EXTENSIONS'ı kullan
        return jsonify({'success': False, 'message': 'Geçersiz dosya türü.'}), 400
        
    try:
        kategori = DilekceKategori.query.get(kategori_id)
        if not kategori:
            return jsonify({'success': False, 'message': 'Kategori bulunamadı.'}), 404

        # Dosya adını güvenli hale getir ve benzersiz yap
        original_filename = secure_filename(dilekce_adi)
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        # Eğer kullanıcı uzantısız bir isim girdiyse, orijinal dosyanın uzantısını ekle
        if not file_ext and '.' in file.filename:
            original_filename += '.' + file.filename.rsplit('.', 1)[1].lower()
        
        # Benzersiz dosya adı oluştur (kategori adı ve zaman damgası ile)
        # Örn: ihtarnameler_1700000000_ornek_ihtar.docx
        benzersiz_dosya_adi_on_eki = secure_filename(kategori.ad.replace(' ', '_').lower())
        benzersiz_dosya_adi = f"{benzersiz_dosya_adi_on_eki}_{int(pytime.time())}_{original_filename}"
        
        # Yükleme klasörünü oluştur (eğer yoksa)
        upload_klasoru = app.config['ORNEK_DILEKCE_UPLOAD_FOLDER']
        os.makedirs(upload_klasoru, exist_ok=True)
        
        file_path = os.path.join(upload_klasoru, benzersiz_dosya_adi)
        file.save(file_path)

        yeni_dilekce = OrnekDilekce(
            ad=original_filename, # Kullanıcının verdiği veya orijinal dosya adı
            dosya_yolu=benzersiz_dosya_adi, # Kaydedilen benzersiz ad
            kategori_id=kategori_id,
            user_id=current_user.id
        )
        db.session.add(yeni_dilekce)
        db.session.commit()
        
        log_activity(
            activity_type='Örnek Dilekçe Eklendi',
            description=f'Yeni örnek dilekçe eklendi: {yeni_dilekce.ad} (Kategori: {kategori.ad})',
            user_id=current_user.id
        )
        return jsonify({
            'success': True, 
            'dilekce': {
                'id': yeni_dilekce.id, 
                'ad': yeni_dilekce.ad, 
                'kategori': kategori.ad, 
                'kategori_id': kategori.id,
                'tarih': yeni_dilekce.yuklenme_tarihi.strftime('%d.%m.%Y')
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        # Hata durumunda yüklenen dosyayı silmeyi deneyebiliriz
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass # Silme hatasını yoksay
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ornek_dilekceler', methods=['GET'])
@login_required
# @permission_required('ornek_dilekce_goruntule') # İzin eklenebilir
def api_ornek_dilekceleri_listele():
    kategori_id_filter = request.args.get('kategoriId')
    try:
        query = OrnekDilekce.query.join(DilekceKategori).options(db.joinedload(OrnekDilekce.kategori))
        if kategori_id_filter:
            query = query.filter(OrnekDilekce.kategori_id == kategori_id_filter)
        
        dilekceler = query.order_by(OrnekDilekce.yuklenme_tarihi.desc()).all()
        
        return jsonify({
            'success': True, 
            'dilekceler': [{
                'id': d.id, 
                'ad': d.ad, 
                'kategori': d.kategori.ad,
                'kategori_id': d.kategori_id,
                'dosya_yolu': d.dosya_yolu, # Önizleme ve indirme için eklendi
                'tarih': d.yuklenme_tarihi.strftime('%d.%m.%Y')
            } for d in dilekceler]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ornek_dilekceler/<int:dilekce_id>/indir', methods=['GET'])
@login_required
# @permission_required('ornek_dilekce_indir') # İzin eklenebilir
def api_ornek_dilekce_indir(dilekce_id):
    try:
        dilekce = OrnekDilekce.query.get_or_404(dilekce_id)
        
        # CORS header'ları ile birlikte response oluştur
        response = make_response(send_from_directory(
            app.config['ORNEK_DILEKCE_UPLOAD_FOLDER'],
            dilekce.dosya_yolu,
            as_attachment=True,
            download_name=dilekce.ad # İndirilirken görünecek dosya adı
        ))
        
        # CORS header'ları ekle
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Cache-Control'] = 'public, max-age=300'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ornek_dilekceler/<int:dilekce_id>/onizle', methods=['GET'])
@login_required
# @permission_required('ornek_dilekce_onizle') # İzin eklenebilir
def api_ornek_dilekce_onizle(dilekce_id):
    try:
        dilekce = OrnekDilekce.query.get_or_404(dilekce_id)
        filepath = os.path.join(app.config['ORNEK_DILEKCE_UPLOAD_FOLDER'], dilekce.dosya_yolu)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': 'Dosya bulunamadı.'}), 404
        
        # Dosya uzantısını kontrol et
        file_ext = dilekce.dosya_yolu.rsplit('.', 1)[1].lower() if '.' in dilekce.dosya_yolu else ''
        
        print(f"Önizleme istenen dilekçe - ID: {dilekce_id}, Ad: {dilekce.ad}, Uzantı: {file_ext}")
        if os.getenv('DEBUG', 'False').lower() == 'true':
            print(f"DEBUG: DOCX/DOC dosya yolu: {filepath}")
            print(f"DEBUG: Dosya mevcut mu? {os.path.exists(filepath)}")
        
        # UDF dosyası ise UDF viewer endpoint'ine yönlendir
        if file_ext == 'udf':
            print(f"UDF dosyası tespit edildi, UDF viewer'a yönlendiriliyor: {dilekce_id}")
            return redirect(url_for('direct_view_udf_dilekce', dilekce_id=dilekce_id))
        
        # PDF dosyalar için doğrudan dosyayı gönder
        elif file_ext == 'pdf':
            print(f"PDF dosyası tespit edildi, doğrudan gönderiliyor: {dilekce.ad}")
            return send_file(filepath, mimetype='application/pdf')
        
        # TXT dosyalar için doğrudan gönder
        elif file_ext == 'txt':
            print(f"TXT dosyası tespit edildi, doğrudan gönderiliyor: {dilekce.ad}")
            return send_file(filepath, mimetype='text/plain')
        
        # DOC/DOCX dosyalar için HTML önizleme
        elif file_ext in ['doc', 'docx']:
            print(f"DOC/DOCX dosyası tespit edildi, HTML önizleme yapılacak: {dilekce.ad}")
            return redirect(url_for('api_ornek_dilekce_html_onizle', dilekce_id=dilekce_id))
        
        # Diğer dosya türleri için doğrudan gönder
        else:
            print(f"Genel dosya türü tespit edildi ({file_ext}), doğrudan gönderiliyor: {dilekce.ad}")
            return send_file(filepath, mimetype=None)
        
    except Exception as e:
        print(f"Dilekçe önizleme hatası (ID: {dilekce_id}): {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/ornek_dilekceler/<int:dilekce_id>/html_onizle', methods=['GET'])
@login_required
@permission_required('ornek_dilekceler')
def api_ornek_dilekce_html_onizle(dilekce_id):
    """DOC/DOCX dosyalarını HTML olarak önizle"""
    try:
        dilekce = OrnekDilekce.query.get_or_404(dilekce_id)
        filepath = os.path.join(app.config['ORNEK_DILEKCE_UPLOAD_FOLDER'], dilekce.dosya_yolu)
        
        if not os.path.exists(filepath):
            return "Dosya bulunamadı", 404
        
        file_ext = dilekce.dosya_yolu.rsplit('.', 1)[1].lower() if '.' in dilekce.dosya_yolu else ''
        
        if file_ext not in ['doc', 'docx']:
            return "Bu dosya türü desteklenmiyor", 400
        
        try:
            # DOCX dosyaları için mammoth kullan
            if file_ext == 'docx':
                import mammoth
                with open(filepath, 'rb') as f:
                    result = mammoth.convert_to_html(f)
                    html_content = result.value
                    
                # Basit HTML sayfası oluştur
                full_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>{dilekce.ad} - Önizleme</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            margin: 20px;
                            line-height: 1.6;
                            background-color: #f5f5f5;
                        }}
                        .document-container {{
                            background: white;
                            padding: 30px;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            max-width: 800px;
                            margin: 0 auto;
                        }}
                        .document-header {{
                            border-bottom: 2px solid #007bff;
                            padding-bottom: 15px;
                            margin-bottom: 25px;
                        }}
                        .document-title {{
                            color: #007bff;
                            font-size: 24px;
                            font-weight: bold;
                            margin: 0;
                        }}
                        .document-info {{
                            color: #666;
                            font-size: 14px;
                            margin-top: 5px;
                        }}
                        .document-content {{
                            color: #333;
                        }}
                        .document-content p {{
                            margin-bottom: 15px;
                        }}
                        .document-content h1, .document-content h2, .document-content h3 {{
                            color: #007bff;
                            margin-top: 25px;
                            margin-bottom: 15px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="document-container">
                        <div class="document-header">
                            <div class="document-title">{dilekce.ad}</div>
                            <div class="document-info">Word Belgesi Önizlemesi</div>
                        </div>
                        <div class="document-content">
                            {html_content}
                        </div>
                    </div>
                </body>
                </html>
                """
                
                return Response(full_html, mimetype='text/html')
                
            # DOC dosyaları için şimdilik hata mesajı
            else:
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Önizleme Hatası</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            margin: 50px;
                            text-align: center;
                            background-color: #f5f5f5;
                        }}
                        .error-container {{
                            background: white;
                            padding: 40px;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            max-width: 500px;
                            margin: 0 auto;
                        }}
                        .error-icon {{
                            font-size: 64px;
                            color: #ffc107;
                            margin-bottom: 20px;
                        }}
                        .error-title {{
                            color: #333;
                            font-size: 24px;
                            margin-bottom: 15px;
                        }}
                        .error-message {{
                            color: #666;
                            line-height: 1.6;
                            margin-bottom: 25px;
                        }}
                        .download-btn {{
                            background: #007bff;
                            color: white;
                            padding: 12px 24px;
                            border: none;
                            border-radius: 5px;
                            text-decoration: none;
                            display: inline-block;
                            font-size: 16px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <div class="error-icon">📄</div>
                        <div class="error-title">DOC Dosyası</div>
                        <div class="error-message">
                            Eski Word formatındaki (.doc) dosyalar şu anda önizlenemiyor.<br>
                            Dosyayı indirip bilgisayarınızda açabilirsiniz.
                        </div>
                        <a href="/api/ornek_dilekceler/{dilekce_id}/indir" class="download-btn">
                            Dosyayı İndir
                        </a>
                    </div>
                </body>
                </html>
                """
                
                return Response(error_html, mimetype='text/html')
                
        except ImportError:
            # mammoth kurulu değilse
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Önizleme Hatası</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 50px;
                        text-align: center;
                        background-color: #f5f5f5;
                    }}
                    .error-container {{
                        background: white;
                        padding: 40px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        max-width: 500px;
                        margin: 0 auto;
                    }}
                    .error-icon {{
                        font-size: 64px;
                        color: #dc3545;
                        margin-bottom: 20px;
                    }}
                    .error-title {{
                        color: #333;
                        font-size: 24px;
                        margin-bottom: 15px;
                    }}
                    .error-message {{
                        color: #666;
                        line-height: 1.6;
                        margin-bottom: 25px;
                    }}
                    .download-btn {{
                        background: #007bff;
                        color: white;
                        padding: 12px 24px;
                        border: none;
                        border-radius: 5px;
                        text-decoration: none;
                        display: inline-block;
                        font-size: 16px;
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-icon">⚠️</div>
                    <div class="error-title">Önizleme Kullanılamıyor</div>
                    <div class="error-message">
                        Word belgesi önizlemesi için gerekli bileşenler yüklü değil.<br>
                        Dosyayı indirip bilgisayarınızda açabilirsiniz.
                    </div>
                    <a href="/api/ornek_dilekceler/{dilekce_id}/indir" class="download-btn">
                        Dosyayı İndir
                    </a>
                </div>
            </body>
            </html>
            """
            
            return Response(error_html, mimetype='text/html')
            
        except Exception as e:
            print(f"DOCX HTML dönüşüm hatası: {str(e)}")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Önizleme Hatası</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 50px;
                        text-align: center;
                        background-color: #f5f5f5;
                    }}
                    .error-container {{
                        background: white;
                        padding: 40px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        max-width: 500px;
                        margin: 0 auto;
                    }}
                    .error-icon {{
                        font-size: 64px;
                        color: #dc3545;
                        margin-bottom: 20px;
                    }}
                    .error-title {{
                        color: #333;
                        font-size: 24px;
                        margin-bottom: 15px;
                    }}
                    .error-message {{
                        color: #666;
                        line-height: 1.6;
                        margin-bottom: 25px;
                    }}
                    .download-btn {{
                        background: #007bff;
                        color: white;
                        padding: 12px 24px;
                        border: none;
                        border-radius: 5px;
                        text-decoration: none;
                        display: inline-block;
                        font-size: 16px;
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-icon">❌</div>
                    <div class="error-title">Önizleme Hatası</div>
                    <div class="error-message">
                        Bu dosya önizlenirken bir hata oluştu.<br>
                        Dosyayı indirip bilgisayarınızda açabilirsiniz.
                    </div>
                    <a href="/api/ornek_dilekceler/{dilekce_id}/indir" class="download-btn">
                        Dosyayı İndir
                    </a>
                </div>
            </body>
            </html>
            """
            
            return Response(error_html, mimetype='text/html')
            
    except Exception as e:
        print(f"Dilekçe HTML önizleme hatası (ID: {dilekce_id}): {str(e)}")
        return f"Dosya önizlenirken hata oluştu: {str(e)}", 500


@app.route('/api/ornek_dilekceler/<int:dilekce_id>', methods=['DELETE'])
@login_required
@permission_required('ornek_dilekceler')
def api_ornek_dilekce_sil(dilekce_id):
    try:
        dilekce = OrnekDilekce.query.get_or_404(dilekce_id)
        dosya_yolu = os.path.join(app.config['ORNEK_DILEKCE_UPLOAD_FOLDER'], dilekce.dosya_yolu)
        dilekce_adi = dilekce.ad
        kategori_adi = dilekce.kategori.ad

        db.session.delete(dilekce)
        # Veritabanından silme başarılı olursa dosyayı da sil
        if os.path.exists(dosya_yolu):
            try:
                os.remove(dosya_yolu)
            except OSError as e:
                # Dosya silme hatasını logla ama işlemi durdurma (belki dosya açık vs.)
                print(f"Örnek dilekçe dosyası silinirken hata (id: {dilekce_id}, path: {dosya_yolu}): {e}")
                # db.session.rollback() # Eğer dosya silinemezse işlemi geri almak istenirse
                # return jsonify({'success': False, 'message': f'Dosya silinemedi: {e}'}), 500
        
        db.session.commit() # Dosya silme başarılı olmasa bile DB değişikliğini commit et
        log_activity(
            activity_type='Örnek Dilekçe Silindi',
            description=f'Örnek dilekçe silindi: {dilekce_adi} (Kategori: {kategori_adi})',
            user_id=current_user.id
        )
        return jsonify({'success': True, 'message': 'Dilekçe başarıyla silindi.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ornek_dilekceler/<int:dilekce_id>/duzenle', methods=['PUT'])
@login_required
@permission_required('ornek_dilekceler')
def api_ornek_dilekce_duzenle(dilekce_id):
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Güncelleme verisi gerekli.'}), 400

    try:
        dilekce = OrnekDilekce.query.get_or_404(dilekce_id)
        eski_ad = dilekce.ad
        eski_kategori = dilekce.kategori.ad
        
        # Yeni adı güncelle
        if 'yeni_ad' in data and data['yeni_ad']:
            yeni_ad = data['yeni_ad'].strip()
            if yeni_ad:
                # Yeni adı güvenli hale getir ve uzantısını koru
                guvenli_yeni_ad = secure_filename(yeni_ad)
                original_ext = dilekce.ad.rsplit('.', 1)[1].lower() if '.' in dilekce.ad else ''
                yeni_ad_ext = guvenli_yeni_ad.rsplit('.', 1)[1].lower() if '.' in guvenli_yeni_ad else ''

                if original_ext and not yeni_ad_ext:
                    guvenli_yeni_ad += '.' + original_ext
                elif yeni_ad_ext and original_ext and yeni_ad_ext != original_ext:
                    guvenli_yeni_ad = guvenli_yeni_ad.rsplit('.',1)[0] + '.' + original_ext

                dilekce.ad = guvenli_yeni_ad

        # Kategoriyi güncelle
        if 'kategori_id' in data and data['kategori_id']:
            yeni_kategori = DilekceKategori.query.get(data['kategori_id'])
            if not yeni_kategori:
                return jsonify({'success': False, 'message': 'Seçilen kategori bulunamadı.'}), 404
            dilekce.kategori_id = data['kategori_id']

        db.session.commit()
        
        log_activity(
            activity_type='Örnek Dilekçe Güncellendi',
            description=f'Örnek dilekçe güncellendi: "{eski_ad}" -> "{dilekce.ad}" (Kategori: "{eski_kategori}" -> "{dilekce.kategori.ad}")',
            user_id=current_user.id
        )
        return jsonify({
            'success': True, 
            'message': 'Dilekçe başarıyla güncellendi.',
            'dilekce': {
                'id': dilekce.id, 
                'ad': dilekce.ad, 
                'kategori': dilekce.kategori.ad,
                'kategori_id': dilekce.kategori_id,
                'dosya_yolu': dilekce.dosya_yolu,
                'tarih': dilekce.yuklenme_tarihi.strftime('%d.%m.%Y')
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ornek_dilekceler/<int:dilekce_id>/duzenle_ad', methods=['PUT']) # POST yerine PUT daha uygun
@login_required
@permission_required('ornek_dilekceler')
def api_ornek_dilekce_ad_duzenle(dilekce_id):
    data = request.get_json()
    if not data or not data.get('yeni_ad'):
        return jsonify({'success': False, 'message': 'Yeni ad gerekli.'}), 400
    
    yeni_ad = data['yeni_ad'].strip()
    if not yeni_ad:
        return jsonify({'success': False, 'message': 'Yeni ad boş olamaz.'}), 400

    try:
        dilekce = OrnekDilekce.query.get_or_404(dilekce_id)
        eski_ad = dilekce.ad
        
        # Yeni adı güvenli hale getir ve uzantısını koru
        guvenli_yeni_ad = secure_filename(yeni_ad)
        original_ext = dilekce.ad.rsplit('.', 1)[1].lower() if '.' in dilekce.ad else ''
        yeni_ad_ext = guvenli_yeni_ad.rsplit('.', 1)[1].lower() if '.' in guvenli_yeni_ad else ''

        if original_ext and not yeni_ad_ext: # Kullanıcı uzantısız yeni ad girdiyse
            guvenli_yeni_ad += '.' + original_ext
        elif yeni_ad_ext and original_ext and yeni_ad_ext != original_ext: # Farklı uzantı girdiyse, orijinali koru
             # Ya da hata ver: return jsonify({'success': False, 'message': 'Dosya uzantısı değiştirilemez.'}), 400
             guvenli_yeni_ad = guvenli_yeni_ad.rsplit('.',1)[0] + '.' + original_ext


        dilekce.ad = guvenli_yeni_ad
        db.session.commit()
        
        log_activity(
            activity_type='Örnek Dilekçe Adı Güncellendi',
            description=f'Örnek dilekçe adı güncellendi: "{eski_ad}" -> "{dilekce.ad}" (Kategori: {dilekce.kategori.ad})',
            user_id=current_user.id
        )
        return jsonify({
            'success': True, 
            'message': 'Dilekçe adı başarıyla güncellendi.',
            'dilekce': {
                'id': dilekce.id, 
                'ad': dilekce.ad, 
                'kategori': dilekce.kategori.ad,
                'kategori_id': dilekce.kategori_id,
                'dosya_yolu': dilekce.dosya_yolu,
                'tarih': dilekce.yuklenme_tarihi.strftime('%d.%m.%Y')
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
# --- Örnek Dilekçe CRUD API Route'ları SONU ---

# Yargı Kararları Arama Motoru Route'ları
@app.route('/yargi_kararlari_arama')
@login_required
@permission_required('yargi_kararlari_arama')
def yargi_kararlari_arama():
    """Yargı kararları arama ana sayfası"""
    return render_template('yargi_kararlari_arama.html')

@app.route('/api/yargi_arama', methods=['POST'])
@login_required
@csrf.exempt
def api_yargi_arama():
    """Yargı kararları arama API endpoint'i"""
    try:
        print(f"API çağrısı alındı: {request.method}")  # Debug
        data = request.get_json()
        print(f"Alınan veri: {data}")  # Debug
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Veri alınamadı.'
            }), 400
            
        keyword = data.get('keyword', '')
        court_type = data.get('court_type', 'all')
        case_year = data.get('case_year', '')
        decision_year = data.get('decision_year', '')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        page_number = int(data.get('page_number', 1))
        page_size = int(data.get('page_size', 10))
        
        print(f"Arama parametreleri: keyword={keyword}, court_type={court_type}")  # Debug
        
        # Arama servisini kullan
        from yargi_integration import search_yargi_kararlari
        
        search_results = search_yargi_kararlari(
            keyword=keyword,
            court_type=court_type,
            court_unit=data.get('court_unit', ''),
            case_year=case_year,
            decision_year=decision_year,
            start_date=start_date,
            end_date=end_date,
            page_number=page_number,
            page_size=page_size
        )
        
        # Sonuçları JSON formatına çevir - doğrudan döndür
        results_json = search_results
        
        # Aktivite logla
        log_activity('yargi_arama', f'Yargı kararları arandı: {keyword}', current_user.id)
        
        return jsonify({
            'success': True,
            'data': results_json,
            'pagination': results_json.get('pagination', {})
        })
        
    except Exception as e:
        logger.error(f"Yargı arama API hatası: {e}")
        return jsonify({
            'success': False,
            'error': 'Arama işlemi sırasında bir hata oluştu.'
        }), 500

@app.route('/api/yargi_mahkeme_secenekleri')
@login_required
@csrf.exempt
def api_yargi_mahkeme_secenekleri():
    """Mahkeme seçeneklerini döndürür"""
    try:
        from yargi_integration import get_court_options
        
        options = get_court_options()
        return jsonify(options)
    except Exception as e:
        logger.error(f"Mahkeme seçenekleri API hatası: {e}")
        return jsonify({
            'success': False,
            'error': 'Mahkeme seçenekleri alınamadı.'
        }), 500

@app.route('/ai_avukat')
@login_required
@permission_required('ai_avukat')
def ai_avukat():
    """AI Avukat sohbet sayfası"""
    return render_template('ai_avukat.html')

@app.route('/api/ai_avukat/sohbet', methods=['POST'])
@login_required
@permission_required('ai_avukat')
@csrf.exempt
def api_ai_avukat_sohbet():
    """AI Avukat ile sohbet API"""
    try:
        data = request.get_json()
        kullanici_mesaji = data.get('mesaj', '').strip()
        sohbet_id = data.get('sohbet_id', None)
        
        if not kullanici_mesaji:
            return jsonify({'success': False, 'error': 'Mesaj boş olamaz'})
        
        # Google AI API ile sohbet
        ai_yaniti = generate_ai_response(kullanici_mesaji)
        mesaj_zamani = datetime.now().strftime('%H:%M')
        
        # Sohbet geçmişine kaydet (eğer sohbet_id varsa)
        if sohbet_id:
            from models import AISohbetGecmisi
            sohbet = AISohbetGecmisi.query.filter_by(id=sohbet_id, user_id=current_user.id).first()
            if sohbet:
                # Mevcut sohbet verilerini güncelle
                sohbet_data = json.loads(sohbet.sohbet_verisi) if sohbet.sohbet_verisi else []
                sohbet_data.extend([
                    {
                        'tip': 'kullanici',
                        'mesaj': kullanici_mesaji,
                        'zaman': mesaj_zamani
                    },
                    {
                        'tip': 'ai',
                        'mesaj': ai_yaniti,
                        'zaman': mesaj_zamani
                    }
                ])
                
                sohbet.sohbet_verisi = json.dumps(sohbet_data, ensure_ascii=False)
                sohbet.mesaj_sayisi = len(sohbet_data)
                # Türkiye saatiyle güncelleme tarihi
                turkey_tz = timezone(timedelta(hours=3))
                sohbet.guncelleme_tarihi = datetime.now(turkey_tz)
                db.session.commit()
        
        # Sohbet logunu kaydet
        log_activity('AI Avukat Sohbet', f'Kullanıcı: "{kullanici_mesaji[:50]}..."', current_user.id)
        
        return jsonify({
            'success': True, 
            'ai_yaniti': ai_yaniti,
            'mesaj_zamani': mesaj_zamani
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai_avukat/sohbet_gecmisi', methods=['GET'])
@login_required
@permission_required('ai_avukat')
def api_ai_sohbet_gecmisi_listele():
    """Kullanıcının sohbet geçmişlerini listele"""
    try:
        from models import AISohbetGecmisi
        
        sohbetler = AISohbetGecmisi.query.filter_by(user_id=current_user.id).order_by(
            AISohbetGecmisi.guncelleme_tarihi.desc()
        ).all()
        
        sohbet_listesi = []
        for sohbet in sohbetler:
            sohbet_dict = sohbet.to_dict()
            # Sadece özet bilgileri gönder, tam sohbet verisini değil
            sohbet_listesi.append({
                'id': sohbet_dict['id'],
                'baslik': sohbet_dict['baslik'],
                'mesaj_sayisi': sohbet_dict['mesaj_sayisi'],
                'olusturulma_tarihi': sohbet_dict['olusturulma_tarihi'],
                'guncelleme_tarihi': sohbet_dict['guncelleme_tarihi']
            })
        
        return jsonify({
            'success': True,
            'sohbetler': sohbet_listesi
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai_avukat/sohbet_gecmisi/<int:sohbet_id>', methods=['GET'])
@login_required
@permission_required('ai_avukat')
def api_ai_sohbet_gecmisi_detay(sohbet_id):
    """Belirli bir sohbet geçmişinin detayını getir"""
    try:
        from models import AISohbetGecmisi
        
        sohbet = AISohbetGecmisi.query.filter_by(
            id=sohbet_id, 
            user_id=current_user.id
        ).first()
        
        if not sohbet:
            return jsonify({'success': False, 'error': 'Sohbet bulunamadı'})
        
        return jsonify({
            'success': True,
            'sohbet': sohbet.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai_avukat/sohbet_gecmisi', methods=['POST'])
@login_required
@permission_required('ai_avukat')
@csrf.exempt
def api_ai_sohbet_gecmisi_kaydet():
    """Yeni sohbet geçmişi kaydet"""
    try:
        from models import AISohbetGecmisi
        
        # sendBeacon ve normal POST isteklerini destekle
        try:
            data = request.get_json()
            if data is None:
                # sendBeacon için raw data okuma
                raw_data = request.get_data()
                if raw_data:
                    data = json.loads(raw_data.decode('utf-8'))
                else:
                    data = {}
        except Exception:
            # JSON parse hatası durumunda boş dict döndür
            data = {}
        
        baslik = data.get('baslik', '').strip()
        sohbet_verisi = data.get('sohbet_verisi', [])
        
        if not baslik:
            # Otomatik başlık oluştur
            if sohbet_verisi and len(sohbet_verisi) > 0:
                ilk_mesaj = sohbet_verisi[0].get('mesaj', '')[:50]
                baslik = f"Sohbet - {ilk_mesaj}..." if ilk_mesaj else f"Sohbet - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            else:
                baslik = f"Sohbet - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        # Yeni sohbet geçmişi oluştur
        yeni_sohbet = AISohbetGecmisi(
            baslik=baslik,
            sohbet_verisi=json.dumps(sohbet_verisi, ensure_ascii=False),
            mesaj_sayisi=len(sohbet_verisi),
            user_id=current_user.id
        )
        
        db.session.add(yeni_sohbet)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sohbet_id': yeni_sohbet.id,
            'message': 'Sohbet geçmişi kaydedildi'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai_avukat/sohbet_gecmisi/<int:sohbet_id>', methods=['DELETE'])
@login_required
@permission_required('ai_avukat')
@csrf.exempt
def api_ai_sohbet_gecmisi_sil(sohbet_id):
    """Sohbet geçmişini sil"""
    try:
        from models import AISohbetGecmisi
        
        sohbet = AISohbetGecmisi.query.filter_by(
            id=sohbet_id, 
            user_id=current_user.id
        ).first()
        
        if not sohbet:
            return jsonify({'success': False, 'error': 'Sohbet bulunamadı'})
        
        baslik = sohbet.baslik
        db.session.delete(sohbet)
        db.session.commit()
        
        # Log kaydı
        log_activity('AI Sohbet Silindi', f'Sohbet geçmişi silindi: "{baslik}"', current_user.id)
        
        return jsonify({
            'success': True,
            'message': 'Sohbet geçmişi silindi'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

def generate_ai_response(kullanici_mesaji):
    """Google Gemini AI ile yanıt üretir"""
    try:
        # Google Gemini API integration
        # API anahtarını environment variable'dan al
        import os
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        
        if not gemini_api_key:
            return """**API Anahtarı Gerekli!**

Bu özelliği kullanabilmek için Google Gemini API anahtarınızı sistem ortam değişkenlerine eklemeniz gerekmektedir.

**Nasıl API Anahtarı Alınır:**
1. https://makersuite.google.com/app/apikey adresine gidin
2. Google hesabınızla giriş yapın
3. "Create API Key" butonuna tıklayın
4. API anahtarınızı kopyalayın
5. Sistem ortam değişkenlerine `GEMINI_API_KEY` olarak ekleyin

**Geçici Çözüm:** Şu anda yerleşik bilgi tabanımla size yardımcı olabilirim. Hangi hukuk alanında sorununuz var?"""

        try:
            import google.generativeai as genai
            
            # Gemini'yi yapılandır
            genai.configure(api_key=gemini_api_key)
            
            # Model oluştur (güncel model adı)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Türk hukuku uzmanı sistem prompt'u
            system_prompt = """Sen Türkiye Cumhuriyeti hukuk sisteminde çok uzman çok bilgili bir avukat asistanısın. Kullanıcıların (kullanıcılar da avukat) hukuki sorularını Türk hukuku kapsamında yanıtlaman gerekiyor.

Özellik alanların:
- Türk hukukundaki her kanun, alan, konu, tüzük, yönetmelik, içtihat.

Yanıtlarında:
1. Konuyla ilgili kanun maddelerini belirt
2. Pratik öneriler ver
3. Gerekli belgeleri listele
4. Süreçleri açıkla
5. Türkçe hukuk terminolojisi kullan
6. Kullanıcının sorusuna cevap verirken aşırı detaya girip ana sorunun cevabından uzaklaşmamaya dikkat et.

UYARI: Sistemden kullanıcının ad ve soyadını cinsiyetini öğren -eğer öğrenebilirsen- kullanıcıya "ismi"+Bey/Hanım diye hitap et. Öğrenemezsen siz diye hitap et.

Kullanıcı sorusu: """ + kullanici_mesaji

            response = model.generate_content(system_prompt)
            
            if response.text:
                return response.text
            else:
                return generate_fallback_response(kullanici_mesaji)
                
        except ImportError:
            # google-generativeai paketi yüklü değilse
            return """**Google Gemini Kütüphanesi Eksik!**

Google Gemini AI özelliğini kullanabilmek için gerekli kütüphane yüklü değil.

**Çözüm:** Terminal'de şu komutu çalıştırın:
```
pip install google-generativeai
```

Şimdilik yerleşik bilgi tabanımla size yardımcı olabilirim.""" + "\n\n" + generate_fallback_response(kullanici_mesaji)
            
        except Exception as gemini_error:
            logger.error(f"Gemini API hatası: {gemini_error}")
            return f"""**Gemini API Hatası**

Google Gemini ile bağlantı kurulamadı: {str(gemini_error)}

Şimdilik yerleşik bilgi tabanımla size yardımcı olabilirim.""" + "\n\n" + generate_fallback_response(kullanici_mesaji)
            
    except Exception as e:
        logger.error(f"AI Response üretme hatası: {e}")
        return generate_fallback_response(kullanici_mesaji)


def generate_fallback_response(kullanici_mesaji):
    """Gemini kullanılamadığında fallback yanıt sistemi"""
    mesaj_lower = kullanici_mesaji.lower()
    
    if any(word in mesaj_lower for word in ['merhaba', 'selam', 'hello', 'hi']):
        return "Merhaba! Ben AI Avukat asistanınızım. Hukuki sorularınızda size yardımcı olmaktan mutluluk duyarım. Nasıl yardımcı olabilirim?"
    
    elif any(word in mesaj_lower for word in ['boşanma', 'ayrılma', 'nafaka']):
        return """**Boşanma Hukuku** (Türk Medeni Kanunu)

**Boşanma Türleri:**
1. **Anlaşmalı Boşanma** (TMK m.166): Eşlerin karşılıklı rızası ile
2. **Çekişmeli Boşanma** (TMK m.161-165): Evlilik birliğini temelinden sarsacak sebeplerle

**Gerekli Belgeler:**
- Evlilik cüzdanı
- Nüfus kayıt örneği
- Gelir belgesi
- Varsa mal varlığını gösteren belgeler

**Süreç:**
1. Dava dilekçesi hazırlama
2. Mahkemeye başvuru
3. Duruşma süreci
4. Karar

⚖️ **Önemli:** Bu genel bilgidir. Kesin hukuki tavsiye için mutlaka avukata danışın."""
    
    elif any(word in mesaj_lower for word in ['miras', 'vasiyet', 'saklı pay']):
        return """**Miras Hukuku** (Türk Medeni Kanunu)

**Yasal Mirasçılar:**
1. **Birinci zümre:** Çocuklar ve torunlar (TMK m.495)
2. **İkinci zümre:** Ana, baba ve kardeşler (TMK m.496)
3. **Üçüncü zümre:** Büyük ana-baba (TMK m.497)

**Saklı Paylar (TMK m.506):**
- Çocuklar: Miras payının 1/2'si
- Eş: Miras payının 1/4'ü  
- Ana-baba: Miras payının 1/4'ü

**Vasiyet:**
- Tasarruf edilebilir kısım: Saklı pay dışında kalan
- Şekil şartları: Resmi, el yazısı veya sözlü vasiyet

⚖️ **Önemli:** Miras işlemleri için notere başvurun."""
    
    elif any(word in mesaj_lower for word in ['iş', 'işçi', 'işveren', 'tazminat']):
        return """**İş Hukuku** (İş Kanunu No: 4857)

**İşçi Hakları:**
- **Kıdem Tazminatı:** 1 yıl+ çalışma (İş K. m.120)
- **İhbar Tazminatı:** Süresiz sözleşmelerde (İş K. m.17)
- **Yıllık Ücretli İzin:** Yılda en az 14 gün (İş K. m.53)
- **Fazla Mesai:** %50 zamlı ödeme (İş K. m.41)

**İş Sözleşmesi Feshi:**
- **Haklı neden:** Derhal fesih (İş K. m.24-25)
- **Geçerli neden:** İhbarlı fesih (İş K. m.18)
- **Geçersiz fesih:** Tazminat hakkı

**Başvuru Süresi:** 1 yıl (İş K. m.132)

⚖️ **Önemli:** İş davalarında avukat zorunludur."""
    
    elif any(word in mesaj_lower for word in ['ceza', 'suç', 'dava']):
        return """**Ceza Hukuku** (Türk Ceza Kanunu No: 5237)

**Temel Kavramlar:**
- **Suç:** Kanunda tanımlanan ve ceza ile müeyyide altına alınan fiiller
- **Ceza Ehliyeti:** 12 yaş (TCK m.31)
- **Zamanaşımı:** Suçun türüne göre değişir (TCK m.66-67)

**Suç Türleri:**
- Kişiye karşı suçlar (TCK 2. Kısım)
- Topluma karşı suçlar (TCK 3. Kısım)
- Devlete karşı suçlar (TCK 4. Kısım)

**Ceza Davası Süreci:**
1. Soruşturma (Savcılık)
2. Kovuşturma (Mahkeme)
3. Karar

⚖️ **ÇOK ÖNEMLİ:** Ceza davalarında MUTLAKA avukat tutun!"""
    
    elif any(word in mesaj_lower for word in ['kira', 'kiracı', 'ev sahibi']):
        return """**Kira Hukuku** (Türk Borçlar Kanunu m.299-356)

**Kiracı Hakları:**
- **Kira Artışı:** TÜFE + %25 sınırı (6570 s. Kanun)
- **Tahliye Korunması:** Belirli şartlarda
- **Tamirat Hakkı:** Kiralayan yükümlülüğü

**Ev Sahibi Hakları:**
- **Kira Tahsilatı:** Aylık ödeme
- **Tahliye Davası:** Kanuni sebepler (TBK m.315)
- **Teminat:** 3 aya kadar

**Gerekli Belgeler:**
- Kira sözleşmesi
- Ödeme makbuzları
- Tebligat adresi

⚖️ **Önemli:** Kira davaları için icra takibi başlatabilirsiniz."""
    
    else:
        return """**AI Avukat Asistanı** - Türk Hukuku Uzmanı

Size yardımcı olabileceğim hukuk alanları:

🏛️ **Medeni Hukuk**
- Boşanma, velayet, nafaka
- Miras, vasiyet, saklı pay
- Kişilik hakları

👔 **İş Hukuku**
- İşçi hakları ve tazminatlar
- İş sözleşmeleri
- İş kazaları

🏠 **Kira Hukuku**
- Kiracı-ev sahibi ilişkileri
- Kira artışları
- Tahliye davaları

⚖️ **Ceza Hukuku**
- Suçlar ve cezalar
- Ceza davası süreci

💼 **Ticaret Hukuku**
- Şirket kuruluşu
- Ticari işlemler
- Konkordato

Lütfen sorunuzu daha detaylı şekilde sorun veya yukarıdaki alanlardan birini seçin."""

@app.route('/api/yargi_karar_metni', methods=['POST'])
@login_required
@csrf.exempt
def api_yargi_karar_metni():
    """Belirli bir kararın tam metnini getir"""
    try:
        data = request.get_json()
        court_type = data.get('court_type')
        document_id = data.get('document_id')
        document_url = data.get('document_url')
        
        if not court_type or not document_id:
            return jsonify({
                'success': False,
                'error': 'Mahkeme türü ve doküman ID gerekli'
            }), 400
        
        logger.info(f"Karar metni istendi: court_type={court_type}, document_id={document_id}")
        
        from yargi_integration import get_document_content
        
        result = get_document_content(court_type, document_id, document_url)
        
        if result['success']:
            response_data = {
                'success': True,
                'court_type': result['court_type'],
                'source_url': result.get('source_url', '')
            }
            
            # İçerik türüne göre response'u ayarla
            if result.get('content_type') == 'pdf':
                response_data.update({
                    'content_type': 'pdf',
                    'pdf_url': result.get('pdf_url', result.get('source_url', ''))
                })
            elif result.get('content'):
                response_data.update({
                    'content_type': 'text',
                    'content': result['content']
                })
            elif result.get('redirect_url'):
                response_data.update({
                    'redirect_url': result['redirect_url']
                })
            
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
        
    except Exception as e:
        logger.error(f"Karar metni alınırken hata: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== 2FA VE E-POSTA ROUTE'LARI =====

# 2FA QR Kod Oluşturma
@app.route('/generate_2fa_qr', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def generate_2fa_qr():
    """2FA için QR kod oluştur"""
    try:
        import pyotp
        import qrcode
        import base64
        from io import BytesIO
        import json

        user = User.query.get(current_user.id)
        
        # Veritabanındaki JSON'ı yükle
        user_permissions = user.permissions if user.permissions else {}

        # 2FA secret'ı oluştur (eğer yoksa)
        if 'two_factor_secret' not in user_permissions:
            user_permissions['two_factor_secret'] = pyotp.random_base32()
            user.permissions = user_permissions
            db.session.commit()
        
        secret = user_permissions['two_factor_secret']
        
        # TOTP URI oluştur
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="Kaplan Hukuk Otomasyon"
        )
        
        # QR kod oluştur
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # QR kodu base64'e çevir
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qr_code': img_str,
            'secret': secret,
            'message': 'QR kod oluşturuldu. Google Authenticator uygulaması ile tarayın.'
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'message': 'pyotp veya qrcode kütüphanesi eksik. pip install pyotp qrcode[pil] komutu ile yükleyin.'
        }), 500
    except Exception as e:
        logger.error(f"2FA QR kod oluşturma hatası: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'QR kod oluşturulamadı: {str(e)}'
        }), 500

# 2FA Kurulum Doğrulama
@app.route('/verify_2fa_setup', methods=['POST'])
@login_required
@csrf.exempt  
def verify_2fa_setup():
    """2FA kurulum kodunu doğrula ve 2FA'yı etkinleştir"""
    try:
        import pyotp
        
        data = request.get_json()
        code = data.get('token') or data.get('code')
        secret = data.get('secret')
        
        if not code:
            return jsonify({
                'success': False,
                'message': 'Doğrulama kodu gerekli'
            }), 400
        
        if not secret:
            return jsonify({
                'success': False,
                'message': '2FA secret gerekli'
            }), 400
        
        user = User.query.get(current_user.id)
        
        # TOTP ile kodu doğrula
        totp = pyotp.TOTP(secret)
        
        if totp.verify(code, valid_window=1):
            # Kod doğru, 2FA'yı etkinleştir
            if not user.permissions:
                user.permissions = {}
            user.permissions['two_factor_auth'] = True
            user.permissions['two_factor_secret'] = secret
            db.session.commit()
            
            # Log oluştur
            log_activity(
                activity_type='guvenlik_ayar',
                description='İki faktörlü doğrulama başarıyla etkinleştirildi',
                user_id=user.id
            )
            
            return jsonify({
                'success': True,
                'message': 'İki faktörlü doğrulama başarıyla etkinleştirildi'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Doğrulama kodu hatalı veya süresi dolmuş'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 2FA Kod Doğrulama
@app.route('/verify_2fa_code', methods=['POST'])
@login_required
@csrf.exempt
def verify_2fa_code():
    """2FA kodunu doğrula"""
    try:
        import pyotp
        
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if not code or len(code) != 6:
            return jsonify({
                'success': False,
                'message': '6 haneli kod gerekli'
            }), 400
        
        user = User.query.get(current_user.id)
        
        if not user.permissions or not user.permissions.get('two_factor_secret'):
            return jsonify({
                'success': False,
                'message': '2FA secret bulunamadı. Önce QR kod oluşturun.'
            }), 400
        
        secret = user.permissions['two_factor_secret']
        totp = pyotp.TOTP(secret)
        
        # Kodu doğrula (30 saniye tolerance)
        if totp.verify(code, valid_window=1):
            # 2FA'yı etkinleştir
            user.permissions['two_factor_auth'] = True
            db.session.commit()
            
            # Log oluştur
            log_activity(
                activity_type='2fa_etkinlestirme',
                description='İki faktörlü doğrulama başarıyla etkinleştirildi',
                user_id=current_user.id
            )
            
            return jsonify({
                'success': True,
                'message': '2FA başarıyla etkinleştirildi!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Geçersiz kod. Lütfen tekrar deneyin.'
            }), 400
            
    except ImportError:
        return jsonify({
            'success': False,
            'message': 'pyotp kütüphanesi eksik.'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'2FA doğrulama hatası: {str(e)}'
        }), 500

# E-posta Gönderme Fonksiyonu
def send_notification_email(to_email, subject, body):
    """Bildirim e-postası gönder"""
    try:
        from email_utils import send_notification_email as send_email_func
        return send_email_func(to_email, subject, body)
    except Exception as e:
        logger.error(f"E-posta gönderme hatası: {e}")
        return False, f"E-posta gönderim hatası: {str(e)}"

# E-posta Test Route'u (Güncelleme)
@app.route('/test_email_notification', methods=['POST'])
@login_required
@csrf.exempt
def test_email_notification():
    """E-posta bildirim sistemini test et"""
    try:
        from email_utils import send_test_email
        # JSON veya form data kabul et
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        test_type = data.get('type', 'general')
        
        # Test e-postası içeriği
        if test_type == 'welcome':
            subject = "Kaplan Hukuk Otomasyon - Hos Geldiniz!"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5aa0;">Hos Geldiniz!</h2>
                    <p>Sayın <strong>{current_user.get_full_name()}</strong>,</p>
                    <p>Kaplan Hukuk Otomasyon sistemine hoş geldiniz! Hesabınız başarıyla aktifleştirilmiştir.</p>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Hesap Bilgileriniz:</h3>
                        <ul>
                            <li><strong>Ad Soyad:</strong> {current_user.get_full_name()}</li>
                            <li><strong>E-posta:</strong> {current_user.email}</li>
                            <li><strong>Kullanıcı Adı:</strong> {current_user.username}</li>
                            <li><strong>Kayıt Tarihi:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</li>
                        </ul>
                    </div>
                    
                    <p>Sistemi kullanmaya başlamak için <a href="{request.host_url}" style="color: #2c5aa0;">buraya tıklayın</a>.</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="font-size: 12px; color: #666;">
                        Bu e-posta otomatik olarak gönderilmiştir. Lütfen yanıtlamayın.
                    </p>
                </div>
            </body>
            </html>
            """
        
        elif test_type == 'reminder':
            subject = "Kaplan Hukuk Otomasyon - Hatirlatma"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #d4642a;">Sistem Hatirlatmasi</h2>
                    <p>Sayın <strong>{current_user.get_full_name()}</strong>,</p>
                    <p>Bu bir test hatırlatması e-postasıdır.</p>
                    
                    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                        <p><strong>Hatırlatma:</strong> Sistemde bekleyen işlemleriniz olabilir.</p>
                        <p><strong>⏰ Tarih:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
                    </div>
                    
                    <p>Detayları görmek için <a href="{request.host_url}" style="color: #2c5aa0;">sisteme giriş yapın</a>.</p>
                </div>
            </body>
            </html>
            """
        
        else:  # general test
            subject = "Kaplan Hukuk Otomasyon - Test E-postası"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5aa0;">E-posta Test Başarılı! ✅</h2>
                    <p>Sayın <strong>{current_user.get_full_name()}</strong>,</p>
                    <p>E-posta bildirim sistemi başarıyla çalışıyor!</p>
                    
                    <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                        <h4 style="margin-top: 0; color: #155724;">Test Detayları:</h4>
                        <ul style="margin-bottom: 0;">
                            <li><strong>Test Zamanı:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</li>
                            <li><strong>Kullanıcı:</strong> {current_user.get_full_name()}</li>
                            <li><strong>E-posta:</strong> {current_user.email}</li>
                            <li><strong>Sistem:</strong> Kaplan Hukuk Otomasyon</li>
                        </ul>
                    </div>
                    
                    <p style="color: #28a745;"><strong>✅ E-posta sistemi düzgün çalışıyor!</strong></p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="font-size: 12px; color: #666;">
                        Bu test e-postasıdır. Herhangi bir işlem yapmanız gerekmez.
                    </p>
                </div>
            </body>
            </html>
            """
        
        # E-postayı gönder
        success, message = send_notification_email(current_user.email, subject, body)
        
        if success:
            # Log oluştur
            log_activity(
                activity_type='email_test',
                description=f'Test e-postası gönderildi: {test_type}',
                user_id=current_user.id
            )
            
            return jsonify({
                'success': True,
                'message': f'Test e-postası {current_user.email} adresine gönderildi!'
            })
        else:
            # Başarısız durumda 200 OK döndür ama success: false
            return jsonify({
                'success': False,
                'message': f'E-posta gönderilemedi: {message}'
            })
            
    except Exception as e:
        logger.error(f"E-posta test endpoint hatası: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'message': f'E-posta test hatası: {str(e)}'
        }), 500

# ===== E-POSTA BİLDİRİM SİSTEMİ =====

def should_send_email_notification(user, notification_type):
    """Kullanıcıya e-posta bildirimi gönderilip gönderilmeyeceğini kontrol et"""
    if not user.permissions:
        return True  # Default olarak bildirim gönder
    
    email_settings = user.permissions.get('email_notifications', {})
    if isinstance(email_settings, bool):
        return email_settings
    
    # Bildirim türüne göre kontrol
    notification_settings = {
        'welcome': email_settings.get('welcome', True),
        'case_created': email_settings.get('case_created', True),
        'case_updated': email_settings.get('case_updated', True),
        'payment_received': email_settings.get('payment_received', True),
        'event_reminder': email_settings.get('event_reminder', True),
        'user_approved': email_settings.get('user_approved', True),
        'password_changed': email_settings.get('password_changed', True),
        'security_alert': email_settings.get('security_alert', True)
    }
    
    return notification_settings.get(notification_type, True)

def send_system_notification(user_id, notification_type, subject, body, **kwargs):
    """Sistem bildirimi gönder (e-posta + veritabanı kaydı)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return False, "Kullanıcı bulunamadı"
        
        # E-posta gönderilsin mi kontrol et
        if should_send_email_notification(user, notification_type):
            success, message = send_notification_email(user.email, subject, body)
            
            # Log oluştur
            log_activity(
                activity_type='email_notification',
                description=f'{notification_type} bildirimi gönderildi: {subject}',
                user_id=user_id,
                details={
                    'notification_type': notification_type,
                    'email_sent': success,
                    'recipient': user.email,
                    'message': message
                }
            )
            
            return success, message
        else:
            return True, "E-posta bildirimi kullanıcı tarafından devre dışı bırakılmış"
            
    except Exception as e:
        logger.error(f"Sistem bildirimi gönderme hatası: {e}")
        return False, str(e)

# Özel bildirim fonksiyonları
def send_welcome_email(user):
    """Hoş geldin e-postası gönder"""
    subject = "Kaplan Hukuk Otomasyon - Hos Geldiniz!"
    body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c5aa0;">Hos Geldiniz!</h2>
            <p>Sayın <strong>{user.get_full_name()}</strong>,</p>
            <p>Kaplan Hukuk Otomasyon sistemine hoş geldiniz! Hesabınız başarıyla onaylanmıştır.</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Hesap Bilgileriniz:</h3>
                <ul>
                    <li><strong>Ad Soyad:</strong> {user.get_full_name()}</li>
                    <li><strong>E-posta:</strong> {user.email}</li>
                    <li><strong>Kullanıcı Adı:</strong> {user.username}</li>
                    <li><strong>Rol:</strong> {user.role}</li>
                </ul>
            </div>
            
            <p>Sistemi kullanmaya başlamak için <a href="{request.host_url}" style="color: #2c5aa0;">buraya tıklayın</a>.</p>
            
            <hr style="margin: 30px 0;">
            <p style="font-size: 12px; color: #666;">
                Bu e-posta otomatik olarak gönderilmiştir.
            </p>
        </div>
    </body>
    </html>
    """
    return send_system_notification(user.id, 'welcome', subject, body)

def send_case_notification(user_id, case, notification_type):
    """Dosya ile ilgili bildirim gönder"""
    if notification_type == 'case_created':
        subject = f"Yeni Dosya Oluşturuldu - {case.client_name}"
        action = "oluşturuldu"
    elif notification_type == 'case_updated':
        subject = f"Dosya Güncellendi - {case.client_name}"
        action = "güncellendi"
    else:
        return False, "Geçersiz bildirim türü"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c5aa0;">Dosya {action.title()}</h2>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Dosya Bilgileri:</h3>
                <ul>
                    <li><strong>Müvekkil:</strong> {case.client_name}</li>
                    <li><strong>Dosya No:</strong> {case.year}/{case.case_number}</li>
                    <li><strong>Mahkeme:</strong> {case.court}</li>
                    <li><strong>Durum:</strong> {case.status}</li>
                </ul>
            </div>
            
            <p>Detayları görmek için sisteme giriş yapın.</p>
        </div>
    </body>
    </html>
    """
    return send_system_notification(user_id, notification_type, subject, body)

def send_event_reminder(user_id, event):
    """Etkinlik hatırlatması gönder"""
    subject = f"Etkinlik Hatirlatmasi - {event.title}"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #d4642a;">Etkinlik Hatirlatmasi</h2>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <h3 style="margin-top: 0;">{event.title}</h3>
                <ul>
                    <li><strong>Tarih:</strong> {event.date.strftime('%d.%m.%Y')}</li>
                    <li><strong>Saat:</strong> {event.time.strftime('%H:%M') if event.time else 'Belirtilmemiş'}</li>
                    <li><strong>Açıklama:</strong> {event.description or 'Açıklama yok'}</li>
                </ul>
            </div>
            
            <p>Detayları görmek için takvime göz atın.</p>
        </div>
    </body>
    </html>
    """
    return send_system_notification(user_id, 'event_reminder', subject, body)

def send_payment_notification(user_id, client, amount):
    """Ödeme bildirimi gönder"""
    subject = f"Ödeme Alındı - {client.name}"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #28a745;">💰 Ödeme Alındı</h2>
            
            <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                <h3 style="margin-top: 0;">Ödeme Detayları:</h3>
                <ul>
                    <li><strong>Müvekkil:</strong> {client.name}</li>
                    <li><strong>Tutar:</strong> {amount:,.2f} TL</li>
                    <li><strong>Tarih:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return send_system_notification(user_id, 'payment_received', subject, body)

# E-posta Bildirim Ayarları Route'u
@app.route('/email_notification_settings', methods=['GET', 'POST'])
@login_required
def email_notification_settings():
    """E-posta bildirim ayarlarını yönet"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            user = User.query.get(current_user.id)
            
            if not user.permissions:
                user.permissions = {}
            
            # E-posta bildirim ayarlarını güncelle
            user.permissions['email_notifications'] = {
                'welcome': data.get('welcome', True),
                'case_created': data.get('case_created', True),
                'case_updated': data.get('case_updated', True),
                'payment_received': data.get('payment_received', True),
                'event_reminder': data.get('event_reminder', True),
                'user_approved': data.get('user_approved', True),
                'password_changed': data.get('password_changed', True),
                'security_alert': data.get('security_alert', True)
            }
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'E-posta bildirim ayarları güncellendi'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    else:
        # Mevcut ayarları getir
        user = User.query.get(current_user.id)
        email_settings = user.permissions.get('email_notifications', {}) if user.permissions else {}
        
        return jsonify({
            'success': True,
            'settings': {
                'welcome': email_settings.get('welcome', True),
                'case_created': email_settings.get('case_created', True),
                'case_updated': email_settings.get('case_updated', True),
                'payment_received': email_settings.get('payment_received', True),
                'event_reminder': email_settings.get('event_reminder', True),
                'user_approved': email_settings.get('user_approved', True),
                'password_changed': email_settings.get('password_changed', True),
                'security_alert': email_settings.get('security_alert', True)
            }
        })

# Yeni kişi ekleme API endpoint'i
@app.route('/add_person_to_case', methods=['POST'])
@login_required
@permission_required('dosya_duzenle')
@csrf.exempt
def add_person_to_case():
    """Dosyaya yeni kişi ekle"""
    try:
        case_id = request.form.get('case_id')
        person_type = request.form.get('person_type')  # 'client' veya 'opponent'
        entity_type = request.form.get('entity_type')
        capacity = request.form.get('capacity')
        name = request.form.get('name')
        phone = request.form.get('phone')
        identity_number = request.form.get('identity_number')
        address = request.form.get('address')
        
        if not all([case_id, person_type, name]):
            return jsonify({
                'success': False,
                'message': 'Gerekli alanlar eksik'
            }), 400
        
        case = CaseFile.query.get(case_id)
        if not case:
            return jsonify({
                'success': False,
                'message': 'Dosya bulunamadı'
            }), 404
        
        # Mevcut ek kişileri al
        if person_type == 'client':
            additional_people = case.additional_clients or []
        else:
            additional_people = case.additional_opponents or []
        
        # Yeni kişiyi ekle
        new_person = {
            'entity_type': entity_type,
            'capacity': capacity,
            'name': name,
            'phone': phone,
            'identity_number': identity_number,
            'address': address
        }
        
        additional_people.append(new_person)
        
        # Dosyayı güncelle
        if person_type == 'client':
            case.additional_clients = additional_people
        else:
            case.additional_opponents = additional_people
        
        db.session.commit()
        
        # Activity log oluştur
        log_activity(
            activity_type='dosya_guncelleme',
            description=f'Dosyaya yeni {person_type} eklendi: {name}',
            user_id=current_user.id,
            case_id=case_id
        )
        
        return jsonify({
            'success': True,
            'message': f'Yeni {person_type} başarıyla eklendi',
            'person_id': len(additional_people) - 1  # Index'i döndür
        })
        
    except Exception as e:
        logger.error(f"Kişi ekleme hatası: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Yeni vekil ekleme API endpoint'i
@app.route('/add_lawyer_to_case', methods=['POST'])
@login_required
@permission_required('dosya_duzenle')
@csrf.exempt
def add_lawyer_to_case():
    """Dosyaya yeni vekil ekle"""
    try:
        case_id = request.form.get('case_id')
        name = request.form.get('name')
        bar_number = request.form.get('bar_number')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if not all([case_id, name]):
            return jsonify({
                'success': False,
                'message': 'Gerekli alanlar eksik'
            }), 400
        
        case = CaseFile.query.get(case_id)
        if not case:
            return jsonify({
                'success': False,
                'message': 'Dosya bulunamadı'
            }), 404
        
        # Eğer ana vekil boşsa, ana vekil olarak ekle
        if not case.opponent_lawyer:
            case.opponent_lawyer = name
            case.opponent_lawyer_bar_number = bar_number
            case.opponent_lawyer_phone = phone
            case.opponent_lawyer_address = address
            message = 'Ana vekil bilgileri başarıyla eklendi'
        else:
            # Ana vekil doluysa, ek vekil olarak ekle
            additional_lawyers = case.additional_lawyers or []
            
            new_lawyer = {
                'name': name,
                'bar_number': bar_number,
                'phone': phone,
                'address': address
            }
            
            additional_lawyers.append(new_lawyer)
            case.additional_lawyers = additional_lawyers
            message = 'Ek vekil başarıyla eklendi'
        
        db.session.commit()
        
        # Activity log oluştur
        log_activity(
            activity_type='dosya_guncelleme',
            description=f'Dosyaya vekil eklendi: {name}',
            user_id=current_user.id,
            case_id=case_id
        )
        
        return jsonify({
            'success': True,
            'message': message,
            'lawyer_id': len(case.additional_lawyers) if case.additional_lawyers else 0
        })
        
    except Exception as e:
        logger.error(f"Vekil ekleme hatası: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Ana kişi güncelleme endpoint'i
@app.route('/update_main_person', methods=['POST'])
@login_required
@permission_required('dosya_duzenle')
@csrf.exempt
def update_main_person():
    """Ana müvekkil/karşı taraf bilgilerini güncelle"""
    try:
        case_id = request.form.get('case_id')
        person_type = request.form.get('person_type')  # 'client' veya 'opponent'
        entity_type = request.form.get('entity_type')
        capacity = request.form.get('capacity')
        name = request.form.get('name')
        phone = request.form.get('phone')
        identity_number = request.form.get('identity_number')
        address = request.form.get('address')
        
        if not all([case_id, person_type, name]):
            return jsonify({
                'success': False,
                'message': 'Gerekli alanlar eksik'
            }), 400
        
        case = CaseFile.query.get(case_id)
        if not case:
            return jsonify({
                'success': False,
                'message': 'Dosya bulunamadı'
            }), 404
        
        # Ana kişi bilgilerini güncelle
        if person_type == 'client':
            case.client_entity_type = entity_type
            case.client_capacity = capacity
            case.client_name = name
            case.phone_number = phone
            case.client_identity_number = identity_number
            case.client_address = address
        else:  # opponent
            case.opponent_entity_type = entity_type
            case.opponent_capacity = capacity
            case.opponent_name = name
            case.opponent_phone = phone
            case.opponent_identity_number = identity_number
            case.opponent_address = address
        
        db.session.commit()
        
        # Activity log oluştur
        log_activity(
            activity_type='dosya_guncelleme',
            description=f'Ana {person_type} bilgileri güncellendi: {name}',
            user_id=current_user.id,
            case_id=case_id
        )
        
        return jsonify({
            'success': True,
            'message': f'{"Müvekkil" if person_type == "client" else "Karşı taraf"} bilgileri başarıyla güncellendi'
        })
        
    except Exception as e:
        logger.error(f"Ana kişi güncelleme hatası: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Ana kişi silme endpoint'i
@app.route('/delete_main_person', methods=['POST'])
@login_required
@permission_required('dosya_duzenle')
@csrf.exempt
def delete_main_person():
    """Ana müvekkil/karşı taraf bilgilerini sil"""
    try:
        case_id = request.form.get('case_id')
        person_type = request.form.get('person_type')  # 'client' veya 'opponent'
        
        if not all([case_id, person_type]):
            return jsonify({
                'success': False,
                'message': 'Gerekli alanlar eksik'
            }), 400
        
        case = CaseFile.query.get(case_id)
        if not case:
            return jsonify({
                'success': False,
                'message': 'Dosya bulunamadı'
            }), 404
        
        # Ana kişi bilgilerini temizle
        if person_type == 'client':
            case.client_entity_type = 'person'
            case.client_capacity = None
            case.client_name = None
            case.phone_number = None
            case.client_identity_number = None
            case.client_address = None
        else:  # opponent
            case.opponent_entity_type = 'person'
            case.opponent_capacity = None
            case.opponent_name = None
            case.opponent_phone = None
            case.opponent_identity_number = None
            case.opponent_address = None
        
        db.session.commit()
        
        # Activity log oluştur
        log_activity(
            activity_type='dosya_guncelleme',
            description=f'Ana {person_type} bilgileri temizlendi',
            user_id=current_user.id,
            case_id=case_id
        )
        
        return jsonify({
            'success': True,
            'message': f'{"Müvekkil" if person_type == "client" else "Karşı taraf"} bilgileri başarıyla temizlendi'
        })
        
    except Exception as e:
        logger.error(f"Ana kişi silme hatası: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Dosya temel bilgileri güncelleme endpoint'i
@app.route('/update_case_basic_info', methods=['POST'])
@login_required
@permission_required('dosya_duzenle')
@csrf.exempt
def update_case_basic_info():
    """Dosyanın temel bilgilerini güncelle"""
    try:
        case_id = request.form.get('case_id')
        file_type = request.form.get('file_type')
        year = request.form.get('year')
        case_number = request.form.get('case_number')
        open_date = request.form.get('open_date')
        city = request.form.get('city')
        courthouse = request.form.get('courthouse')
        department = request.form.get('department')
        status = request.form.get('status')
        next_hearing = request.form.get('next_hearing')
        hearing_time = request.form.get('hearing_time')
        hearing_type = request.form.get('hearing_type')
        
        if not all([case_id, file_type, year, case_number, status]):
            return jsonify({
                'success': False,
                'message': 'Gerekli alanlar eksik'
            }), 400
        
        case = CaseFile.query.get(case_id)
        if not case:
            return jsonify({
                'success': False,
                'message': 'Dosya bulunamadı'
            }), 404
        
        # Tarihleri parse et
        open_date_obj = None
        if open_date:
            try:
                open_date_obj = datetime.strptime(open_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        next_hearing_obj = None
        if next_hearing and next_hearing.strip():
            try:
                next_hearing_obj = datetime.strptime(next_hearing.strip(), '%Y-%m-%d').date()
            except ValueError as e:
                logger.warning(f"Duruşma tarihi parse hatası: {next_hearing} - {e}")
                next_hearing_obj = None
        
        # Dosya bilgilerini güncelle
        if os.getenv('DEBUG', 'False').lower() == 'true':
            print(f"DEBUG: Updating file_type from {case.file_type} to {file_type}")
        case.file_type = file_type
        case.year = int(year)
        case.case_number = case_number
        case.open_date = open_date_obj
        case.status = status
        case.next_hearing = next_hearing_obj
        case.hearing_time = hearing_time if hearing_time and hearing_time.strip() else None
        case.hearing_type = hearing_type if hearing_type else 'durusma'
        
        # Şehir bilgisini courthouse string'inden çıkar ve güncelle
        if city and courthouse:
            case.courthouse = f"{city} - {courthouse}"
        elif courthouse:
            case.courthouse = courthouse
        
        case.department = department if department else None
        
        db.session.commit()
        
        # Activity log oluştur
        log_activity(
            activity_type='dosya_guncelleme',
            description=f'Dosya temel bilgileri güncellendi',
            user_id=current_user.id,
            case_id=case_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Dosya bilgileri başarıyla güncellendi',
            'data': {
                'file_type': file_type,
                'year': year,
                'case_number': case_number,
                'open_date': open_date,
                'city': city,
                'courthouse': courthouse,
                'department': department,
                'status': status,
                'next_hearing': next_hearing,
                'hearing_time': hearing_time,
                'hearing_type': hearing_type
            }
        })
        
    except Exception as e:
        logger.error(f"Dosya bilgileri güncelleme hatası: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("=" * 50)
    print("LOGIN FUNCTION CALLED!!!")
    print("=" * 50)
    print(f"DEBUG LOGIN FUNCTION CALLED - Method: {request.method}")
    if current_user.is_authenticated:
        print("DEBUG - User already authenticated, redirecting")
        return redirect(url_for('anasayfa'))
    
    # GET request'te session'ı temizleme - kapatıldı
    # if request.method == 'GET' and 'temp_user_id' in session:
    #     print("DEBUG - GET request, clearing 2FA session")
    #     session.pop('temp_user_id', None)
    #     session.pop('next_page', None)
        
    if request.method == 'POST':
        print("DEBUG - POST request received")
        email = request.form.get('email')
        password = request.form.get('password')
        totp_code = request.form.get('totp_code')
        csrf_token = request.form.get('csrf_token')
        
        print(f"DEBUG LOGIN - Email: {email}")
        print(f"DEBUG LOGIN - Password provided: {password is not None}")
        print(f"DEBUG LOGIN - TOTP code: {totp_code}")
        print(f"DEBUG LOGIN - CSRF token: {csrf_token}")
        print(f"DEBUG LOGIN - Session before: {dict(session)}")
        print(f"DEBUG LOGIN - Form data: {dict(request.form)}")
        
        # 2FA doğrulama aşaması
        if 'temp_user_id' in session and totp_code:
            print("DEBUG - 2FA doğrulama aşaması")
            try:
                import pyotp
                user = User.query.get(session['temp_user_id'])
                print(f"DEBUG - User found: {user is not None}")
                
                if user and user.permissions and user.permissions.get('two_factor_secret'):
                    secret = user.permissions['two_factor_secret']
                    totp = pyotp.TOTP(secret)
                    
                    print(f"DEBUG - Secret exists, verifying code {totp_code}")
                    print(f"DEBUG - Current time: {totp.now()}")
                    verification_result = totp.verify(totp_code, valid_window=1)
                    print(f"DEBUG - Verification result: {verification_result}")
                    
                    if verification_result:
                        # 2FA doğru, giriş yap
                        print("DEBUG - 2FA verification successful, logging in user")
                        login_user(user)
                        next_page = session.pop('next_page', url_for('anasayfa'))
                        session.pop('temp_user_id', None)
                        
                        # Log oluştur
                        log_activity(
                            activity_type='giris',
                            description='2FA ile başarılı giriş',
                            user_id=user.id
                        )
                        
                        print(f"DEBUG - Redirecting to: {next_page}")
                        return redirect(next_page)
                    else:
                        print("DEBUG - 2FA verification failed")
                        print(f"DEBUG - Expected code: {totp.now()}")
                        print(f"DEBUG - Received code: {totp_code}")
                        flash('Geçersiz doğrulama kodu.', 'error')
                        return render_template('auth.html', require_2fa=True, user_email=user.email)
                else:
                    print("DEBUG - 2FA secret not found")
                    flash('2FA yapılandırma hatası.', 'error')
                    session.pop('temp_user_id', None)
                    session.pop('next_page', None)
                    return render_template('auth.html')
            except Exception as e:
                print(f"DEBUG - 2FA exception: {str(e)}")
                flash('2FA doğrulama sırasında hata oluştu.', 'error')
                session.pop('temp_user_id', None)
                session.pop('next_page', None)
                return render_template('auth.html')
        
        # Normal email/password doğrulama
        if email and password:
            print("DEBUG - Normal email/password doğrulama")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                print(f"DEBUG - Password check passed for user: {user.email}")
                if not user.is_approved and not user.is_admin:
                    flash('Hesabınız henüz onaylanmamış. Lütfen yönetici onayını bekleyin.', 'warning')
                    return render_template('auth.html')
                
                # 2FA kontrolü
                if user.permissions and hasattr(user.permissions, 'get') and user.permissions.get('two_factor_auth', False):
                    print("DEBUG - 2FA required, setting session")
                    # 2FA etkinse, kullanıcıyı session'da sakla ve 2FA sayfasına yönlendir
                    session['temp_user_id'] = user.id
                    session['next_page'] = request.args.get('next') or url_for('anasayfa')
                    print(f"DEBUG - Session after 2FA setup: {dict(session)}")
                    return render_template('auth.html', require_2fa=True, user_email=user.email)
                else:
                    print("DEBUG - No 2FA required, direct login")
                    # 2FA yoksa direkt giriş yap
                    login_user(user)
                    next_page = request.args.get('next')
                    
                    # Log oluştur
                    log_activity(
                        activity_type='giris',
                        description='Başarılı giriş',
                        user_id=user.id
                    )
                    
                    return redirect(next_page or url_for('anasayfa'))
            else:
                print("DEBUG - Password check failed")
                # Kullanıcı var mı kontrol et
                if user and not user.is_approved and not user.is_admin:
                    flash('Hesabınız henüz onaylanmamış. Lütfen yönetici onayını bekleyin.', 'warning')
                else:
                    flash('Geçersiz e-posta veya şifre.', 'error')
    
    print("DEBUG - Rendering auth.html")
    return render_template('auth.html')

@app.route('/vekaletname')
def vekaletname():
    return render_template('vekaletname.html')

@app.route('/test_route')
def test_route():
    print("TEST ROUTE CALLED!!!")
    return "Test route works!"

if __name__ == '__main__':
    with app.app_context():
        # Veritabanı tablolarının var olup olmadığını kontrol et,
        # yoksa oluştur (Mevcut verileri silmez)
        db.create_all()
        
        # Admin kullanıcısını kontrol et/oluştur
        create_admin_user()
        
    app.run(debug=True)
