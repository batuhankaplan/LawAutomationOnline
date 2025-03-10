from flask import Flask, render_template, request, url_for, flash, redirect, jsonify, session, send_from_directory, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import json
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import locale
import time
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

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission):
                flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
                return redirect(url_for('anasayfa'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/database.db'
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
                        unique_filename = f"images/profile_{user.id}_{int(time.time())}_{filename}"
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
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bu sayfaya erişim yetkiniz yok.', 'error')
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

def log_activity(activity_type, description, user_id, case_id=None):
    user = User.query.get(user_id)
    if user:
        activity = ActivityLog(
            activity_type=activity_type,
            description=description.format(user_name=user.get_full_name()),
            user_id=user_id,
            related_case_id=case_id
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
    
    # Duyuruları al
    announcements = Announcement.query.all()
    
    # Dosya türlerine göre sayıları hesapla
    hukuk_count = CaseFile.query.filter_by(file_type='hukuk').count()
    ceza_count = CaseFile.query.filter_by(file_type='ceza').count()
    icra_count = CaseFile.query.filter_by(file_type='icra').count()
    
    # Son aktiviteleri al (ilk 5 işlem)
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
    # Toplam aktivite sayısını al
    total_activities = ActivityLog.query.count()
    
    # Yaklaşan duruşmaları al (sadece ilk 3)
    upcoming_hearings = CalendarEvent.query.filter(
        CalendarEvent.date >= datetime.now().date(),
        CalendarEvent.event_type == 'durusma'
    ).order_by(CalendarEvent.date, CalendarEvent.time).limit(3).all()
    
    # Toplam duruşma sayısını al
    total_hearings = CalendarEvent.query.filter(
        CalendarEvent.date >= datetime.now().date(),
        CalendarEvent.event_type == 'durusma'
    ).count()
    
    # Toplam aktif dosya sayısını hesapla
    total_active_cases = CaseFile.query.filter_by(status='Aktif').count()
    
    # Adliye istatistiklerini al (en çok dosyası olan ilk 4 adliye)
    courthouse_stats = db.session.query(
        CaseFile.courthouse,
        db.func.count(CaseFile.id).label('total_cases')
    ).group_by(CaseFile.courthouse)\
    .order_by(db.func.count(CaseFile.id).desc())\
    .limit(4).all()
    
    # Her aktivite için kullanıcı bilgisini ve detayları ekle
    activities_with_details = []
    for activity in recent_activities:
        user = User.query.get(activity.user_id)
        activity_data = {
            'type': activity.activity_type,
            'description': activity.description,
            'timestamp': activity.timestamp,
            'user': user.get_full_name() if user else 'Bilinmeyen Kullanıcı',
            'details': activity.details
        }
        activities_with_details.append(activity_data)
    
    return render_template('anasayfa.html', 
                         announcements=announcements,
                         hukuk_count=hukuk_count,
                         ceza_count=ceza_count,
                         icra_count=icra_count,
                         total_active_cases=total_active_cases,
                         recent_activities=activities_with_details,
                         total_activities=total_activities,
                         upcoming_hearings=upcoming_hearings,
                         total_hearings=total_hearings,
                         courthouse_stats=courthouse_stats)

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
    events_data = [{
        'id': event.id,
        'title': event.title,
        'date': event.date.strftime('%Y-%m-%d'),
        'time': event.time.strftime('%H:%M'),
        'event_type': event.event_type,
        'description': event.description,
        'assigned_to': event.assigned_to,
        'deadline_date': event.deadline_date.strftime('%Y-%m-%d') if event.deadline_date else None,
        'is_completed': event.is_completed
    } for event in events]
    
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
    
    announcements = Announcement.query.all()
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
        amount = request.form['amount']
        currency = request.form['currency']
        installments = request.form['installments']
        date = request.form['date']
        
        new_client = Client(name=name, surname=surname, tc=tc, amount=amount, currency=currency, installments=installments, date=date)
        db.session.add(new_client)
        
        # Log kaydı
        log = ActivityLog(
            activity_type='odeme_ekleme',
            description=f'Yeni ödeme eklendi: {name} {surname}',
            details={
                'musteri': f'{name} {surname}',
                'tc': tc,
                'tutar': f'{amount} {currency}',
                'taksit': installments,
                'tarih': date
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
        return jsonify({'success': False, 'error': 'Ödeme düzenleme yetkiniz bulunmamaktadır.'}), 403
        
    data = request.get_json()
    client = Client.query.get(client_id)
    if client:
        old_status = client.status
        client.name = data['name']
        client.surname = data['surname']
        client.tc = data['tc']
        client.amount = data['amount']
        client.currency = data['currency']
        client.installments = data['installments']
        client.date = data['date']
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
        
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Müşteri bulunamadı'})

@app.route('/delete_client/<int:client_id>', methods=['DELETE'])
@login_required
def delete_client(client_id):
    if not current_user.has_permission('odeme_sil'):
        return jsonify({'success': False, 'error': 'Ödeme silme yetkiniz bulunmamaktadır.'}), 403
        
    try:
        client = Client.query.get(client_id)
        if client:
            # İlgili ödemeleri sil
            Payment.query.filter_by(client_id=client_id).delete()
            
            # Müşteriyi sil
            db.session.delete(client)
            db.session.commit()
            
            # Aktivite loguna kaydet
            log_activity(
                'delete',
                f'Ödeme silindi: {client.name} {client.surname}',
                current_user.id
            )
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Müşteri bulunamadı'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/musteri_sorgula', methods=['GET', 'POST'])
def musteri_sorgula():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        tc = request.form['tc']
        query = Client.query
        if name:
            query = query.filter(Client.name.ilike(f'%{name}%'))
        if surname:
            query = query.filter(Client.surname.ilike(f'%{surname}%'))
        if tc:
            query = query.filter_by(tc=tc)
        clients = query.all()
    else:
        clients = []
    return render_template('musteri_sorgula.html', clients=clients)

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
        courthouse = request.form.get('courthouse')
        department = request.form.get('department')
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
    
    return render_template('dosya_sorgula.html', 
                         case_files=case_files)

@app.route('/dosya_ekle', methods=['GET', 'POST'])
@login_required
@permission_required('dosya_ekle')
def dosya_ekle():
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Tüm gerekli alanların dolu olduğunu kontrol et
            required_fields = ['file-type', 'courthouse', 'department', 'year', 'case-number', 'client-name', 'open-date']
            if not all(data.get(field) for field in required_fields):
                return jsonify(success=False, message="Tüm alanları doldurunuz"), 400
            
            new_case_file = CaseFile(
                file_type=data['file-type'],
                courthouse=data['courthouse'],
                department=data['department'],
                year=int(data['year']),
                case_number=data['case-number'],
                client_name=data['client-name'],
                phone_number=data.get('phone-number', ''),
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
            
            return jsonify(success=True)
            
        except Exception as e:
            db.session.rollback()
            print(f"Hata: {str(e)}")
            return jsonify(success=False, message=str(e)), 400
        
    # GET isteği için bugünün tarihini gönder
    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('dosya_ekle.html', today_date=today_date)

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
def edit_case(case_id):
    try:
        data = request.get_json()
        case_file = db.session.get(CaseFile, case_id)
        if case_file:
            case_file.client_name = data.get('client_name', case_file.client_name)
            case_file.phone_number = data.get('phone_number', case_file.phone_number)
            case_file.status = data.get('status', case_file.status)
            case_file.description = data.get('description', case_file.description)
            case_file.hearing_time = data.get('hearing_time', case_file.hearing_time)  # Güncellenen hearing_time alanı
            
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
        
        event = CalendarEvent(
            title=data['title'],
            date=event_date,
            time=event_time,
            event_type=data['event_type'],
            description=data.get('description', ''),
            user_id=current_user.id,
            assigned_to=data.get('assigned_to', ''),
            deadline_date=deadline_date,
            is_completed=data.get('is_completed', False)
        )
        
        db.session.add(event)
        
        # Log kaydı
        log_details = {
            'baslik': data['title'],
            'tarih': date_str,
            'saat': time_str,
            'tur': data['event_type'],
            'aciklama': data.get('description', ''),
        }
        
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
                description=event.description,
                user_id=event.user_id,
                assigned_to=event.assigned_to,
                is_completed=event.is_completed
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
            'description': event.description,
            'assigned_to': event.assigned_to,
            'is_completed': event.is_completed
        }
        
        if deadline_date:
            response_data['deadline_date'] = deadline_date.strftime('%Y-%m-%d')
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Etkinlik ekleme hatası: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400

@app.route('/update_event/<int:event_id>', methods=['PUT', 'POST'])
@login_required
@permission_required('etkinlik_duzenle')
def update_event(event_id):
    try:
        event = CalendarEvent.query.get_or_404(event_id)
        
        # JSON verisini güvenli bir şekilde al
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Geçersiz JSON verisi'}), 400
        except Exception as json_error:
            app.logger.error(f"JSON işleme hatası: {str(json_error)}")
            return jsonify({'error': 'Geçersiz JSON formatı'}), 400
        
        app.logger.info(f"Etkinlik güncelleme isteği alındı: {event_id}, Veri: {data}")
        
        # Eski değerleri kaydet
        old_title = event.title
        old_date = event.date
        old_time = event.time
        
        # Tarihleri UTC'ye çevirmeden işle
        date_str = data.get('date')
        time_str = data.get('time')
        deadline_str = data.get('deadline_date')
        
        if not date_str or not time_str:
            return jsonify({'error': 'Tarih ve saat alanları zorunludur'}), 400
        
        # Tarihleri doğrudan string'den date objesine çevir
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            event_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError as e:
            app.logger.error(f"Tarih/saat çevirme hatası: {e}")
            return jsonify({'error': 'Geçersiz tarih veya saat formatı'}), 400
        
        # deadline_date kontrolü - eğer varsa çevir, yoksa None olarak bırak
        deadline_date = None
        if deadline_str:
            try:
                deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError as e:
                app.logger.error(f"deadline_date çevirme hatası: {e}")
                # Hata durumunda deadline_date None olarak kalır
        
        # Verileri güncelle
        event.title = data.get('title', '')
        event.date = event_date
        event.time = event_time
        event.event_type = data.get('event_type', '')
        event.description = data.get('description', '')
        event.assigned_to = data.get('assigned_to', '')
        event.is_completed = data.get('is_completed', False)
        
        # Log kaydı
        log_details = {
            'eski_baslik': old_title,
            'yeni_baslik': event.title,
            'eski_tarih': old_date.strftime('%Y-%m-%d'),
            'yeni_tarih': event_date.strftime('%Y-%m-%d'),
            'eski_saat': old_time.strftime('%H:%M'),
            'yeni_saat': event_time.strftime('%H:%M'),
            'tur': data.get('event_type', ''),
            'aciklama': data.get('description', ''),
        }
        
        if deadline_str:
            log_details['son_tarih'] = deadline_str
        
        log = ActivityLog(
            activity_type='etkinlik_duzenleme',
            description=f'Etkinlik düzenlendi: {old_title}',
            details=log_details,
            user_id=current_user.id,
            related_event_id=event.id
        )
        db.session.add(log)
        
        # Deadline işlemleri
        if deadline_date:
            event.deadline_date = deadline_date
            
            # Eski son gün etkinliğini sil
            old_deadline_event = CalendarEvent.query.filter_by(
                title=f"SON GÜN: {old_title}",
                event_type=event.event_type
            ).first()
            if old_deadline_event:
                db.session.delete(old_deadline_event)
            
            # Yeni son gün etkinliği ekle
            if deadline_date != event_date:
                deadline_event = CalendarEvent(
                    title=f"SON GÜN: {event.title}",
                    date=deadline_date,
                    time=event_time,
                    event_type=event.event_type,
                    description=event.description,
                    user_id=event.user_id,
                    assigned_to=event.assigned_to,
                    is_completed=event.is_completed
                )
                db.session.add(deadline_event)
        
        db.session.commit()
        app.logger.info(f"Etkinlik başarıyla güncellendi: {event.id}")
        
        response_data = {
            'id': event.id,
            'title': event.title,
            'date': event_date.strftime('%Y-%m-%d'),
            'time': event_time.strftime('%H:%M'),
            'event_type': event.event_type,
            'description': event.description,
            'assigned_to': event.assigned_to,
            'is_completed': event.is_completed
        }
        
        if deadline_date:
            response_data['deadline_date'] = deadline_date.strftime('%Y-%m-%d')
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Etkinlik güncelleme hatası: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400

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
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

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
            unique_filename = f"{case_id}_{int(time.time())}_{original_filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            
            new_document = Document(
                case_id=case_id,
                document_type=document_type,
                filename=f"{display_name}.{file_ext}",  # Görünen isim
                filepath=unique_filename,  # Gerçek dosya yolu
                upload_date=datetime.now(),
                user_id=1
            )
            
            db.session.add(new_document)
            db.session.commit()
            
            # İşlem logu ekle
            case_file = CaseFile.query.get(case_id)
            log_activity(
                activity_type='belge_yukleme',
                description=f"Yeni belge yüklendi: {case_file.client_name} - {document_type} ({custom_name or file.filename})",
                user_id=1,
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
        # Geçici PDF dosyası için path oluştur
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            output_path = tmp_pdf.name
        
        # unoconv ile UDF'yi PDF'e dönüştür
        result = subprocess.run(
            ['unoconv', '-f', 'pdf', '-o', output_path, input_path], 
            check=True,
            capture_output=True,
            text=True
        )
        
        # Dönüştürme başarılı mı kontrol et
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            print(f"Dönüştürme başarısız. Çıktı dosyası oluşturulamadı veya boş.")
            if result.stderr:
                print(f"Hata çıktısı: {result.stderr}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"unoconv çalıştırma hatası: {str(e)}")
        if e.stderr:
            print(f"Hata çıktısı: {e.stderr}")
        return None
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        return None

@app.route('/preview_document/<int:document_id>')
def preview_document(document_id):
    document = Document.query.get_or_404(document_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
    
    # Dosya uzantısını kontrol et
    ext = document.filename.rsplit('.', 1)[1].lower()
    
    if ext in ['jpg', 'jpeg', 'png', 'tiff', 'tif']:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            document.filepath,
            mimetype=f'image/{ext}'
        )
    elif ext == 'pdf':
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            document.filepath,
            mimetype='application/pdf'
        )
    else:
        return jsonify(success=False, message="Bu dosya türü için önizleme kullanılamıyor.")

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
        hearing_date = data.get('hearing_date')
        hearing_time = data.get('hearing_time', '09:00')
        status = data.get('status')
        
        case_file = CaseFile.query.get(case_id)
        if not case_file:
            return jsonify(success=False, message="Dosya bulunamadı")

        existing_event = CalendarEvent.query.filter_by(
            case_id=case_id,
            event_type='durusma'
        ).first()

        if status == 'Kapalı' or not hearing_date:
            if existing_event:
                db.session.delete(existing_event)
                db.session.commit()
                log_activity(
                    activity_type='durusma_silme',
                    description=f"Duruşma kaydı silindi: {case_file.client_name} - {case_file.case_number}",
                    user_id=1,
                    case_id=case_id
                )
            return jsonify(success=True)

        event_date = datetime.strptime(hearing_date, '%Y-%m-%d').date()
        event_time = datetime.strptime(hearing_time, '%H:%M').time()
        
        if existing_event:
            existing_event.date = event_date
            existing_event.time = event_time
            existing_event.title = f"Duruşma - {case_file.client_name} ({case_file.case_number})"
            existing_event.description = f"Dosya Türü: {case_file.file_type}\nAdliye: {case_file.courthouse}\nBirim: {case_file.department}"
            log_activity(
                activity_type='durusma_guncelleme',
                description=f"Duruşma güncellendi: {case_file.client_name} - {event_date.strftime('%d.%m.%Y')} {event_time.strftime('%H:%M')}",
                user_id=1,
                case_id=case_id
            )
        else:
            new_event = CalendarEvent(
                title=f"Duruşma - {case_file.client_name} ({case_file.case_number})",
                date=event_date,
                time=event_time,
                event_type='durusma',
                description=f"Dosya Türü: {case_file.file_type}\nAdliye: {case_file.courthouse}\nBirim: {case_file.department}",
                user_id=1,
                case_id=case_id
            )
            db.session.add(new_event)
            log_activity(
                activity_type='durusma_ekleme',
                description=f"Yeni duruşma eklendi: {case_file.client_name} - {event_date.strftime('%d.%m.%Y')} {event_time.strftime('%H:%M')}",
                user_id=1,
                case_id=case_id
            )
        
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e))

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
def update_description(case_id):
    try:
        data = request.get_json()
        case_file = CaseFile.query.get_or_404(case_id)
        
        case_file.description = data.get('description', '')
        db.session.commit()
        
        return jsonify(success=True)
    except Exception as e:
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
    try:
        user = User.query.get_or_404(user_id)
        return jsonify({
            'success': True,
            'permissions': user.permissions or {}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/admin/update_user_permissions/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def update_user_permissions(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Yetkileri güncelle
        user.permissions = data.get('permissions', {})
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Kullanıcı yetkileri güncellendi'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

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

@app.route('/isci_gorusme')
@login_required
def isci_gorusme():
    return render_template('isci_gorusme.html')

@app.route('/save_worker_interview', methods=['POST'])
@login_required
def save_worker_interview():
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

@app.route('/save_isci_gorusme', methods=['POST'])
@login_required
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

# Kaydedilmiş formları getirme
@app.route('/get_isci_gorusme_forms')
@login_required
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

@app.route('/worker_interview')
@login_required
def worker_interview():
    return render_template('worker_interview.html')

if __name__ == '__main__':
    with app.app_context():
        # Mevcut veritabanını sil
        db.drop_all()
        # Yeni şema ile veritabanını oluştur
        db.create_all()
        
        # Admin kullanıcısını oluştur
        admin_user = User.query.filter_by(email='admin@kaplanhukuk.com').first()
        if not admin_user:
            admin_user = User(
                email='admin@kaplanhukuk.com',
                username='admin',
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
    
    app.run(debug=True)