"""
PaymentClient tablosunu olustur
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'firstwebsite'))

from models import db
from app import app

def create_table():
    """Yeni tablo olustur"""
    with app.app_context():
        print("PaymentClient tablosu olusturuluyor...")

        create_payment_client_table = """
        CREATE TABLE IF NOT EXISTS payment_client (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type VARCHAR(20) NOT NULL DEFAULT 'person',
            name VARCHAR(200) NOT NULL,
            surname VARCHAR(100),
            identity_number VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user(id)
        );
        """

        add_column_to_client = """
        ALTER TABLE client ADD COLUMN payment_client_id INTEGER;
        """

        try:
            db.session.execute(db.text(create_payment_client_table))
            print("'payment_client' tablosu olusturuldu")

            try:
                db.session.execute(db.text(add_column_to_client))
                print("'client' tablosuna 'payment_client_id' kolonu eklendi")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("'payment_client_id' kolonu zaten var")
                else:
                    raise

            db.session.commit()
            print("\nTablo basariyla olusturuldu!")

        except Exception as e:
            db.session.rollback()
            print(f"Hata olustu: {str(e)}")
            raise

if __name__ == '__main__':
    create_table()
