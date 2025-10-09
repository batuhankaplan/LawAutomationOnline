"""
Payment Document API Endpoints
Ödeme Belge Yükleme/Silme/Güncelleme API'leri
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from models import db, Client, PaymentDocument, ActivityLog
import os
import uuid


def register_payment_document_routes(app):
    """Ödeme belgesi route'larını app'e ekle"""

    @app.route('/api/upload_payment_document/<int:client_id>', methods=['POST'])
    @login_required
    def upload_payment_document(client_id):
        """Ödeme belgesi yükle"""
        try:
            client = Client.query.get_or_404(client_id)

            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'Dosya bulunamadı'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'Dosya seçilmedi'}), 400

            # Form verilerini al
            document_type = request.form.get('document_type', 'Diğer')
            document_name = request.form.get('document_name', file.filename)
            description = request.form.get('description', '')

            # Dosya uzantısını kontrol et
            allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx'}
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext not in allowed_extensions:
                return jsonify({'success': False, 'message': 'Geçersiz dosya türü'}), 400

            # Benzersiz dosya adı oluştur
            unique_filename = f"{uuid.uuid4()}_{file.filename}"

            # Klasörü oluştur
            payment_documents_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'payment_documents')
            os.makedirs(payment_documents_dir, exist_ok=True)

            # Dosyayı kaydet
            filepath = os.path.join(payment_documents_dir, unique_filename)
            file.save(filepath)

            # Veritabanına kaydet
            document = PaymentDocument(
                client_id=client_id,
                document_type=document_type,
                document_name=document_name,
                filename=unique_filename,
                filepath=f"payment_documents/{unique_filename}",
                description=description if description else None,
                user_id=current_user.id
            )
            db.session.add(document)
            db.session.commit()

            # Log kaydı
            log = ActivityLog(
                activity_type='odeme_belgesi_yukleme',
                description=f'Ödeme belgesi yüklendi: {document_name}',
                details={
                    'client_id': client_id,
                    'document_type': document_type,
                    'filename': unique_filename
                },
                user_id=current_user.id,
                related_payment_id=client_id
            )
            db.session.add(log)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Belge başarıyla yüklendi',
                'document': {
                    'id': document.id,
                    'document_type': document.document_type,
                    'document_name': document.document_name,
                    'description': document.description,
                    'upload_date': document.upload_date.strftime('%d.%m.%Y %H:%M')
                }
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/api/payment_document/<int:document_id>', methods=['PUT'])
    @login_required
    def update_payment_document(document_id):
        """Ödeme belgesi güncelle (isim ve açıklama)"""
        try:
            document = PaymentDocument.query.get_or_404(document_id)
            data = request.get_json()

            old_name = document.document_name
            document.document_name = data.get('document_name', document.document_name)
            document.description = data.get('description', document.description)

            db.session.commit()

            # Log kaydı
            log = ActivityLog(
                activity_type='odeme_belgesi_guncelleme',
                description=f'Ödeme belgesi güncellendi: {old_name} → {document.document_name}',
                details={
                    'document_id': document_id,
                    'old_name': old_name,
                    'new_name': document.document_name
                },
                user_id=current_user.id,
                related_payment_id=document.client_id
            )
            db.session.add(log)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Belge başarıyla güncellendi'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/api/payment_document/<int:document_id>', methods=['DELETE'])
    @login_required
    def delete_payment_document(document_id):
        """Ödeme belgesi sil"""
        try:
            document = PaymentDocument.query.get_or_404(document_id)

            # Dosyayı sil
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
            if os.path.exists(full_path):
                os.remove(full_path)

            # Veritabanından sil
            client_id = document.client_id
            document_name = document.document_name

            db.session.delete(document)
            db.session.commit()

            # Log kaydı
            log = ActivityLog(
                activity_type='odeme_belgesi_silme',
                description=f'Ödeme belgesi silindi: {document_name}',
                details={
                    'document_id': document_id,
                    'filename': document.filename
                },
                user_id=current_user.id,
                related_payment_id=client_id
            )
            db.session.add(log)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Belge başarıyla silindi'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


    @app.route('/api/download_payment_document/<int:document_id>')
    @login_required
    def download_payment_document(document_id):
        """Ödeme belgesini indir"""
        from flask import send_file
        try:
            document = PaymentDocument.query.get_or_404(document_id)
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)

            if not os.path.exists(full_path):
                return jsonify({'success': False, 'message': 'Dosya bulunamadı'}), 404

            return send_file(full_path, as_attachment=True, download_name=document.document_name)

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
