import os
import sqlite3
from PIL import Image
import random
import string
import hashlib

# SQLite database setup
def create_db():
    conn = sqlite3.connect('watermark_db.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        email TEXT,
                        phone TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        image_path TEXT,
                        watermark_metadata TEXT,
                        image_hash TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')

    conn.commit()
    conn.close()

# Add a user to the database
def add_user(name, email, phone):
    conn = sqlite3.connect('watermark_db.db')
    cursor = conn.cursor()

    cursor.execute('''INSERT INTO users (name, email, phone)
                      VALUES (?, ?, ?)''', (name, email, phone))

    conn.commit()
    conn.close()

# Get the user's ID by email
def get_user_by_email(email):
    conn = sqlite3.connect('watermark_db.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT id FROM users WHERE email = ?''', (email,))
    user = cursor.fetchone()

    conn.close()

    if user:
        return user[0]
    return None

# Generate a random watermark text (for storage and metadata)
def generate_watermark_text(name, email):
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    watermark_text = f"{name}_{email}_{rand_str}"
    return watermark_text

# Modify pixels slightly to embed invisible watermark
def add_watermark(image_path, watermark_text, connected_name):
    img = Image.open(image_path)
    width, height = img.size

    # Randomly select 10 pixels in the image to modify
    modified_pixels = []
    for _ in range(10):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)

        # Get the original pixel color
        r, g, b = img.getpixel((x, y))

        # Slightly modify the color of the pixel
        new_r = (r + random.randint(-5, 5)) % 256  # Modify in a small range
        new_g = (g + random.randint(-5, 5)) % 256
        new_b = (b + random.randint(-5, 5)) % 256

        # Save the modified pixel's position and the new color
        modified_pixels.append((x, y, (new_r, new_g, new_b)))

        # Update the pixel in the image
        img.putpixel((x, y), (new_r, new_g, new_b))

    # Save the new image with watermark in the 'filename_images' folder
    folder_name = os.path.splitext(os.path.basename(image_path))[0] + "_images"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Save each image with the name provided by the user
    watermarked_image_path = f"filename_images/{connected_name}_{random.randint(1000, 9999)}.png"
    img.save(watermarked_image_path)

    # Generate a hash for the image (for leak detection)
    image_hash = generate_image_hash(watermarked_image_path)

    return watermarked_image_path, image_hash, modified_pixels

# Store image metadata in the database
def store_image_metadata(user_id, image_path, watermark_text, image_hash, modified_pixels, connected_name):
    conn = sqlite3.connect('watermark_db.db')
    cursor = conn.cursor()

    # Store the positions and color changes in the metadata (as JSON or a string)
    watermark_metadata = {
        'watermark_text': watermark_text,
        'modified_pixels': modified_pixels,
        'connected_name': connected_name
    }

    cursor.execute('''INSERT INTO images (user_id, image_path, watermark_metadata, image_hash)
                      VALUES (?, ?, ?, ?)''', (user_id, image_path, str(watermark_metadata), image_hash))

    conn.commit()
    conn.close()

# Generate an image hash for leak detection
def generate_image_hash(image_path):
    with open(image_path, 'rb') as f:
        image_data = f.read()
        return hashlib.sha256(image_data).hexdigest()

# Scan an image to detect a watermark and identify the user
def scan_image_for_watermark(image_path):
    img = Image.open(image_path)
    width, height = img.size

    # Retrieve the watermark metadata from the database based on the image hash
    image_hash = generate_image_hash(image_path)
    conn = sqlite3.connect('watermark_db.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT user_id, watermark_metadata FROM images WHERE image_hash = ?''', (image_hash,))
    result = cursor.fetchone()

    conn.close()

    if result:
        user_id, watermark_metadata = result
        metadata = eval(watermark_metadata)  # Converting string representation back to a dictionary
        connected_name = metadata.get('connected_name')
        print(f"Watermark detected for user with ID {user_id}: Connected to {connected_name}")
        return connected_name
    else:
        print("No watermark found.")
        return None

# Main Menu Function
def display_menu():
    print("\n--- Watermarking System ---")
    print("1. Create a new user (Register)")
    print("2. Login to your account")
    print("3. Scan an image for watermarking")
    print("4. Exit")

    choice = input("Please choose an option (1/2/3/4): ")
    return choice

# Function to register a new user
def register_user():
    name = input("Enter your name: ")
    email = input("Enter your email: ")
    phone = input("Enter your phone number: ")

    # Add the user to the database
    add_user(name, email, phone)
    print(f"User {name} added successfully.")

# Function to login an existing user
def login_user():
    email = input("Enter your email: ")

    user_id = get_user_by_email(email)

    if user_id:
        print(f"User logged in successfully with ID {user_id}")
        return user_id
    else:
        print("User not found! Please register first.")
        return None

# Function to watermark an image
def watermark_image(user_id):
    # Ask for image path and number of watermarked copies to generate
    image_path = input("Enter the path to the image you want to watermark: ")
    num_images = int(input("How many watermarked images do you want to generate? "))

    for i in range(num_images):
        # Ask for the connected name for each image
        connected_name = input(f"Enter the connected name for image {i+1}: ")

        # Generate unique watermark text
        watermark_text = generate_watermark_text('Sample User', 'user@example.com')

        # Add watermark to the image
        watermarked_image_path, image_hash, modified_pixels = add_watermark(image_path, watermark_text, connected_name)

        # Store metadata in the database
        store_image_metadata(user_id, watermarked_image_path, watermark_text, image_hash, modified_pixels, connected_name)

        print(f"Watermarked image {i+1} saved as {watermarked_image_path}")
    print("Watermarking complete!")

# Main function that drives the application
def main():
    # Initialize database
    create_db()

    while True:
        # Display the menu and get user choice
        choice = display_menu()

        if choice == '1':
            # Register new user
            register_user()

        elif choice == '2':
            # Login existing user
            user_id = login_user()

            if user_id:
                watermark_image(user_id)

        elif choice == '3':
            # Scan an image for watermarking
            image_to_scan = input("Enter the path of the image to scan for leaks: ")
            scan_image_for_watermark(image_to_scan)

        elif choice == '4':
            print("Exiting the program.")
            break

        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()
