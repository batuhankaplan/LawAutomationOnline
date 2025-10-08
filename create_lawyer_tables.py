"""
Lawyer ve PartyLawyer tablolarını oluştur
"""
import sys
import os

# firstwebsite modülünü import edebilmek için path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'firstwebsite'))

from models import db
from app import app

def create_tables():
    """Yeni tabloları oluştur"""
    with app.app_context():
        print("Yeni tablolar olusturuluyor...")

        # SQL komutları
        create_lawyer_table = """
        CREATE TABLE IF NOT EXISTS lawyer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(150) NOT NULL,
            bar VARCHAR(100),
            bar_number VARCHAR(20),
            phone VARCHAR(20),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            case_id INTEGER NOT NULL,
            FOREIGN KEY (case_id) REFERENCES case_file(id) ON DELETE CASCADE
        );
        """

        create_party_lawyer_table = """
        CREATE TABLE IF NOT EXISTS party_lawyer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lawyer_id INTEGER NOT NULL,
            party_type VARCHAR(20) NOT NULL,
            party_index INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lawyer_id) REFERENCES lawyer(id) ON DELETE CASCADE
        );
        """

        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_lawyer_case_id ON lawyer(case_id);
        CREATE INDEX IF NOT EXISTS idx_party_lawyer_lawyer_id ON party_lawyer(lawyer_id);
        CREATE INDEX IF NOT EXISTS idx_party_lawyer_type_index ON party_lawyer(party_type, party_index);
        """

        try:
            # Tabloları oluştur
            db.session.execute(db.text(create_lawyer_table))
            print("'lawyer' tablosu olusturuldu")

            db.session.execute(db.text(create_party_lawyer_table))
            print("'party_lawyer' tablosu olusturuldu")

            # İndexleri oluştur
            for index_sql in create_indexes.strip().split(';'):
                if index_sql.strip():
                    db.session.execute(db.text(index_sql))

            print("Indexler olusturuldu")

            db.session.commit()
            print("\nTum tablolar basariyla olusturuldu!")

        except Exception as e:
            db.session.rollback()
            print(f"Hata olustu: {str(e)}")
            raise

if __name__ == '__main__':
    create_tables()
