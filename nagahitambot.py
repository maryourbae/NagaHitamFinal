import os
import time
import extract_msg
import vobject
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram.ext import Updater, ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, PicklePersistence, CallbackContext, ContextTypes
import logging
import json
from datetime import datetime

# Konfigurasi logging untuk file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_activity.log', encoding='utf-8'),  # Log ke file
        logging.StreamHandler()  # Log ke console
    ]
)
logger = logging.getLogger(__name__)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# Definisikan state untuk conversation
CHOOSING = 0

ALLOWED_USERS_FILE = 'allowed_users.json'

# Load allowed users from JSON file
def load_allowed_users():
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, 'r') as f:
            return json.load(f)
    return []

# Save allowed users to JSON file
def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump(ALLOWED_USERS, f)

# Initialize allowed users
ALLOWED_USERS = load_allowed_users()
ADMIN_IDS = [6700632643, 7286714726]  # List ID admin yang diizinkan

# Fungsi untuk mencatat aktivitas
def log_activity(user_id, username, action, details=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] User ID: {user_id} (@{username}) - Action: {action}"
    if details:
        log_message += f" - Details: {details}"
    logger.info(log_message)

def convert_msg_to_txt(file_path):
    try:
        msg = extract_msg.Message(file_path)
        txt_file_path = file_path.replace('.msg', '.txt')
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Subject: {msg.subject}\n")
            f.write(f"From: {msg.sender}\n")
            f.write(f"To: {msg.to}\n")
            f.write(f"Date: {msg.date}\n")
            f.write("\nBody:\n")
            f.write(msg.body)
        return txt_file_path
    except Exception as e:
        print(f"Error dalam konversi MSG ke TXT: {str(e)}")
        return None

def convert_txt_to_vcf(file_path, vcf_filename, contact_name, partition_size=None):
    """Fungsi untuk mengkonversi file TXT ke VCF dengan batas partisi yang ditentukan (default tidak terbatas)"""
    try:
        logger.info(f"Converting TXT to VCF: {file_path} -> {vcf_filename}")
        # Baca nomor dari file TXT
        with open(file_path, 'r', encoding='utf-8') as f:
            numbers = [line.strip() for line in f if line.strip()]
        
        # Buat file VCF
        vcf_files = []  # List untuk menyimpan path file VCF yang dibuat
        os.makedirs('downloads', exist_ok=True)
        
        # Jika partition_size tidak ditentukan, gunakan panjang daftar numbers
        if partition_size is None or partition_size > len(numbers):
            partition_size = len(numbers)
        
        for i in range(0, len(numbers), partition_size):  # Bagi nomor menjadi kelompok sesuai partition_size
            vcf_file_path = f"downloads/{vcf_filename}_{i//partition_size + 1}.vcf"  # Nama file VCF
            with open(vcf_file_path, 'w', encoding='utf-8') as f:
                for j in range(i, min(i + partition_size, len(numbers))):  # Ambil sesuai partition_size
                    f.write("BEGIN:VCARD\n")
                    f.write("VERSION:3.0\n")
                    f.write(f"FN:{contact_name} {j + 1}\n")  # Tambahkan nomor urut
                    f.write(f"TEL;TYPE=CELL:{numbers[j]}\n")
                    f.write("END:VCARD\n")
            vcf_files.append(vcf_file_path)  # Simpan path file VCF yang dibuat
        
        return vcf_files  # Kembalikan list file VCF yang dibuat
    except Exception as e:
        logger.error(f"Error dalam mengkonversi TXT ke VCF: {str(e)}")
        return None

def convert_msg_to_vcf(file_path, adm_number, navy_number):
    try:
        logger.info(f"Converting MSG to VCF: {file_path}")
        msg = extract_msg.Message(file_path)
        vcf_file_path = file_path.replace('.msg', '.vcf')
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Format ADM
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{msg.sender}\n")
            f.write(f"TEL:{adm_number}\n")  # Nomor ADM tanpa TYPE
            f.write(f"NOTE:SUBJEK: {msg.subject}\n")
            f.write(f"NOTE:TANGGAL: {msg.date}\n")
            f.write(f"NOTE:ISI:\n{msg.body}\n")
            f.write("END:VCARD\n")
            
            # Format NAVY
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{msg.sender}\n")
            f.write(f"TEL:{navy_number}\n")  # Nomor NAVY tanpa TYPE
            f.write(f"NOTE:SUBJEK: {msg.subject}\n")
            f.write(f"NOTE:TANGGAL: {msg.date}\n")
            f.write(f"NOTE:ISI:\n{msg.body}\n")
            f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        print(f"Error dalam konversi MSG ke VCF: {str(e)}")
        return None

def convert_msg_to_adm_navy(file_path, adm_number, navy_number):
    try:
        msg = extract_msg.Message(file_path)
        adm_file_path = file_path.replace('.msg', '_ADM.txt')
        navy_file_path = file_path.replace('.msg', '_NAVY.txt')
        with open(adm_file_path, 'w', encoding='utf-8') as f:
            f.write("=== FORMAT ADM ===\n")
            f.write(f"DARI: {msg.sender}\n")
            f.write(f"UNTUK: {adm_number}\n")  # Menggunakan nomor ADM yang diterima
            f.write(f"TANGGAL: {msg.date}\n")
            f.write(f"SUBJEK: {msg.subject}\n")
            f.write("\nISI:\n")
            f.write(msg.body)
        with open(navy_file_path, 'w', encoding='utf-8') as f:
            f.write("=== FORMAT NAVY ===\n")
            f.write(f"FROM: {msg.sender}\n")
            f.write(f"TO: {navy_number}\n")  # Menggunakan nomor NAVY yang diterima
            f.write(f"DATE: {msg.date}\n")
            f.write(f"SUBJECT: {msg.subject}\n")
            f.write("\nCONTENT:\n")
            f.write(msg.body)
        return (adm_file_path, navy_file_path)
    except Exception as e:
        print(f"Error dalam konversi MSG ke ADM/NAVY: {str(e)}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fungsi untuk memulai percakapan dan menampilkan menu awal."""
    user = update.effective_user
    log_activity(user.id, user.username, "Started bot")
    reply_markup = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Start 🔄")],
            [KeyboardButton("1️⃣ MSG ke TXT 📝"), KeyboardButton("2️⃣ TXT ke VCF 📱")],
            [KeyboardButton("3️⃣ MSG ke ADM & NAVY 📋"), KeyboardButton("4️⃣ MSG ke VCF 📱")],
            [KeyboardButton("Developer 👨‍💻")]
        ],
        resize_keyboard=True
    )
    
    # Dapatkan username dan escape karakter khusus
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    # Escape karakter khusus dalam username
    username = username.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]').replace('(', r'\(').replace(')', r'\)').replace('~', r'\~').replace('`', r'\`').replace('>', r'\>').replace('#', r'\#').replace('+', r'\+').replace('-', r'\-').replace('=', r'\=').replace('|', r'\|').replace('{', r'\{').replace('}', r'\}').replace('.', r'\.').replace('!', r'\!')

    # Welcome message dengan username yang sudah di-escape
    welcome_message = (
        f"*🤖 Halo {username}\\!*\n"
        "*Selamat datang di NagaHitam Bot\\!*\n"
        "Silakan pilih menu yang tersedia 🚀:\n\n"
        "*1️⃣ Konversi MSG ke TXT*\n"
        "*2️⃣ Konversi TXT ke VCF*\n"
        "*3️⃣ Konversi MSG ke ADM & NAVY*\n"
        "*4️⃣ Konversi MSG ke VCF*"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='MarkdownV2')
    return CHOOSING

async def handle_text(update: Update, context: CallbackContext):
    """Fungsi untuk menangani input teks dari keyboard button"""
    user = update.effective_user
    text = update.message.text
    log_activity(user.id, user.username, "Text command", text)
    
    if text in ["Start 🔄", "Cancel"]:
        context.user_data.clear()
        return await start(update, context)
    elif text == "Developer 👨‍💻":
        dev_message = (
            "*👨‍💻 Developer Information\\:*\n\n"
            "*Name\\:* Naga Hitam\n"
            "*GitHub\\:* github\\.com/maryourbae\n"
            "*Telegram\\:* @toyng"
        )
        await update.message.reply_text(dev_message, parse_mode='MarkdownV2')
        return CHOOSING
    
    # Inisialisasi jika belum ada
    if 'contact_name' not in context.user_data:
        context.user_data['contact_name'] = None
    if 'waiting_for_message_vcf' not in context.user_data:
        context.user_data['waiting_for_message_vcf'] = False
    if 'adm_numbers' not in context.user_data:
        context.user_data['adm_numbers'] = []
    if 'navy_numbers' not in context.user_data:
        context.user_data['navy_numbers'] = []

    # Menangani pilihan menu 1
    if text == "1️⃣ MSG ke TXT 📝":
        context.user_data['waiting_for_number'] = True
        await update.message.reply_text(
            "Silakan masukkan nomor yang ingin disimpan.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Cancel")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_number'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)
            
        context.user_data['number'] = text
        context.user_data['waiting_for_number'] = False
        context.user_data['waiting_for_filename'] = True
        await update.message.reply_text("Silakan masukkan nama file (tanpa ekstensi):")
        return CHOOSING
    
    elif context.user_data.get('waiting_for_filename'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)
            
        context.user_data['filename'] = text
        # Langsung proses dan kirim file
        try:
            number = context.user_data['number']
            filename = f"downloads/{text}.txt"
            
            # Pastikan direktori downloads ada
            os.makedirs('downloads', exist_ok=True)
            
            # Tulis nomor ke file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{number}\n")
            
            # Kirim file ke user
            with open(filename, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=f"{text}.txt"
                )
            
            await update.message.reply_text("File TXT Berhasil dibuat! ✅")
            
            # Bersihkan file
            if os.path.exists(filename):
                os.remove(filename)
            
            # Reset state dan kembali ke menu utama
            context.user_data.clear()
            return await start(update, context)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
            context.user_data.clear()
            return await start(update, context)
    elif text == "2️⃣ TXT ke VCF 📱":
        context.user_data['waiting_for_vcf_filename'] = True
        await update.message.reply_text(
            "Silakan masukkan nama untuk file VCF.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Cancel")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_vcf_filename'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)
            
        context.user_data['vcf_filename'] = text
        context.user_data['waiting_for_vcf_filename'] = False
        context.user_data['waiting_for_partition_size'] = True
        await update.message.reply_text(
            "Silakan masukkan ukuran partisi (masukkan angka untuk membatasi, atau tekan 'Enter' untuk tidak membatasi):",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Enter")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_partition_size'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)
        
        partition_size = int(text) if text.isdigit() else None  # Gunakan None jika input tidak valid
        context.user_data['partition_size'] = partition_size
        context.user_data['waiting_for_partition_size'] = False
        context.user_data['waiting_for_contact_name'] = True
        await update.message.reply_text("Silakan masukkan nama kontak:")
        return CHOOSING
    
    elif context.user_data.get('waiting_for_contact_name'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)
            
        context.user_data['contact_name'] = text
        context.user_data['waiting_for_contact_name'] = False
        context.user_data['waiting_for_txt_file'] = True
        await update.message.reply_text("Silakan kirim file TXT yang ingin dikonversi.")
        return CHOOSING
    
    elif text == "3️⃣ MSG ke ADM & NAVY 📋":
        context.user_data['waiting_for_adm_number'] = True
        await update.message.reply_text(
            "Masukkan nomor Admin:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Cancel")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_adm_number'):
        if text.lower() == 'cancel':
            await update.message.reply_text("❌ Proses dibatalkan. Kembali ke menu utama.")
            context.user_data['waiting_for_adm_number'] = False
            return await start(update, context)
        
        # Pisahkan input berdasarkan baris baru dan tambahkan ke daftar
        numbers = text.strip().split('\n')
        for number in numbers:
            if number.strip():
                context.user_data['adm_numbers'].append(number.strip())
        
        # Langsung lanjut ke input Navy
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = True
        await update.message.reply_text("Masukkan nomor Navy:")
        return CHOOSING
    
    elif context.user_data.get('waiting_for_navy_number'):
        if text.lower() == 'cancel':
            await update.message.reply_text("❌ Proses dibatalkan. Kembali ke menu utama.")
            context.user_data['waiting_for_navy_number'] = False
            return await start(update, context)
        
        # Pisahkan input berdasarkan baris baru dan tambahkan ke daftar
        numbers = text.strip().split('\n')
        for number in numbers:
            if number.strip():
                context.user_data['navy_numbers'].append(number.strip())
        
        # Langsung proses pembuatan VCF
        adm_numbers = context.user_data['adm_numbers']
        navy_numbers = context.user_data['navy_numbers']
        
        # Buat file VCF dengan nomor yang diberikan
        vcf_file_path = create_vcf_from_multiple_numbers(adm_numbers, navy_numbers)
        
        if vcf_file_path:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(vcf_file_path, 'rb'),
                filename="AdminNavy.vcf"
            )
            await update.message.reply_text("File Admin & Navy berhasil dibuat! ✅")
        else:
            await update.message.reply_text('Terjadi kesalahan: File VCF tidak dapat dibuat.')
        
        # Reset state
        context.user_data['adm_numbers'] = []
        context.user_data['navy_numbers'] = []
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = False
        
        # Kembali ke menu utama
        return await start(update, context)
    elif text == "4️⃣ MSG ke VCF 📱":
        context.user_data['waiting_for_message_vcf'] = True
        context.user_data['contact_name'] = None
        context.user_data['contact_numbers'] = []  # Reset daftar nomor
        context.user_data['waiting_for_numbers'] = False
        await update.message.reply_text(
            "Silakan masukkan nama kontak untuk VCF."
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_message_vcf'):
        if text.lower() == 'cancel':
            # Reset semua state
            context.user_data['waiting_for_message_vcf'] = False
            context.user_data['contact_name'] = None
            context.user_data['contact_numbers'] = []
            context.user_data['waiting_for_numbers'] = False
            await update.message.reply_text("❌ Proses dibatalkan. Kembali ke menu utama.")
            return await start(update, context)
            
        if context.user_data['contact_name'] is None:
            # Simpan nama kontak
            context.user_data['contact_name'] = text
            context.user_data['waiting_for_numbers'] = True
            await update.message.reply_text(
                f"Nama kontak '{text}' telah disimpan.\n"
                "Silakan kirim nomor kontak (bisa lebih dari satu, pisahkan dengan baris baru)."
            )
            return CHOOSING
        
        elif context.user_data.get('waiting_for_numbers'):
            # Proses nomor kontak dan langsung buat VCF
            numbers = text.strip().split('\n')
            contact_numbers = [num.strip() for num in numbers if num.strip()]
            contact_name = context.user_data['contact_name']
            
            # Buat file VCF (tanpa pesan)
            vcf_file_path = create_vcf_from_contacts([{'name': contact_name, 'number': num} for num in contact_numbers])
            
            if vcf_file_path:
                try:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(vcf_file_path, 'rb'),
                        filename=f"{contact_name}.vcf"
                    )
                    await update.message.reply_text("File VCF berhasil dibuat! ✅")
                except Exception as e:
                    await update.message.reply_text(f"❌ Terjadi kesalahan saat mengirim file: {str(e)}")
            else:
                await update.message.reply_text("❌ Terjadi kesalahan dalam membuat file VCF.")
            
            # Reset semua state
            context.user_data['waiting_for_message_vcf'] = False
            context.user_data['contact_name'] = None
            context.user_data['contact_numbers'] = []
            context.user_data['waiting_for_numbers'] = False
            
            # Kembali ke menu utama
            return await start(update, context)

    # Jika tidak ada kondisi yang terpenuhi
    await update.message.reply_text(
        "Silakan pilih menu yang tersedia atau kirim file untuk dikonversi."
    )
    
    return CHOOSING

async def button(update: Update, context: CallbackContext):
    """Fungsi untuk menangani klik tombol inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'selesai':
        # Jika pengguna mengklik tombol 'Selesai', proses pembuatan VCF
        adm_numbers = context.user_data['adm_numbers']
        navy_numbers = context.user_data['navy_numbers']
        
        # Buat file VCF dengan nomor yang diberikan
        vcf_file_path = create_vcf_from_numbers(adm_numbers, navy_numbers)
        
        if vcf_file_path:
            await context.bot.send_document(chat_id=query.message.chat.id, document=open(vcf_file_path, 'rb'), filename="contacts.vcf")
        else:
            await query.message.reply_text('Terjadi kesalahan: File VCF tidak dapat dibuat.')
        
        # Reset state
        context.user_data['adm_numbers'] = []
        context.user_data['navy_numbers'] = []
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = False

    # Tambahkan logika lain untuk tombol lainnya jika diperlukan

async def save_message_to_txt(update: Update, context: CallbackContext):
    """Fungsi untuk menyimpan pesan ke file TXT"""
    try:
        number = context.user_data['number']
        filename = f"downloads/{context.user_data['filename']}.txt"
        
        # Pastikan direktori downloads ada
        os.makedirs('downloads', exist_ok=True)
        
        # Tulis nomor ke file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{number}\n")
        
        # Kirim file ke user menggunakan path file
        with open(filename, 'rb') as file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file,
                filename=f"{context.user_data['filename']}.txt"
            )
        
        # Reset state
        context.user_data['waiting_for_message'] = False
        
        # Hapus file setelah dikirim
        cleanup_files(filename)
        
        await update.message.reply_text("File TXT Berhasil dibuat! ✅")
    
    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan: {str(e)}")
        context.user_data['waiting_for_message'] = False

async def message_handler(update: Update, context: CallbackContext):
    """Handler untuk semua pesan teks"""
    if context.user_data.get('waiting_for_message'):
        await save_message_to_txt(update, context)
    else:
        await handle_text(update, context)

async def handle_file(update: Update, context: CallbackContext):
    """Fungsi untuk menangani file yang dikirim user"""
    try:
        user = update.effective_user
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name
        log_activity(user.id, user.username, "File upload", file_name)
        
        # Download file
        downloaded_file = f"downloads/{file_name}"
        os.makedirs('downloads', exist_ok=True)
        await file.download_to_drive(downloaded_file)
        
        if context.user_data.get('waiting_for_txt_file'):
            # Konversi TXT ke VCF
            vcf_filename = context.user_data.get('vcf_filename', 'contacts')
            contact_name = context.user_data.get('contact_name', 'Contact')
            vcf_files = convert_txt_to_vcf(downloaded_file, vcf_filename, contact_name, context.user_data.get('partition_size'))
            
            if vcf_files:
                for vcf_file in vcf_files:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(vcf_file, 'rb'),
                        filename=os.path.basename(vcf_file)
                    )
                await update.message.reply_text("Semua file VCF berhasil dibuat ✅!")
            else:
                await update.message.reply_text("❌ Terjadi kesalahan dalam membuat file VCF.")
            
            # Reset state
            context.user_data.clear()
            return await start(update, context)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
        context.user_data.clear()
        return await start(update, context)

def cleanup_files(*files):
    """Fungsi untuk membersihkan file temporary"""
    for file_path in files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error dalam membersihkan file {file_path}: {str(e)}")

def create_vcf_from_numbers(adm_numbers, navy_numbers):
    try:
        vcf_file_path = "downloads/Admin & Navy.vcf"  # Tentukan nama file VCF
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Tulis semua nomor dalam satu file VCF
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write("FN:Admin\n")
            for adm_number in adm_numbers:
                f.write(f"TEL;TYPE=CELL:{adm_number}\n")
            f.write("END:VCARD\n")
            
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write("FN:Navy\n")
            for navy_number in navy_numbers:
                f.write(f"TEL;TYPE=CELL:{navy_number}\n")
            f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        print(f"Error dalam membuat VCF: {str(e)}")
        return None

def create_vcf_from_message(contact_name, message_text, contact_numbers, vcf_filename=None):
    """Fungsi untuk membuat file VCF dari pesan dan daftar nomor kontak"""
    try:
        # Gunakan nama file yang diberikan atau nama kontak jika tidak ada
        filename = vcf_filename if vcf_filename else contact_name
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        vcf_file_path = f"downloads/{safe_filename}.vcf"
        
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            for number in contact_numbers:
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{contact_name}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")  # Menyimpan nomor kontak
                f.write("NOTE:\n")
                
                # Memecah pesan menjadi baris-baris untuk menghindari baris yang terlalu panjang
                message_lines = message_text.split('\n')
                for line in message_lines:
                    escaped_line = line.replace(',', '\\,').replace(';', '\\;')
                    f.write(escaped_line + '\\n')
                
                f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        print(f"Error dalam membuat VCF dari pesan: {str(e)}")
        return None

def create_vcf_from_multiple_numbers(adm_numbers, navy_numbers):
    """Fungsi untuk membuat VCF dari nomor Admin dan Navy"""
    try:
        logger.info(f"Creating VCF from multiple numbers - ADM: {len(adm_numbers)}, NAVY: {len(navy_numbers)}")
        vcf_file_path = "downloads/AdminNavy.vcf"
        os.makedirs('downloads', exist_ok=True)
        
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Tulis nomor Admin
            for i, number in enumerate(adm_numbers, 1):
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:Admin {i}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write("END:VCARD\n")
            
            # Tulis nomor Navy
            for i, number in enumerate(navy_numbers, 1):
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:Navy {i}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        logger.error(f"Error dalam membuat VCF: {str(e)}")
        return None

def create_vcf_from_contacts(contacts):
    """Fungsi untuk membuat VCF dari daftar kontak"""
    try:
        vcf_file_path = "downloads/contacts.vcf"
        os.makedirs('downloads', exist_ok=True)
        
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            for contact in contacts:
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{contact['name']}\n")
                f.write(f"TEL;TYPE=CELL:{contact['number']}\n")
                f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        logger.error(f"Error dalam membuat VCF: {str(e)}")
        return None

async def convert_and_send_vcf(update: Update, context: CallbackContext, file_path, adm_number, navy_number):
    try:
        vcf_file_path = convert_msg_to_vcf(file_path, adm_number, navy_number)
        
        if vcf_file_path:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(vcf_file_path, 'rb'),
                filename=os.path.basename(vcf_file_path)
            )
            await update.message.reply_text("File VCF Admin dan Navy telah berhasil dibuat! ✅")
            await update.message.reply_text("Silakan periksa file yang telah dikirim dan gunakan untuk menyimpan kontak.")
        else:
            await update.message.reply_text('❌ Terjadi kesalahan: File VCF tidak dapat dibuat.')
        
        # Reset state setelah mengirim file
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = False

    except Exception as e:
        logger.error(f"Error saat mengonversi dan mengirim VCF: {str(e)}")
        await update.message.reply_text(f'❌ Terjadi kesalahan: {str(e)}')

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return
    
    if context.args:
        try:
            new_user_id = int(context.args[0])
            with open('allowed_users.json', 'r') as f:
                data = json.load(f)
            
            # Cek apakah user sudah ada
            if not any(user['id'] == new_user_id for user in data['users']):
                # Tambah user baru
                new_user = {
                    "id": new_user_id,
                    "role": "user",
                    "added_date": datetime.now().strftime("%Y-%m-%d")
                }
                data['users'].append(new_user)
                
                # Simpan ke file
                with open('allowed_users.json', 'w') as f:
                    json.dump(data, f, indent=4)
                
                await update.message.reply_text(f"✅ Pengguna dengan ID {new_user_id} telah ditambahkan.")
                log_activity(user_id, update.message.from_user.username, "Add user", f"Added user ID: {new_user_id}")
            else:
                await update.message.reply_text(f"❌ Pengguna dengan ID {new_user_id} sudah ada dalam daftar.")
        except ValueError:
            await update.message.reply_text("❌ ID pengguna harus berupa angka.")
        except Exception as e:
            await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
    else:
        await update.message.reply_text("ℹ️ Silakan masukkan ID pengguna yang ingin ditambahkan.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return
    
    if context.args:
        try:
            user_to_remove = int(context.args[0])
            with open('allowed_users.json', 'r') as f:
                data = json.load(f)
            
            # Cari dan hapus user
            user_list = data['users']
            for i, user in enumerate(user_list):
                if user['id'] == user_to_remove:
                    if user['role'] == 'admin':
                        await update.message.reply_text("❌ Tidak dapat menghapus user admin.")
                        return
                    del user_list[i]
                    
                    # Simpan perubahan
                    with open('allowed_users.json', 'w') as f:
                        json.dump(data, f, indent=4)
                    
                    await update.message.reply_text(f"✅ Pengguna dengan ID {user_to_remove} telah dihapus.")
                    log_activity(user_id, update.message.from_user.username, "Remove user", f"Removed user ID: {user_to_remove}")
                    return
            
            await update.message.reply_text(f"❌ Pengguna dengan ID {user_to_remove} tidak ditemukan.")
        except ValueError:
            await update.message.reply_text("❌ ID pengguna harus berupa angka.")
        except Exception as e:
            await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
    else:
        await update.message.reply_text("ℹ️ Silakan masukkan ID pengguna yang ingin dihapus.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return
    
    try:
        with open('allowed_users.json', 'r') as f:
            data = json.load(f)
        
        if not data['users']:
            await update.message.reply_text("ℹ️ Tidak ada pengguna terdaftar.")
            return
        
        user_list = "📋 Daftar Pengguna:\n\n"
        for user in data['users']:
            user_list += f"ID: {user['id']}\n"
            user_list += f"Role: {user['role']}\n"
            user_list += f"Ditambahkan: {user['added_date']}\n"
            user_list += "-------------------\n"
        
        await update.message.reply_text(user_list)
        log_activity(update.effective_user.id, update.effective_user.username, "List users")
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")

async def view_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Anda tidak memiliki akses untuk melihat log.")
        return
    
    try:
        with open('bot_activity.log', 'r', encoding='utf-8') as f:
            last_logs = f.readlines()[-50:]  # 50 baris terakhir
        log_text = ''.join(last_logs)
        await update.message.reply_text(f"50 aktivitas terakhir:\n\n{log_text}")
    except Exception as e:
        await update.message.reply_text(f"Error membaca log: {str(e)}")

def main():
    application = ApplicationBuilder().token("Token").build()
    
    # Buat conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex('^(Start 🔄|Cancel)$'), start)
        ],
        states={
            CHOOSING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text),
                MessageHandler(filters.Document.ALL, handle_file),
            ]
        },
        fallbacks=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex('^(Start 🔄|Cancel)$'), start)
        ],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('adduser', add_user))
    application.add_handler(CommandHandler('removeuser', remove_user))
    application.add_handler(CommandHandler('listusers', list_users))
    application.add_handler(CommandHandler('viewlogs', view_logs))
    
    application.run_polling()

if __name__ == '__main__':
    main()