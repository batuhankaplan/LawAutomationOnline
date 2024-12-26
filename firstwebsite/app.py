from flask import Flask, render_template, redirect, url_for, request, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
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
    announcements = Announcement.query.all()
    return render_template('anasayfa.html', announcements=announcements)

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
    court = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    client_name = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/takvim')
def takvim():
    return render_template('takvim.html')

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
        court = request.form['court']
        year = request.form['year']
        case_number = request.form['case-number']
        client_name = request.form['client-name']
        new_case_file = CaseFile(file_type=file_type, court=court, year=year, case_number=case_number, client_name=client_name, user_id=1)  # user_id=1 olarak sabitlenmiştir
        db.session.add(new_case_file)
        db.session.commit()
    return render_template('dosya_ekle.html')

@app.route('/case_details/<int:case_id>', methods=['GET'])
def case_details(case_id):
    case_file = CaseFile.query.get(case_id)
    if case_file:
        return jsonify({
            'file_type': case_file.file_type,
            'court': case_file.court,
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
        case_file.court = data['court']
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)