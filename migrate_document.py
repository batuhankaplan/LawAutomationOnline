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

            # Veritabanı tipini tespit et
            db_type = db.engine.dialect.name
            print(f'Detected database type: {db_type}')

            with db.engine.connect() as conn:
                # Kolonun var olup olmadığını kontrol et
                if db_type == 'sqlite':
                    # SQLite için PRAGMA kullan
                    result = conn.execute(text("PRAGMA table_info(document)"))
                    columns = [row[1] for row in result]
                elif db_type == 'postgresql':
                    # PostgreSQL için information_schema kullan
                    result = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name='document'"
                    ))
                    columns = [row[0] for row in result]
                else:
                    print(f'Unsupported database type: {db_type}')
                    return

                if 'parent_document_id' in columns:
                    print('Column parent_document_id already exists!')
                    return

                # Kolonu ekle
                print(f'Adding column to {db_type} database...')
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
