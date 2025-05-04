import os
import sqlite3
import tempfile
import shutil
from Invisimark import (
    create_db, add_user, get_user_by_email, generate_watermark_text,
    generate_image_hash, add_watermark, store_image_metadata, scan_image_for_watermark
)
from PIL import Image

# ---------- Setup Fixtures ----------

def setup_module(module):
    create_db()

def teardown_module(module):
    if os.path.exists('watermark_db.db'):
        os.remove('watermark_db.db')

# ---------- Tests ----------

def test_add_user_and_lookup():
    add_user("Alice", "alice@example.com", "1234567890")
    user_id = get_user_by_email("alice@example.com")
    assert isinstance(user_id, int)

def test_lookup_nonexistent_user():
    assert get_user_by_email("notfound@example.com") is None

def test_generate_watermark_text():
    text = generate_watermark_text("Alice", "alice@example.com")
    assert "Alice" in text and "alice@example.com" in text and len(text) > 10

def test_generate_image_hash():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new('RGB', (10, 10), color='red')
        img.save(tmp.name)
        img_hash = generate_image_hash(tmp.name)
    os.remove(tmp.name)
    assert len(img_hash) == 64  # SHA-256 hash

def test_add_watermark_and_metadata():
    user_email = "bob@example.com"
    add_user("Bob", user_email, "123")
    user_id = get_user_by_email(user_email)

    tmp_dir = tempfile.mkdtemp()
    image_path = os.path.join(tmp_dir, "test.png")
    Image.new('RGB', (20, 20), color='blue').save(image_path)

    wm_text = generate_watermark_text("Bob", user_email)
    wm_path, img_hash, modified_pixels = add_watermark(image_path, wm_text, "LeakTest")
    
    store_image_metadata(user_id, wm_path, wm_text, img_hash, modified_pixels, "LeakTest")
    assert os.path.exists(wm_path)
    shutil.rmtree(tmp_dir)

def test_scan_image_detects_user():
    user_email = "carol@example.com"
    add_user("Carol", user_email, "321")
    user_id = get_user_by_email(user_email)

    tmp_dir = tempfile.mkdtemp()
    image_path = os.path.join(tmp_dir, "test2.png")
    Image.new('RGB', (30, 30), color='green').save(image_path)

    wm_text = generate_watermark_text("Carol", user_email)
    wm_path, img_hash, modified_pixels = add_watermark(image_path, wm_text, "LeakCarol")
    store_image_metadata(user_id, wm_path, wm_text, img_hash, modified_pixels, "LeakCarol")

    detected = scan_image_for_watermark(wm_path)
    assert detected == "LeakCarol"
    shutil.rmtree(tmp_dir)

def test_invalid_image_scan():
    tmp_path = "nonexistent_file.png"
    try:
        result = scan_image_for_watermark(tmp_path)
    except FileNotFoundError:
        result = None
    assert result is None or result == "No watermark found."

def test_image_hash_uniqueness():
    img1 = Image.new('RGB', (10, 10), color='white')
    img2 = Image.new('RGB', (10, 10), color='black')

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp1, \
         tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp2:
        img1.save(tmp1.name)
        img2.save(tmp2.name)
        hash1 = generate_image_hash(tmp1.name)
        hash2 = generate_image_hash(tmp2.name)

    os.remove(tmp1.name)
    os.remove(tmp2.name)
    assert hash1 != hash2

def test_pixel_modifications_non_empty():
    tmp_dir = tempfile.mkdtemp()
    image_path = os.path.join(tmp_dir, "test3.png")
    Image.new('RGB', (40, 40), color='gray').save(image_path)

    wm_text = "Test_Watermark"
    _, _, modified_pixels = add_watermark(image_path, wm_text, "PixelTest")
    assert len(modified_pixels) == 10
    shutil.rmtree(tmp_dir)

def test_metadata_storage_integrity():
    add_user("Dave", "dave@example.com", "111")
    user_id = get_user_by_email("dave@example.com")

    tmp_dir = tempfile.mkdtemp()
    image_path = os.path.join(tmp_dir, "test4.png")
    Image.new('RGB', (20, 20), color='purple').save(image_path)

    wm_text = generate_watermark_text("Dave", "dave@example.com")
    wm_path, image_hash, modified_pixels = add_watermark(image_path, wm_text, "TestDave")
    store_image_metadata(user_id, wm_path, wm_text, image_hash, modified_pixels, "TestDave")

    conn = sqlite3.connect('watermark_db.db')
    cursor = conn.cursor()
    cursor.execute("SELECT watermark_metadata FROM images WHERE image_hash = ?", (image_hash,))
    result = cursor.fetchone()
    conn.close()

    assert result and "TestDave" in result[0]
    shutil.rmtree(tmp_dir)
