#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add parent_document_id column
"""

import sys
sys.path.insert(0, 'firstwebsite')

from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            print('Creating parent_document_id column...')

            # Önce kolonun var olup olmadığını kontrol et
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(document)"))
                columns = [row[1] for row in result]

                if 'parent_document_id' in columns:
                    print('Column parent_document_id already exists!')
                    return

                # SQLite için kolon ekle (IF NOT EXISTS yok)
                conn.execute(text(
                    'ALTER TABLE document ADD COLUMN parent_document_id INTEGER REFERENCES document(id)'
                ))
                conn.commit()

            print('Migration completed successfully!')
            print('Column parent_document_id added to document table')

        except Exception as e:
            print(f'Error during migration: {e}')
            raise

if __name__ == '__main__':
    migrate()
