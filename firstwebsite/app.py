from flask import Flask, render_template, request, url_for, flash, redirect, jsonify, session
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
from uyap_integration import UYAPIntegration

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAIL_SERVER'] = 'smtp-mail.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yzbatuhankaplan@outlook.com'
app.config['MAIL_PASSWORD'] = 'your_mail_password'  # Mail şifrenizi buraya yazın
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Migrate nesnesini oluştur
mail = Mail(app)

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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False)  # 'dosya_ekleme', 'masraf_ekleme', 'belge_yukleme', vs.
    description = db.Column(db.String(250), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    related_case_id = db.Column(db.Integer, db.ForeignKey('case_file.id'), nullable=True)

def log_activity(activity_type, description, user_id, case_id=None):
    activity = ActivityLog(
        activity_type=activity_type,
        description=description,
        user_id=user_id,
        related_case_id=case_id
    )
    db.session.add(activity)
    db.session.commit()

@app.route('/')
def anasayfa():
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
    
    return render_template('anasayfa.html', 
                         announcements=announcements,
                         hukuk_count=hukuk_count,
                         ceza_count=ceza_count,
                         icra_count=icra_count,
                         total_active_cases=total_active_cases,
                         recent_activities=recent_activities,
                         total_activities=total_activities,
                         upcoming_hearings=upcoming_hearings,
                         total_hearings=total_hearings,
                         courthouse_stats=courthouse_stats)

# Daha fazla aktivite yüklemek için yeni endpoint
@app.route('/load_more_activities/<int:offset>')
def load_more_activities(offset):
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).offset(offset).limit(5).all()
    
    activities_data = [{
        'type': activity.activity_type,
        'description': activity.description,
        'timestamp': activity.timestamp.strftime('%d.%m.%Y %H:%M')
    } for activity in activities]
    
    return jsonify(activities=activities_data)

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
    description = db.Column(db.Text, nullable=True)  # Açıklama alanı eklendi

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
    expenses = db.relationship('Expense', backref='case_file', lazy=True)
    documents = db.relationship('Document', backref='case_file', lazy=True)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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

# Adli tatil tarihlerini kontrol eden fonksiyon
def is_adli_tatil(date):
    # Adli tatil: 20 Temmuz - 31 Ağustos arası
    if date.month == 7 and date.day >= 20:
        return True
    if date.month == 8:
        return True
    return False

@app.route('/takvim')
def takvim():
    events = CalendarEvent.query.all()
    events_data = [{
        'id': event.id,
        'title': event.title,
        'date': event.date.strftime('%Y-%m-%d'),
        'time': event.time.strftime('%H:%M'),
        'event_type': event.event_type,
        'description': event.description
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
    
    return render_template('takvim.html', 
                         events=events_data,
                         adli_tatil_data=adli_tatil_data)

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
def duyurular():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_announcement = Announcement(title=title, content=content, user_id=1)  # user_id=1 olarak sabitlenmiştir
        db.session.add(new_announcement)
        db.session.commit()
    announcements = Announcement.query.all()
    return render_template('duyurular.html', announcements=announcements)

@app.route('/odemeler', methods=['GET', 'POST'])
def odemeler():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        tc = request.form['tc']
        amount = request.form['amount']
        currency = request.form['currency']
        installments = request.form['installments']
        date = request.form['date']
        
        new_client = Client(name=name, surname=surname, tc=tc, amount=amount, currency=currency, installments=installments, date=date)
        db.session.add(new_client)
        db.session.commit()
        
        return redirect(url_for('odemeler'))
    
    clients = Client.query.all()
    return render_template('odemeler.html', clients=clients)

@app.route('/update_client/<int:client_id>', methods=['POST'])
def update_client(client_id):
    data = request.get_json()
    client = Client.query.get(client_id)
    if client:
        client.name = data['name']
        client.surname = data['surname']
        client.tc = data['tc']
        client.amount = data['amount']
        client.currency = data['currency']
        client.installments = data['installments']
        client.date = data['date']
        client.status = data['status']
        client.description = data.get('description', '')  # Açıklama alanını güncelle
        
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Müşteri bulunamadı'})

@app.route('/delete_client/<int:client_id>', methods=['DELETE'])  # POST yerine DELETE metodu
def delete_client(client_id):
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
                1  # TODO: Gerçek kullanıcı ID'sini kullan
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
                user_id=1
            )
            
            db.session.add(new_case_file)
            db.session.commit()
            
            # İşlem logu ekle
            log_activity(
                activity_type='dosya_ekleme',
                description=f"Yeni dosya eklendi: {data['client-name']} - {data['case-number']}",
                user_id=1,
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
def add_event():
    data = request.get_json()
    
    # Tarih ve saat bilgisini birleştir
    date_time_str = f"{data['date']} {data['time']}"
    date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
    
    new_event = CalendarEvent(
        title=data['title'],
        date=date_time_obj.date(),
        time=date_time_obj.time(),
        event_type=data['event_type'],
        description=data['description'],
        user_id=1
    )
    
    db.session.add(new_event)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': new_event.id
    })

@app.route('/update_event/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    data = request.get_json()
    event = CalendarEvent.query.get(event_id)
    
    if event:
        event.title = data['title']
        event.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        event.time = datetime.strptime(data['time'], '%H:%M').time()
        event.event_type = data['event_type']
        event.description = data['description']
        
        # Eğer etkinlik bir duruşma ise ve bir dosyaya bağlıysa
        if event.case_id and event.event_type in ['durusma', 'e-durusma']:
            case = CaseFile.query.get(event.case_id)
            if case:
                case.next_hearing = event.date
                case.hearing_time = event.time.strftime('%H:%M')
        
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    event = CalendarEvent.query.get(event_id)
    if event:
        db.session.delete(event)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            'yasal': 9.0,  # Yasal faiz oranı
            'mevduat': 45.0  # En yüksek mevduat faizi
        }
        return rates
    except:
        # Hata durumunda varsayılan değerleri döndür
        return {
            'reeskont': 13.75,
            'avans': 14.75,
            'temerrut': 19.0,
            'yasal': 9.0,
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

@app.route('/uyap_sync', methods=['POST'])
def uyap_sync():
    try:
        print("UYAP senkronizasyonu başlatılıyor...")
        uyap = UYAPIntegration()
        
        # UYAP'a giriş yap
        print("UYAP'a giriş yapılıyor...")
        if not uyap.login():
            error_msg = "UYAP girişi başarısız oldu. Lütfen e-imza ile giriş yaptığınızdan emin olun."
            print(error_msg)
            return jsonify(success=False, message=error_msg)
        
        print("UYAP'a giriş başarılı, dosyalar çekiliyor...")
        # Dosyaları çek
        cases = uyap.get_case_files()
        
        if not cases:
            error_msg = "Hiç dosya bulunamadı. Bu durum şunlardan kaynaklanabilir:\n" + \
                       "1. Menü öğeleri bulunamadı\n" + \
                       "2. Dosya türü veya yargı birimi seçilemedi\n" + \
                       "3. Sorgulama sonucu döndürülemedi"
            print(error_msg)
            return jsonify(success=False, message=error_msg)
        
        print(f"{len(cases)} adet dosya bulundu, veritabanına kaydediliyor...")
        # Her dosya için veritabanına kaydet
        saved_count = 0
        for case in cases:
            try:
                # Dosya detaylarını çek
                details = uyap.get_case_details(case['dosya_no'])
                
                # Mevcut dosyayı kontrol et
                existing_case = CaseFile.query.filter_by(
                    case_number=case['dosya_no']
                ).first()
                
                if existing_case:
                    print(f"Mevcut dosya güncelleniyor: {case['dosya_no']}")
                    # Mevcut dosyayı güncelle
                    existing_case.courthouse = case['mahkeme']
                    existing_case.status = case['durum']
                    if details:
                        existing_case.next_hearing = details.get('durusma_tarihi')
                        existing_case.hearing_time = details.get('durusma_saati')  # Güncellenen hearing_time alanı
                        existing_case.description = details.get('son_islem')
                    saved_count += 1
                else:
                    print(f"Yeni dosya ekleniyor: {case['dosya_no']}")
                    # Yeni dosya oluştur
                    new_case = CaseFile(
                        file_type=case['dosya_turu'].lower(),
                        courthouse=case['mahkeme'],
                        department=case['yargi_birimi'],
                        year=int(case['dosya_no'].split('/')[0]) if '/' in case['dosya_no'] else datetime.now().year,
                        case_number=case['dosya_no'],
                        client_name=case['taraflar'].split('/')[-1].strip(),
                        phone_number=case.get('phone_number', ''),
                        status=case['durum'],
                        description=case.get('son_islem', ''),
                        hearing_time=case.get('durusma_saati', ''),  # Güncellenen hearing_time alanı
                        user_id=1  # Aktif kullanıcı ID'si
                    )
                    db.session.add(new_case)
                    saved_count += 1
            except Exception as e:
                print(f"Dosya kaydedilirken hata: {str(e)}")
                continue
        
        try:
            db.session.commit()
            print(f"Veritabanına {saved_count} dosya kaydedildi.")
        except Exception as e:
            db.session.rollback()
            error_msg = f"Veritabanı kayıt hatası: {str(e)}"
            print(error_msg)
            return jsonify(success=False, message=error_msg)
        
        uyap.close()
        return jsonify(success=True, message=f"{saved_count} dosya senkronize edildi")
        
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(error_msg)
        return jsonify(success=False, message=error_msg)

if __name__ == '__main__':
    with app.app_context():
        # Mevcut veritabanını sil
        db.drop_all()
        # Yeni şema ile veritabanını oluştur
        db.create_all()
    
    app.run(debug=True)