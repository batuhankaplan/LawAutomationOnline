from flask import Flask, render_template, request, url_for, flash, redirect, jsonify, session, send_from_directory, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta, date, time
import json
import os
from werkzeug.utils import secure_filename
import locale
import time as pytime
import subprocess
import tempfile
from flask_mail import Mail, Message
from bs4 import BeautifulSoup
import requests
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, User, ActivityLog, Client, Payment, Document, Notification, Expense, CaseFile, Announcement, CalendarEvent, WorkerInterview, IsciGorusmeTutanagi
import uuid
from PIL import Image
from functools import wraps
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
                    'isci_gorusme_sil': 'İşçi Görüşme Silme'
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
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAIL_SERVER'] = 'smtp-mail.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yzbatuhankaplan@outlook.com'
app.config['MAIL_PASSWORD'] = 'your_mail_password'

db.init_app(app)
migrate = Migrate(app, db)
mail = Mail(app)

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

# --- End Flask-Admin Setup ---

# Auth routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('anasayfa'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_approved and not user.is_admin:
                flash('Hesabınız henüz onaylanmamış. Lütfen yönetici onayını bekleyin.', 'warning')
                return render_template('auth.html')
            
            # Admin kullanıcısı için varsayılan yetkileri ayarla
            if user.is_admin and not user.permissions:
                user.permissions = {
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
                    'dosya_sil': True
                }
                db.session.commit()
                
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('anasayfa'))
        else:
            flash('Geçersiz e-posta veya şifre.', 'error')
    
    return render_template('auth.html')

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
        gender = request.form.get('gender').lower()
        phone = request.form.get('phone')
        
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
            user.phone = request.form.get('phone')
            user.role = request.form.get('meslek')
            user.gender = request.form.get('cinsiyet')
            
            # Doğum tarihi kontrolü ve dönüşümü
            birth_date = request.form.get('birth_date')
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
        
        if not current_user.check_password(current_password):
            flash('Mevcut şifre yanlış!', 'error')
            return redirect(url_for('settings'))
        
        current_user.set_password(new_password)
        db.session.commit()
        flash('Şifreniz başarıyla değiştirildi!', 'success')
        
    except Exception as e:
        flash(f'Şifre değiştirme işlemi başarısız: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        password = request.form.get('password')
        if not current_user.check_password(password):
            flash('Şifre yanlış!', 'error')
            return redirect(url_for('settings'))
        
        user_id = current_user.id
        logout_user()
        User.query.filter_by(id=user_id).delete()
        db.session.commit()
        flash('Hesabınız başarıyla silindi!', 'success')
        return redirect(url_for('login'))
        
    except Exception as e:
        flash(f'Hesap silme işlemi başarısız: {str(e)}', 'error')
        return redirect(url_for('settings'))

@app.route('/enable_2fa', methods=['POST'])
@login_required
def enable_2fa():
    # Bu fonksiyon şu an için sadece başarılı yanıt dönüyor
    # İki faktörlü doğrulama için gerekli implementasyon daha sonra eklenebilir
    return jsonify({'success': True})

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
        now = datetime.now()
        current_time = {
            'weekday': now.strftime('%A'),  # Gün adı
            'time': now.strftime('%H:%M'),  # Saat
            'date': now.strftime('%d.%m.%Y')  # Tarih
        }
    except Exception:
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

@app.route('/')
def anasayfa():
    # Kullanıcı giriş yapmamışsa login sayfasına yönlendir
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    # Kullanıcı giriş yapmış ama onaylanmamışsa
    if not current_user.is_approved and not current_user.is_admin:
        flash('Hesabınız henüz onaylanmamış. Lütfen yönetici onayını bekleyin.', 'warning')
        logout_user()
        return redirect(url_for('login'))
    
    # Duyuruları al - Sadece gerekli sütunları seç
    # announcements = Announcement.query.all() # Eski sorgu
    announcements = db.session.query(Announcement.id, Announcement.title, Announcement.content).all()
    
    # Dosya türlerine göre sayıları hesapla
    hukuk_count = CaseFile.query.filter_by(file_type='hukuk').count()
    ceza_count = CaseFile.query.filter_by(file_type='ceza').count()
    icra_count = CaseFile.query.filter_by(file_type='icra').count()
    
    # Toplam dosya sayısı
    total_count = hukuk_count + ceza_count + icra_count
    
    # Son aktiviteleri al (son 5)
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
    
    # Toplam aktivite sayısını hesapla
    total_activities = ActivityLog.query.count()
    
    # Yaklaşan duruşmaları SADECE takvimden al
    today = datetime.now().date()
    
    # Sadece takvimden duruşmaları al (hem bağlı hem bağımsız olan tüm duruşma ve e-duruşma etkinlikleri)
    upcoming_hearings = CalendarEvent.query.filter(
        CalendarEvent.date >= today,
        CalendarEvent.event_type.in_(['durusma', 'e-durusma'])
    ).order_by(CalendarEvent.date, CalendarEvent.time).limit(4).all()
    
    # Toplam duruşma sayısını al
    total_hearings = CalendarEvent.query.filter(
        CalendarEvent.date >= today,
        CalendarEvent.event_type.in_(['durusma', 'e-durusma'])
    ).count()
    
    # Kullanıcı yetkilerini kontrol et
    is_admin = current_user.is_admin
    user_permissions = current_user.permissions if current_user.permissions else {}
    takvim_goruntule = user_permissions.get('takvim_goruntule', False) or is_admin
    
    # Debug mesajları
    print(f"Kullanıcı admin mi: {is_admin}")
    print(f"Kullanıcı yetkileri: {user_permissions}")
    print(f"Takvim görüntüleme yetkisi: {takvim_goruntule}")
    
    # Aktif dosya sayısını hesapla (status=Aktif olan dosyalar)
    total_active_cases = CaseFile.query.filter_by(status='Aktif').count()
    
    # Adliye istatistiklerini hesapla
    courthouse_stats = db.session.query(
        CaseFile.courthouse, 
        func.count(CaseFile.id).label('total_cases')
    ).filter(
        CaseFile.courthouse != None,
        CaseFile.courthouse != "Uygulanmaz",
        CaseFile.file_type.in_(['hukuk', 'ceza', 'savcilik', 'icra'])
    ).group_by(CaseFile.courthouse).order_by(desc('total_cases')).limit(6).all()
    
    # Adliye istatistiklerini sözlük listesine dönüştür
    courthouse_stats_list = [
        {'courthouse': stat.courthouse, 'total_cases': stat.total_cases} 
        for stat in courthouse_stats
    ]
    
    return render_template('anasayfa.html',
                           announcements=announcements,
                           hukuk_count=hukuk_count,
                           ceza_count=ceza_count,
                           icra_count=icra_count,
                           total_count=total_count,
                           total_active_cases=total_active_cases,
                           activities=activities, 
                           total_activities=total_activities,
                           upcoming_hearings=upcoming_hearings,
                           total_hearings=total_hearings,
                           courthouse_stats=courthouse_stats_list,
                           can_view_calendar=takvim_goruntule)

# Daha fazla aktivite yüklemek için yeni endpoint
@app.route('/load_more_activities/<int:offset>')
def load_more_activities(offset):
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).offset(offset).limit(5).all()
    
    activities_data = []
    for activity in activities:
        user = User.query.get(activity.user_id)
        activity_data = {
            'type': activity.activity_type,
            'description': activity.description,
            'timestamp': activity.timestamp.strftime('%d.%m.%Y %H:%M'),
            'user': user.get_full_name() if user else 'Bilinmeyen Kullanıcı',
            'details': activity.details,
            'profile_image': url_for('static', filename=user.profile_image) if user and user.profile_image else url_for('static', filename='images/pp.png')
        }
        activities_data.append(activity_data)
    
    return jsonify(activities=activities_data)

@app.route('/takvim')
@login_required
@permission_required('takvim_goruntule')
def takvim():
    # Debug mesajları
    print(f"Kullanıcı admin mi: {current_user.is_admin}")
    print(f"Kullanıcı yetkileri: {current_user.permissions}")
    print(f"Takvim görüntüleme yetkisi: {current_user.has_permission('takvim_goruntule')}")
    
    # Tüm etkinlikleri getir
    events = CalendarEvent.query.all()
    events_data = []
    
    for event in events:
        event_data = {
            'id': event.id,
            'title': event.title,
            'date': event.date.strftime('%Y-%m-%d'),
            'time': event.time.strftime('%H:%M'),
            'event_type': event.event_type,
            'description': event.description,
            'assigned_to': event.assigned_to,
            'file_type': event.file_type,
            'courthouse': event.courthouse,
            'department': event.department,
            'deadline_date': event.deadline_date.strftime('%Y-%m-%d') if event.deadline_date else None,
            'is_completed': event.is_completed
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
    
    return render_template('takvim.html', 
                         events=events_data,
                         adli_tatil_data=adli_tatil_data,
                         all_courthouses=cities_courthouses, # Tüm adliye verilerini gönder
                         user_permissions=user_permissions)

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
        
    if request.method == 'POST':
        if not current_user.has_permission('odeme_ekle'):
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
    return render_template('odemeler.html', clients=clients)

@app.route('/update_client/<int:client_id>', methods=['POST'])
@login_required
def update_client(client_id):
    if not current_user.has_permission('odeme_duzenle'):
        return jsonify({'success': False, 'error': 'Ödeme düzenleme yetkiniz bulunmamaktadır.'})
        
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
                
            client.status = data['status']
            client.description = data.get('description', '')

            # Ödeme durumu değiştiyse log kaydı ekle
            if old_status != data['status']:
                log = ActivityLog(
                    activity_type='odeme_guncelleme',
                    description=f'Ödeme durumu güncellendi: {client.name} {client.surname}',
                    details={
                        'musteri': f'{client.name} {client.surname}',
                        'eski_durum': old_status,
                        'yeni_durum': data['status'],
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
    if request.method == 'POST':
        # Form verilerini al
        file_type = request.form.get('file-type')
        city = request.form.get('city')  # Yeni eklenen şehir filtresi
        courthouse = request.form.get('courthouse')
        department = request.form.get('department')
        court_number = request.form.get('court-number')  # Yeni eklenen mahkeme numarası filtresi
        year = request.form.get('year')
        case_number = request.form.get('case-number')
        client_name = request.form.get('client-name')
        status = request.form.get('status')
        
        # Sorguyu başlat
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
def dosya_ekle():
    if request.method == 'POST':
        try:
            data = request.get_json()
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

            if file_type in ['ARABULUCULUK', 'AİHM', 'AYM']:
                courthouse = "Uygulanmaz"  # Varsayılan değer ata
                department = "Uygulanmaz"  # Varsayılan değer ata
            elif file_type.upper() in ['AIHM', 'AHM']:  # Türkçe karakter sorunu için ek kontrol
                courthouse = "Uygulanmaz"  # Varsayılan değer ata
                department = "Uygulanmaz"  # Varsayılan değer ata
            elif file_type == 'savcilik':  # Küçük harfle doğru şekilde kontrol ediyoruz
                department = "Savcılık"    # Savcılık için her zaman sabit bir değer kullan
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
                phone_number=data.get('phone-number', ''), # Phone number is now optional
                status='Aktif',
                open_date=datetime.strptime(data['open-date'], '%Y-%m-%d').date(),
                user_id=current_user.id
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

            return jsonify(success=True, new_case_id=new_case_file.id) # Yeni ID'yi döndür

        except Exception as e:
            db.session.rollback()
            print(f"Hata: {str(e)}")
            return jsonify(success=False, message=str(e)), 400

    # GET isteği için şehir ve adliye verilerini yükle
    cities_courthouses, cities = parse_adliye_list()
    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('dosya_ekle.html',
                         today_date=today_date,
                         cities=cities,
                         all_courthouses=json.dumps(cities_courthouses, ensure_ascii=False)) # Pass all data as JSON

@app.route('/case_details/<int:case_id>')
def case_details(case_id):
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
        
        return jsonify({
            'success': True,
            'file_type': case_file.file_type,
            'courthouse': case_file.courthouse,
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
        case_file = db.session.get(CaseFile, case_id)
        if case_file:
            # Dosya bilgilerini güncelle
            case_file.file_type = data.get('file_type', case_file.file_type)
            case_file.courthouse = data.get('courthouse', case_file.courthouse)
            case_file.client_name = data.get('client_name', case_file.client_name)
            case_file.phone_number = data.get('phone_number', case_file.phone_number)
            case_file.status = data.get('status', case_file.status)
            case_file.description = data.get('description', case_file.description)
            case_file.hearing_time = data.get('hearing_time', case_file.hearing_time)  # Güncellenen hearing_time alanı
            
            # Yeni: Duruşma türünü al ve kaydet
            case_file.hearing_type = data.get('hearing_type', 'durusma')
            
            # Departman bilgisini de güncelle (Frontend'den doğru değerin geldiğini varsayıyoruz)
            department_value = data.get('department') 
            if department_value:
                 case_file.department = department_value
            
            # Duruşma tarihi ve saati opsiyonel
            if data.get('next_hearing'):
                case_file.next_hearing = datetime.strptime(data['next_hearing'], '%Y-%m-%d').date()
            else:
                case_file.next_hearing = None
            
            db.session.commit()
            
            log_activity(
                activity_type='dosya_duzenleme',
                description=f"Dosya güncellendi: {case_file.client_name}",
                user_id=1,
                case_id=case_id
            )
            
            return jsonify(success=True)
        return jsonify(success=False, message="Dosya bulunamadı")
    except Exception as e:
        print(f"Hata: {str(e)}")
        db.session.rollback()
        return jsonify(success=False, message=str(e))

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
        
        event = CalendarEvent(
            title=data['title'],
            date=event_date,
            time=event_time,
            event_type=data['event_type'],
            description=description,
            user_id=current_user.id,
            assigned_to=data.get('assigned_to', ''),
            deadline_date=deadline_date,
            is_completed=data.get('is_completed', False),
            file_type=file_type,
            courthouse=courthouse,
            department=department
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
        
        log = ActivityLog(
            activity_type='etkinlik_ekleme',
            description=f'Yeni etkinlik eklendi: {data["title"]}',
            details=log_details,
            user_id=current_user.id,
            related_event_id=event.id
        )
        db.session.add(log)
        
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
                department=department
            )
            db.session.add(deadline_event)
        
        db.session.commit()
        app.logger.info(f"Etkinlik başarıyla eklendi: {event.id}")
        
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
            
        # Eğer başkası eklemiş ve kullanıcı süper admin değilse düzenleme yapılamaz
        if event.user_id != current_user.id and not current_user.is_admin:
            app.logger.warning(f"Yetkisiz güncelleme denemesi: Kullanıcı {current_user.email} başkasının etkinliğini (ID: {event_id}) düzenlemeye çalıştı.")
            return jsonify({"error": "Başkasının eklediği etkinliği düzenleyemezsiniz."}), 403
            
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
        if 'date' in data and 'time' in data:
            # Yeni format: ayrı date ve time alanları
            try:
                event_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                event_time = datetime.strptime(data['time'], '%H:%M').time()
                
                event.date = event_date
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
            event.description = data['description']
            
        if 'assigned_to' in data:
            event.assigned_to = data['assigned_to'] or None
            
        if 'is_completed' in data:
            event.is_completed = data.get('is_completed', False)
        
        # Açıklamayı SADECE istekte varsa güncelle
        if 'description' in data:
            event.description = data['description']
        
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
        
        # Değişiklikleri kaydet
        db.session.commit()
        
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
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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
                filepath=unique_filename,  # Gerçek dosya yolu
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
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        document.filepath,
        as_attachment=True,
        download_name=document.filename
    )

@app.route('/delete_document/<int:document_id>', methods=['POST'])
@login_required
@permission_required('dosya_sil')
def delete_document(document_id):
    try:
        document = Document.query.get_or_404(document_id)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
        
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
    if not os.path.exists(filepath):
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
                    permanent_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
                    
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
        case_id = data.get('case_id')
        hearing_date_str = data.get('hearing_date') # Tarih string olarak alınır
        hearing_time_str = data.get('hearing_time', '09:00') # Saat string olarak alınır
        status = data.get('status')
        hearing_type = data.get('hearing_type', 'durusma').lower()
        
        case_file = CaseFile.query.get(case_id)
        if not case_file:
            return jsonify(success=False, message="Dosya bulunamadı")

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
        
        event_title_prefix = "E-Duruşma" if hearing_type == 'e-durusma' else "Duruşma"
        event_title = f"{event_title_prefix} - {case_file.client_name} ({case_file.year}/{case_file.case_number})"
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
def iletisim():
    return render_template('iletisim.html')

@app.route('/send_contact_mail', methods=['POST'])
def send_contact_mail():
    try:
        data = request.get_json()
        
        msg = Message('Yeni İletişim Formu Mesajı',
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[app.config['MAIL_USERNAME']])
        
        msg.body = f"""
        Yeni bir iletişim formu mesajı alındı:
        
        Gönderen: {data['name']}
        E-posta: {data['email']}
        
        Mesaj:
        {data['message']}
        """
        
        mail.send(msg)
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
def hesaplamalar(type):
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
def update_settings():
    try:
        data = request.get_json()
        user = User.query.get(current_user.id)
        
        if 'fontSize' in data:
            user.font_size = data['fontSize']
            
        if 'theme' in data:
            user.theme_preference = data['theme']
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ayarlar başarıyla güncellendi'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/admin_panel')
@login_required
@admin_required
def admin_panel():
    # Onay bekleyen kullanıcıları al
    pending_users = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    
    # Onaylanmış kullanıcıları al
    approved_users = User.query.filter_by(is_approved=True).order_by(User.approval_date.desc()).all()
    
    return render_template('admin_panel.html', 
                         pending_users=pending_users,
                         approved_users=approved_users)

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

@app.route('/admin/toggle_user_status/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    try:
        user = User.query.get_or_404(user_id)
        user.is_approved = not user.is_approved
        
        if not user.is_approved:
            user.approval_date = None
            user.approved_by = None
        else:
            user.approval_date = datetime.now()
            user.approved_by = current_user.id
            
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e))

@app.route('/admin/get_user_permissions/<int:user_id>')
@login_required
@admin_required
def get_user_permissions(user_id):
    """Kullanıcı yetkilerini JSON formatında döndürür"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Tüm yetki anahtarlarını içeren bir sözlük oluştur
        permissions = user.permissions if user.permissions else {}
        
        # Tüm izinler için varsayılan değer olarak False ekle
        all_permissions = [
            'dosya_sorgula', 'dosya_ekle', 'dosya_duzenle', 'dosya_sil',
            'takvim_goruntule', 'etkinlik_ekle', 'etkinlik_duzenle', 'etkinlik_sil', 'etkinlik_goruntule',
            'duyuru_goruntule', 'duyuru_ekle', 'duyuru_duzenle', 'duyuru_sil',
            'odeme_goruntule', 'odeme_ekle', 'odeme_duzenle', 'odeme_sil', 'odeme_istatistik_goruntule',
            'faiz_hesaplama', 'harc_hesaplama', 'isci_hesaplama', 'vekalet_hesaplama', 'ceza_infaz_hesaplama',
            'rapor_goruntule', 'rapor_olustur',
            'musteri_goruntule', 'musteri_ekle', 'musteri_duzenle', 'musteri_sil',
            'panel_goruntule', 'ayarlar', 'isci_gorusme_goruntule', 'isci_gorusme_ekle', 'isci_gorusme_duzenle', 'isci_gorusme_sil'
        ]
        
        # Eksik izinleri ekle
        for permission in all_permissions:
            if permission not in permissions:
                permissions[permission] = False
        
        return jsonify({
            'success': True,
            'permissions': permissions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Kullanıcı yetkileri alınamadı: {str(e)}'
        }), 500

@app.route('/admin/update_user_permissions/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def update_user_permissions(user_id):
    """Kullanıcı yetkilerini günceller"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Yetkileri güncelle
        if 'permissions' in data:
            # Yeni bir permissions sözlüğü oluştur - tamamen değiştir
            new_permissions = {}
            
            # Gelen her yetkiyi yeni sözlüğe ekle
            for permission, value in data['permissions'].items():
                new_permissions[permission] = value == True
            
            # Kullanıcının permissions alanını tamamen güncelle
            user.permissions = new_permissions
            db.session.commit()
            
            # Log oluştur
            log_activity(
                activity_type='yetki_guncelleme',
                description=f'Kullanıcı yetkileri güncellendi: {user.username}',
                user_id=current_user.id,
                details={
                    'updated_by': current_user.get_full_name(),
                    'permissions': new_permissions
                }
            )
            
            return jsonify({
                'success': True,
                'message': 'Kullanıcı yetkileri güncellendi',
                'permissions': new_permissions
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Yetki bilgileri eksik'
            }), 400
    except Exception as e:
        db.session.rollback()
        print(f"Yetki güncelleme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Kullanıcı yetkileri güncellenirken hata oluştu: {str(e)}'
        }), 500

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
def save_isci_gorusme():
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

@app.route('/save_isci_gorusme_json', methods=['POST'])
@login_required
@permission_required('isci_gorusme_ekle')
def save_isci_gorusme_json():
    try:
        data = request.get_json()
        
        # Tarihleri datetime.date formatına çevir
        start_date = datetime.strptime(data.get('startDate'), '%Y-%m-%d').date()
        insurance_date = datetime.strptime(data.get('insuranceDate'), '%Y-%m-%d').date()
        end_date = datetime.strptime(data.get('endDate'), '%Y-%m-%d').date()
        
        # Yeni görüşme kaydı oluştur
        interview = WorkerInterview(
            fullName=data.get('fullName'),
            tcNo=data.get('tcNo'),
            phone=data.get('phone'),
            address=data.get('address'),
            startDate=start_date,
            insuranceDate=insurance_date,
            endDate=end_date,
            endReason=data.get('endReason'),
            companyName=data.get('companyName'),
            businessType=data.get('businessType'),
            companyAddress=data.get('companyAddress'),
            position=data.get('position'),
            workHours=data.get('workHours'),
            overtime=data.get('overtime'),
            salary=float(data.get('salary', 0)),
            transportation=float(data.get('transportation', 0)) if data.get('transportation') else None,
            food=float(data.get('food', 0)) if data.get('food') else None,
            benefits=data.get('benefits'),
            weeklyHoliday=data.get('weeklyHoliday'),
            holidays=data.get('holidays'),
            annualLeave=data.get('annualLeave'),
            unpaidSalary=data.get('unpaidSalary'),
            witness1=data.get('witness1'),
            witness2=data.get('witness2'),
            witness3=data.get('witness3'),
            witness4=data.get('witness4'),
            user_id=current_user.id
        )
        
        db.session.add(interview)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Form başarıyla kaydedildi.'})
        
    except Exception as e:
        print(f"Hata: {str(e)}")  # Hatayı konsola yazdır
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Form kaydedilirken bir hata oluştu: {str(e)}'})

@app.route('/get_worker_interviews')
@login_required
def get_worker_interviews():
    try:
        interviews = WorkerInterview.query.filter_by(user_id=current_user.id).order_by(WorkerInterview.created_at.desc()).all()
        return jsonify({
            'success': True,
            'forms': [interview.to_dict() for interview in interviews]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_worker_interview/<int:interview_id>')
@login_required
def get_worker_interview(interview_id):
    try:
        interview = WorkerInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Yetkisiz erişim'}), 403
            
        return jsonify({
            'success': True,
            'form': interview.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_worker_interview/<int:interview_id>', methods=['DELETE'])
@login_required
def delete_worker_interview(interview_id):
    try:
        interview = WorkerInterview.query.get_or_404(interview_id)
        if interview.user_id != current_user.id:
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
        forms = IsciGorusmeTutanagi.query.filter_by(user_id=current_user.id).order_by(IsciGorusmeTutanagi.created_at.desc()).all()
        forms_data = []
        
        for form in forms:
            forms_data.append({
                'id': form.id,
                'name': form.name or 'İsimsiz Form',
                'date': form.created_at.strftime('%d.%m.%Y')
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
        
        # Kullanıcı kontrolü
        if form.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Bu forma erişim izniniz yok'})
        
        form_data = form.to_dict()
        
        # Tanıkları ekle
        for i, witness in enumerate(form.witnesses, 1):
            form_data[f'witness{i}'] = witness
        
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
        
        # Kullanıcı kontrolü
        if form.user_id != current_user.id and not current_user.is_admin:
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
                'ceza_infaz_hesaplama': True
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
@login_required
def delete_client(client_id):
    if not current_user.has_permission('odeme_sil'):
        return jsonify({'success': False, 'error': 'Ödeme silme yetkiniz bulunmamaktadır.'})
        
    client = Client.query.get_or_404(client_id)
    
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
        db.session.add(log)
        db.session.delete(client)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

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
            return html_content
        else:
            return "UDF içeriği ayrıştırılamadı", 500
    except Exception as e:
        print(f"UDF içeriği doğrudan görüntüleme hatası: {str(e)}")
        return f"UDF dosyası görüntülenirken hata oluştu: {str(e)}", 500

if __name__ == '__main__':
    with app.app_context():
        # Veritabanı tablolarının var olup olmadığını kontrol et,
        # yoksa oluştur (Mevcut verileri silmez)
        db.create_all()
        
        # Admin kullanıcısını kontrol et/oluştur
        create_admin_user()
        
    app.run(debug=True)