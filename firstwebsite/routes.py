from flask import request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from firstwebsite.models import db, Announcement, CalendarEvent, ActivityLog
from firstwebsite import app

# Duyuru ekleme route'u
@app.route('/duyuru_ekle', methods=['POST'])
@login_required
def duyuru_ekle():
    if not current_user.duyuru_ekle:
        flash('Duyuru ekleme yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('anasayfa'))
    
    title = request.form.get('title')
    content = request.form.get('content')
    
    duyuru = Announcement(title=title, content=content)
    db.session.add(duyuru)
    db.session.commit()
    
    # Log kaydı
    log = ActivityLog(
        activity_type='duyuru_ekleme',
        description=f'Yeni duyuru eklendi: {title}',
        details={
            'baslik': title,
            'icerik': content[:50] + '...' if len(content) > 50 else content
        },
        user_id=current_user.id,
        related_announcement_id=duyuru.id
    )
    db.session.add(log)
    db.session.commit()
    
    flash('Duyuru başarıyla eklendi.', 'success')
    return redirect(url_for('anasayfa'))

# Takvim etkinlik ekleme route'u
@app.route('/etkinlik_ekle', methods=['POST'])
@login_required
def etkinlik_ekle():
    if not current_user.etkinlik_ekle:
        flash('Etkinlik ekleme yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('takvim'))
    
    title = request.form.get('title')
    start = request.form.get('start')
    end = request.form.get('end')
    
    etkinlik = CalendarEvent(title=title, start=start, end=end)
    db.session.add(etkinlik)
    db.session.commit()
    
    # Log kaydı
    log = ActivityLog(
        activity_type='etkinlik_ekleme',
        description=f'Yeni etkinlik eklendi: {title}',
        details={
            'baslik': title,
            'tarih': start.split('T')[0],
            'saat': start.split('T')[1][:5]
        },
        user_id=current_user.id,
        related_event_id=etkinlik.id
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success'})

# Etkinlik silme route'u
@app.route('/etkinlik_sil/<int:id>', methods=['DELETE'])
@login_required
def etkinlik_sil(id):
    if not current_user.etkinlik_sil:
        return jsonify({'status': 'error', 'message': 'Etkinlik silme yetkiniz bulunmamaktadır.'})
    
    etkinlik = CalendarEvent.query.get_or_404(id)
    
    # Log kaydı
    log = ActivityLog(
        activity_type='etkinlik_silme',
        description=f'Etkinlik silindi: {etkinlik.title}',
        details={
            'baslik': etkinlik.title,
            'tarih': etkinlik.start.strftime('%d.%m.%Y'),
            'saat': etkinlik.start.strftime('%H:%M')
        },
        user_id=current_user.id
    )
    
    db.session.delete(etkinlik)
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success'})

# Etkinlik düzenleme route'u
@app.route('/etkinlik_duzenle/<int:id>', methods=['PUT'])
@login_required
def etkinlik_duzenle(id):
    if not current_user.etkinlik_duzenle:
        return jsonify({'status': 'error', 'message': 'Etkinlik düzenleme yetkiniz bulunmamaktadır.'})
    
    etkinlik = CalendarEvent.query.get_or_404(id)
    data = request.get_json()
    
    old_title = etkinlik.title
    old_start = etkinlik.start
    
    etkinlik.title = data.get('title', etkinlik.title)
    etkinlik.start = data.get('start', etkinlik.start)
    etkinlik.end = data.get('end', etkinlik.end)
    
    # Log kaydı
    log = ActivityLog(
        activity_type='etkinlik_duzenleme',
        description=f'Etkinlik düzenlendi: {old_title}',
        details={
            'eski_baslik': old_title,
            'yeni_baslik': etkinlik.title,
            'eski_tarih': old_start.strftime('%d.%m.%Y %H:%M'),
            'yeni_tarih': etkinlik.start.strftime('%d.%m.%Y %H:%M')
        },
        user_id=current_user.id,
        related_event_id=etkinlik.id
    )
    
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success'}) 