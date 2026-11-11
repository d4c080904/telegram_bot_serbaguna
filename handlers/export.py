import logging
import io
from datetime import datetime
from fpdf import FPDF
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from database.queries import get_all_data_for_export, get_user_profile

logger = logging.getLogger(__name__)
router = Router()

class LaporanPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(40, 167, 69) # Warna hijau GymMate
        self.cell(0, 10, 'GYMMATE FITNESS REPORT', border=False, align='C')
        self.ln(10)
        
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Dicetak pada: {datetime.now().strftime("%d %B %Y - %H:%M")}', border=False, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Halaman {self.page_no()}/{{nb}} - Dibuat oleh GymMate AI', align='C')

@router.callback_query(F.data == "menu_export")
async def callback_menu_export(callback: CallbackQuery):
    try:
        await callback.answer("⏳ Sedang meracik Laporan PDF...")
        user_id = str(callback.from_user.id)
        
        # 1. Ambil Data
        profil = await get_user_profile(user_id)
        nama_user = profil.get('nama', 'Bro') if profil else 'Bro'
        
        food_data, water_data, weight_data = await get_all_data_for_export(user_id)
        
        if not food_data and not water_data and not weight_data:
            await callback.message.answer("⚠️ Belum ada data yang bisa di-export. Coba catat makanan atau minum air dulu ya.")
            return

        # 2. Buat PDF
        pdf = LaporanPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"Halo {nama_user}, ini rangkuman progres lu:", ln=True)

        # --- BAGIAN MAKANAN ---
        if food_data:
            pdf.ln(5)
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_fill_color(230, 245, 230) # Background hijau muda
            pdf.cell(0, 8, " 1. LOG MAKANAN ", ln=True, fill=True)
            
            # Header Tabel
            pdf.set_font("Helvetica", 'B', 9)
            pdf.set_fill_color(200, 220, 200)
            pdf.cell(20, 7, "Tgl", 1, align='C', fill=True)
            pdf.cell(50, 7, "Makanan", 1, align='C', fill=True)
            pdf.cell(25, 7, "Porsi", 1, align='C', fill=True)
            pdf.cell(20, 7, "Kalori", 1, align='C', fill=True)
            pdf.cell(20, 7, "Protein", 1, align='C', fill=True)
            pdf.cell(20, 7, "Karbo", 1, align='C', fill=True)
            pdf.cell(20, 7, "Lemak", 1, align='C', fill=True)
            pdf.cell(15, 7, "Gula", 1, align='C', fill=True)
            pdf.ln()
            
            # Isi Tabel
            pdf.set_font("Helvetica", '', 8)
            for row in food_data:
                makanan = str(row['nama_makanan'])[:25] + "..." if len(str(row['nama_makanan'])) > 25 else str(row['nama_makanan'])
                pdf.cell(20, 6, str(row['tanggal']), 1)
                pdf.cell(50, 6, makanan, 1)
                pdf.cell(25, 6, str(row['estimasi_porsi']), 1)
                pdf.cell(20, 6, str(row['kalori']), 1, align='C')
                pdf.cell(20, 6, f"{row['protein']}g", 1, align='C')
                pdf.cell(20, 6, f"{row['karbo']}g", 1, align='C')
                pdf.cell(20, 6, f"{row['lemak']}g", 1, align='C')
                pdf.cell(15, 6, f"{row['gula']}g", 1, align='C')
                pdf.ln()

        # --- BAGIAN AIR ---
        if water_data:
            pdf.ln(10)
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_fill_color(230, 240, 255) # Background biru muda
            pdf.cell(0, 8, " 2. LOG AIR MINUM ", ln=True, fill=True)
            
            pdf.set_font("Helvetica", 'B', 9)
            pdf.set_fill_color(200, 215, 240)
            pdf.cell(40, 7, "Tanggal", 1, align='C', fill=True)
            pdf.cell(40, 7, "Jumlah (ml)", 1, align='C', fill=True)
            pdf.ln()
            
            pdf.set_font("Helvetica", '', 9)
            for row in water_data:
                pdf.cell(40, 6, str(row['tanggal']), 1)
                pdf.cell(40, 6, str(row['ml']), 1, align='C')
                pdf.ln()

        # --- BAGIAN BERAT ---
        if weight_data:
            pdf.ln(10)
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_fill_color(255, 240, 230) # Background orange muda
            pdf.cell(0, 8, " 3. LOG BERAT BADAN ", ln=True, fill=True)
            
            pdf.set_font("Helvetica", 'B', 9)
            pdf.set_fill_color(240, 215, 200)
            pdf.cell(40, 7, "Tanggal", 1, align='C', fill=True)
            pdf.cell(40, 7, "Berat (kg)", 1, align='C', fill=True)
            pdf.ln()
            
            pdf.set_font("Helvetica", '', 9)
            for row in weight_data:
                pdf.cell(40, 6, str(row['tanggal']), 1)
                pdf.cell(40, 6, str(row['berat']), 1, align='C')
                pdf.ln()

        # 3. Simpan ke Memory & Kirim ke Telegram
        pdf_bytes = pdf.output(dest='S')
        if isinstance(pdf_bytes, bytearray):
            pdf_bytes = bytes(pdf_bytes)
        elif isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode('latin-1')
            
        document = BufferedInputFile(pdf_bytes, filename=f"Laporan_GymMate_{nama_user}.pdf")
        
        await callback.message.answer_document(
            document=document, 
            caption=f"📄 <b>Laporan Fitness {nama_user}</b>\n\nIni laporan lengkap lu bro. Bisa langsung di-print atau disimpen buat tracking progres. 🔥",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"[export pdf] error: {e}")
        await callback.message.answer("❌ Gagal membuat PDF. Coba lagi nanti.")