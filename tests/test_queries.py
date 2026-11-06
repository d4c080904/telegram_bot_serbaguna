import datetime
from database.queries import (
    cek_duplikat_foto, tambah_food_log,
    save_wizard_state, get_wizard_state, delete_wizard_state
)

def test_cek_duplikat_foto_kosong(test_db):
    """Test kalau belum ada data, harusnya False"""
    user_id = "123"
    photo_hash = "abc123hash"
    assert cek_duplikat_foto(user_id, photo_hash) is False

def test_cek_duplikat_foto_ada(test_db):
    """Test kalau data udah ada, harusnya True"""
    user_id = "123"
    photo_hash = "abc123hash"
    
    tambah_food_log(
        user_id=user_id, message_id=1, photo_message_id=1, 
        photo_hash=photo_hash, nama="Nasi Goreng", porsi="1 piring", 
        kalori=500, protein=10, karbo=50, lemak=20, gula=5
    )
    
    assert cek_duplikat_foto(user_id, photo_hash) is True

def test_cek_duplikat_foto_beda_user(test_db):
    """Test kalau hash sama tapi beda user, harusnya False"""
    photo_hash = "abc123hash"
    tambah_food_log(
        user_id="user_A", message_id=1, photo_message_id=1, 
        photo_hash=photo_hash, nama="Nasi Goreng", porsi="1 piring", 
        kalori=500, protein=10, karbo=50, lemak=20, gula=5
    )
    assert cek_duplikat_foto("user_B", photo_hash) is False

def test_tambah_food_log_duplikat_dicegah_db(test_db):
    """Test mastiin DB nolak insert duplikat (Race Condition protection)"""
    user_id = "123"
    photo_hash = "hash_sama"
    
    # Insert pertama (Harus sukses)
    sukses_1 = tambah_food_log(
        user_id=user_id, message_id=1, photo_message_id=1, 
        photo_hash=photo_hash, nama="Nasi Goreng", porsi="1 piring", 
        kalori=500, protein=10, karbo=50, lemak=20, gula=5
    )
    assert sukses_1 is True

    # Insert kedua dengan hash sama (Harus GAGAL / False)
    sukses_2 = tambah_food_log(
        user_id=user_id, message_id=2, photo_message_id=2, 
        photo_hash=photo_hash, nama="Nasi Goreng Double", porsi="2 piring", 
        kalori=1000, protein=20, karbo=100, lemak=40, gula=10
    )
    assert sukses_2 is False # Karena ditolak database

def test_wizard_state_anti_tabrakan(test_db):
    """Test mastiin user bisa punya lebih dari 1 state di saat bersamaan"""
    user_id = "user_123"
    
    # Simpan state onboarding
    save_wizard_state(user_id, "onboarding", "step_1", {"nama": "Budi"})
    # Simpan state waiting_food_photo
    save_wizard_state(user_id, "waiting_food_photo", "waiting", {})
    
    # Keduanya harus tetep ada, gak saling timpa
    assert get_wizard_state(user_id, "onboarding") is not None
    assert get_wizard_state(user_id, "waiting_food_photo") is not None
    
    # Cek isi data onboarding masih utuh
    onboarding_data = get_wizard_state(user_id, "onboarding")
    assert onboarding_data['data']['nama'] == "Budi"