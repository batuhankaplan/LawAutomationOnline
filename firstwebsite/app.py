from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')

@app.route('/')
def anasayfa():
    return render_template('anasayfa.html')

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    surname = db.Column(db.String(150), nullable=False)
    tc = db.Column(db.String(11), unique=True, nullable=False)
    payments = db.relationship('Payment', backref='client', lazy=True)

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

@app.route('/dava_islemleri', methods=['GET', 'POST'])
def dava_islemleri():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_document = Document(filename=filename, user_id=1)  # user_id=1 olarak sabitlenmiştir
            db.session.add(new_document)
            db.session.commit()
        else:
            # Handle other form submissions for case search
            # ...existing code...
            pass
    documents = Document.query.all()
    cases = CaseFile.query.all()  # Adjust this query as needed
    return render_template('dava_islemleri.html', cases=cases, documents=documents)

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
        client = Client.query.filter_by(tc=tc).first()
        if not client:
            client = Client(name=name, surname=surname, tc=tc)
            db.session.add(client)
            db.session.commit()
        amount = request.form['amount']
        date = request.form['date']
        new_payment = Payment(amount=amount, date=datetime.strptime(date, '%Y-%m-%d'), client_id=client.id, user_id=1)  # user_id=1 olarak sabitlenmiştir
        db.session.add(new_payment)
        db.session.commit()
    clients = Client.query.all()
    return render_template('odemeler.html', clients=clients)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)