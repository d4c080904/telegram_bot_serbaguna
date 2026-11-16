import os
import datetime
from fpdf import FPDF
from database.queries import get_all_data_for_export, get_user_profile
import logging

logger = logging.getLogger(__name__)

class PDFLaporan(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Laporan GymMate', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Dicetak pada: {datetime.datetime.now().strftime("%d-%m-%Y %H:%M")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

async def buat_laporan_pdf(user_id: str) -> str:
    try:
        # 1. Ambil Data dari Database
        user = await get_user_profile(user_id)
        food_data, water_data, weight_data = await get_all_data_for_export(user_id)
        
        # 2. Setup PDF
        pdf = PDFLaporan()
        pdf.add_page()
        pdf.set_font('Arial', '', 11)

        # Info User
        nama = user['nama'] if user else 'User'
        berat = user['berat'] if user else '-'
        tinggi = user['tinggi'] if user else '-'
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'Profil: {nama}', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 8, f'Berat Badan: {berat} kg | Tinggi Badan: {tinggi} cm', 0, 1)
        pdf.ln(5)

        # --- TABEL MAKANAN ---
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, '1. Riwayat Makanan', 0, 1)
        pdf.set_font('Arial', 'B', 9)
        
        # Header Tabel
        pdf.cell(25, 8, 'Tanggal', 1, 0, 'C')
        pdf.cell(60, 8, 'Nama Makanan', 1, 0, 'C')
        pdf.cell(20, 8, 'Porsi', 1, 0, 'C')
        pdf.cell(20, 8, 'Kalori', 1, 0, 'C')
        pdf.cell(20, 8, 'Gula (g)', 1, 1, 'C')

        pdf.set_font('Arial', '', 8)
        if not food_data:
            pdf.cell(0, 8, 'Belum ada data makanan.', 1, 1, 'C')
        else:
            for row in food_data[:20]: # Batasi 20 data terakhir biar gak kepanjangan
                pdf.cell(25, 8, str(row['tanggal']), 1, 0, 'C')
                # Potong teks kalau kepanjangan
                nama_makanan = str(row['nama_makanan'])[:35]
                pdf.cell(60, 8, nama_makanan, 1, 0, 'L')
                pdf.cell(20, 8, str(row['estimasi_porsi'])[:10], 1, 0, 'C')
                pdf.cell(20, 8, f"{row['kalori']} kkal", 1, 0, 'C')
                pdf.cell(20, 8, f"{row['gula']} g", 1, 1, 'C')
        pdf.ln(5)

        # --- TABEL AIR ---
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, '2. Riwayat Air Minum', 0, 1)
        pdf.set_font('Arial', 'B', 9)
        
        pdf.cell(40, 8, 'Tanggal', 1, 0, 'C')
        pdf.cell(40, 8, 'Jumlah (ml)', 1, 1, 'C')
        
        pdf.set_font('Arial', '', 9)
        if not water_data:
            pdf.cell(0, 8, 'Belum ada data air minum.', 1, 1, 'C')
        else:
            for row in water_data[:20]:
                pdf.cell(40, 8, str(row['tanggal']), 1, 0, 'C')
                pdf.cell(40, 8, f"{row['ml']} ml", 1, 1, 'C')
        pdf.ln(5)

        # --- TABEL BERAT BADAN ---
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, '3. Riwayat Berat Badan', 0, 1)
        pdf.set_font('Arial', 'B', 9)
        
        pdf.cell(40, 8, 'Tanggal', 1, 0, 'C')
        pdf.cell(40, 8, 'Berat (kg)', 1, 1, 'C')
        
        pdf.set_font('Arial', '', 9)
        if not weight_data:
            pdf.cell(0, 8, 'Belum ada data berat badan.', 1, 1, 'C')
        else:
            for row in weight_data[:20]:
                pdf.cell(40, 8, str(row['tanggal']), 1, 0, 'C')
                pdf.cell(40, 8, f"{row['berat']} kg", 1, 1, 'C')

        # 3. Simpan File
        filename = f"laporan_gymmate_{user_id}.pdf"
        filepath = os.path.join(os.getcwd(), filename)
        pdf.output(filepath)
        
        return filepath

    except Exception as e:
        logger.error(f"Error buat laporan PDF: {e}")
        raise e