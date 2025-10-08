"""
Vekil verilerini eski JSON formatından yeni Lawyer ve PartyLawyer tablolarına taşır
"""
import sys
import os

# firstwebsite modülünü import edebilmek için path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'firstwebsite'))

from models import db, CaseFile, Lawyer, PartyLawyer
from app import app
import json

def capitalize_name(name):
    """İsimleri proper case'e çevir: YENER SEVEN -> Yener Seven"""
    if not name:
        return name

    # Türkçe karakterler için özel işlem
    turkish_upper = {'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'}
    turkish_lower = {'i': 'İ', 'ı': 'I', 'ş': 'Ş', 'ğ': 'Ğ', 'ü': 'Ü', 'ö': 'Ö', 'ç': 'Ç'}

    words = name.split()
    capitalized_words = []

    for word in words:
        if not word:
            continue

        # İlk harfi büyük yap
        first_char = word[0]
        if first_char in turkish_upper:
            first_char = turkish_upper[first_char].upper()
        elif first_char in turkish_lower:
            first_char = turkish_lower[first_char.lower()]
        else:
            first_char = first_char.upper()

        # Geri kalanı küçük yap
        rest = word[1:].lower()

        capitalized_words.append(first_char + rest)

    return ' '.join(capitalized_words)

def migrate_lawyers():
    """Eski vekil verilerini yeni tablolara taşı"""
    with app.app_context():
        print("Vekil migration basliyor...")

        # Tüm dosyaları al
        all_cases = CaseFile.query.all()
        migrated_count = 0
        error_count = 0

        for case in all_cases:
            try:
                lawyers_to_create = []

                # 1. Ana karşı taraf vekili (opponent_lawyer)
                if case.opponent_lawyer and case.opponent_lawyer.strip():
                    lawyer_name = capitalize_name(case.opponent_lawyer.strip())

                    lawyer = Lawyer(
                        name=lawyer_name,
                        bar=case.opponent_lawyer_bar,
                        bar_number=case.opponent_lawyer_bar_number,
                        phone=case.opponent_lawyer_phone,
                        address=case.opponent_lawyer_address,
                        case_id=case.id
                    )
                    db.session.add(lawyer)
                    db.session.flush()  # ID'yi al

                    # Ana karşı tarafa (opponent, index=0) bağla
                    party_assoc = PartyLawyer(
                        lawyer_id=lawyer.id,
                        party_type='opponent',
                        party_index=0
                    )
                    db.session.add(party_assoc)
                    lawyers_to_create.append(f"  Opponent Lawyer: {lawyer_name}")

                # 2. Ek vekiller (additional_lawyers_json)
                if case.additional_lawyers_json:
                    try:
                        additional_lawyers = json.loads(case.additional_lawyers_json)

                        for idx, lawyer_data in enumerate(additional_lawyers):
                            if isinstance(lawyer_data, dict):
                                lawyer_name = capitalize_name(lawyer_data.get('name', '').strip())

                                if lawyer_name:
                                    lawyer = Lawyer(
                                        name=lawyer_name,
                                        bar=lawyer_data.get('bar', ''),
                                        bar_number=lawyer_data.get('bar_number', ''),
                                        phone=lawyer_data.get('phone', ''),
                                        address=lawyer_data.get('address', ''),
                                        case_id=case.id
                                    )
                                    db.session.add(lawyer)
                                    db.session.flush()

                                    # Hangi tarafa ait olduğunu belirle (varsayılan: opponent)
                                    # Gelecekte bu bilgiyi JSON'dan alabilirsiniz
                                    party_type = lawyer_data.get('party_type', 'opponent')
                                    party_index = lawyer_data.get('party_index', 0)

                                    party_assoc = PartyLawyer(
                                        lawyer_id=lawyer.id,
                                        party_type=party_type,
                                        party_index=party_index
                                    )
                                    db.session.add(party_assoc)
                                    lawyers_to_create.append(f"  Additional Lawyer: {lawyer_name}")
                    except json.JSONDecodeError:
                        print(f"  Dosya {case.id}: JSON parse hatasi (additional_lawyers)")

                # 3. Ek karşı taraflar içindeki vekiller (additional_opponents_json)
                if case.additional_opponents_json:
                    try:
                        additional_opponents = json.loads(case.additional_opponents_json)

                        for idx, opponent_data in enumerate(additional_opponents):
                            if isinstance(opponent_data, dict):
                                lawyer_name_raw = opponent_data.get('lawyer', '').strip()

                                if lawyer_name_raw and lawyer_name_raw != '-':
                                    lawyer_name = capitalize_name(lawyer_name_raw)

                                    lawyer = Lawyer(
                                        name=lawyer_name,
                                        bar='',
                                        bar_number='',
                                        phone='',
                                        address='',
                                        case_id=case.id
                                    )
                                    db.session.add(lawyer)
                                    db.session.flush()

                                    # Ek karşı tarafa bağla (index = idx + 1, çünkü 0 ana taraf)
                                    party_assoc = PartyLawyer(
                                        lawyer_id=lawyer.id,
                                        party_type='opponent',
                                        party_index=idx + 1
                                    )
                                    db.session.add(party_assoc)
                                    lawyers_to_create.append(f"  Opponent #{idx+1} Lawyer: {lawyer_name}")
                    except json.JSONDecodeError:
                        print(f"  Dosya {case.id}: JSON parse hatasi (additional_opponents)")

                if lawyers_to_create:
                    db.session.commit()
                    print(f"Dosya {case.id} ({case.year}/{case.case_number}):")
                    for msg in lawyers_to_create:
                        print(msg)
                    migrated_count += 1

            except Exception as e:
                db.session.rollback()
                print(f"Dosya {case.id} migrate edilirken hata: {str(e)}")
                error_count += 1

        print(f"\nMigration tamamlandi!")
        print(f"Toplam {migrated_count} dosya basariyla migrate edildi")
        if error_count > 0:
            print(f"{error_count} dosyada hata olustu")

if __name__ == '__main__':
    migrate_lawyers()
