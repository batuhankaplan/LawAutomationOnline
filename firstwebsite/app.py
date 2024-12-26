from flask import Flask, render_template, redirect, url_for, request, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import locale

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clients.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'
db = SQLAlchemy(app)

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

@app.route('/')
def anasayfa():
    # Duyuruları al
    announcements = Announcement.query.all()
    
    # Dosya türlerine göre sayıları hesapla
    hukuk_count = CaseFile.query.filter_by(file_type='hukuk').count()
    ceza_count = CaseFile.query.filter_by(file_type='ceza').count()
    icra_count = CaseFile.query.filter_by(file_type='icra').count()
    
    return render_template('anasayfa.html', 
                         announcements=announcements,
                         hukuk_count=hukuk_count,
                         ceza_count=ceza_count,
                         icra_count=icra_count)

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

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)

class CaseFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_type = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    client_name = db.Column(db.String(150), nullable=False)
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
    event_type = db.Column(db.String(50), nullable=False)  # 'durusma', 'tahliye', 'is', 'randevu', 'diger'
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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
    
    return render_template('takvim.html', events=events_data)

@app.route('/dosyalarim', methods=['GET', 'POST'])
def dosyalarim():
    if request.method == 'POST':
        file_type = request.form['file-type']
        year = request.form['year']
        case_number = request.form['case-number']
        client_name = request.form['client-name']
        query = CaseFile.query
        if file_type:
            query = query.filter_by(file_type=file_type)
        if year:
            query = query.filter_by(year=year)
        if case_number:
            query = query.filter_by(case_number=case_number)
        if client_name:
            query = query.filter(CaseFile.client_name.ilike(f'%{client_name}%'))
        case_files = query.all()
    else:
        case_files = []
    return render_template('dosyalarim.html', case_files=case_files)

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
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False)

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
        file_type = request.form['file-type']
        year = request.form['year']
        case_number = request.form['case-number']
        client_name = request.form['client-name']
        query = CaseFile.query
        if file_type:
            query = query.filter_by(file_type=file_type)
        if year:
            query = query.filter_by(year=year)
        if case_number:
            query = query.filter_by(case_number=case_number)
        if client_name:
            query = query.filter(CaseFile.client_name.ilike(f'%{client_name}%'))
        case_files = query.all()
    else:
        case_files = []
    return render_template('dosya_sorgula.html', case_files=case_files)

@app.route('/dosya_ekle', methods=['GET', 'POST'])
def dosya_ekle():
    if request.method == 'POST':
        file_type = request.form['file-type']
        year = request.form['year']
        case_number = request.form['case-number']
        client_name = request.form['client-name']
        new_case_file = CaseFile(file_type=file_type, year=year, case_number=case_number, client_name=client_name, user_id=1)  # user_id=1 olarak sabitlenmiştir
        db.session.add(new_case_file)
        db.session.commit()
    return render_template('dosya_ekle.html')

@app.route('/case_details/<int:case_id>', methods=['GET'])
def case_details(case_id):
    case_file = CaseFile.query.get(case_id)
    if case_file:
        return jsonify({
            'file_type': case_file.file_type,
            'year': case_file.year,
            'case_number': case_file.case_number,
            'client_name': case_file.client_name
        })
    return jsonify(success=False)

@app.route('/edit_case/<int:case_id>', methods=['POST'])
def edit_case(case_id):
    data = request.get_json()
    case_file = CaseFile.query.get(case_id)
    if case_file:
        case_file.file_type = data['file_type']
        case_file.year = data['year']
        case_file.case_number = data['case_number']
        case_file.client_name = data['client_name']
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False)

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

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    # Tüm modellerde arama yapalım
    results = []
    
    # Dosyalarda arama
    case_files = CaseFile.query.filter(
        db.or_(
            CaseFile.client_name.ilike(f'%{query}%'),
            CaseFile.case_number.ilike(f'%{query}%'),
            CaseFile.file_type.ilike(f'%{query}%')
        )
    ).limit(5).all()
    
    for case in case_files:
        results.append({
            'type': 'Dosya',
            'title': f'{case.client_name} - {case.case_number}',
            'url': url_for('dosyalarim')
        })
    
    # Müşterilerde arama
    clients = Client.query.filter(
        db.or_(
            Client.name.ilike(f'%{query}%'),
            Client.surname.ilike(f'%{query}%'),
            Client.tc.ilike(f'%{query}%')
        )
    ).limit(5).all()
    
    for client in clients:
        results.append({
            'type': 'Müşteri',
            'title': f'{client.name} {client.surname}',
            'url': url_for('odemeler')
        })
    
    # Duyurularda arama
    announcements = Announcement.query.filter(
        db.or_(
            Announcement.title.ilike(f'%{query}%'),
            Announcement.content.ilike(f'%{query}%')
        )
    ).limit(5).all()
    
    for announcement in announcements:
        results.append({
            'type': 'Duyuru',
            'title': announcement.title,
            'url': url_for('duyurular')
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
        event.event_type = data['event_type']
        event.description = data['description']
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)