#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check attachments in database
"""

import sys
sys.path.insert(0, 'firstwebsite')

from app import app, db
from models import Document

def check_attachments():
    with app.app_context():
        print('Checking documents...')

        # Tüm belgeleri getir
        all_docs = Document.query.all()
        print(f'\nTotal documents: {len(all_docs)}')

        # Ana belgeleri say
        main_docs = Document.query.filter_by(parent_document_id=None).all()
        print(f'Main documents: {len(main_docs)}')

        # Ek belgeleri say
        attachments = Document.query.filter(Document.parent_document_id != None).all()
        print(f'Attachments: {len(attachments)}')

        # Son 5 belgeyi detaylı göster
        print('\n--- Last 5 Documents ---')
        recent_docs = Document.query.order_by(Document.id.desc()).limit(5).all()
        for doc in recent_docs:
            print(f'ID: {doc.id} | Filename: {doc.filename} | Parent ID: {doc.parent_document_id} | Case ID: {doc.case_id}')

        # Eğer ek belgeler varsa onları göster
        if attachments:
            print('\n--- All Attachments ---')
            for att in attachments:
                parent = Document.query.get(att.parent_document_id)
                print(f'Attachment ID: {att.id} | Filename: {att.filename} | Parent: {parent.filename if parent else "NOT FOUND"}')

if __name__ == '__main__':
    check_attachments()
