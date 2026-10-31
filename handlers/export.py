import csv
import io
import logging
from bot_instance import bot
from database.queries import get_all_data_for_export

logger = logging.getLogger(__name__)

@bot.callback_query_handler(func=lambda call: call.data == "menu_export")
def callback_menu_export(call):
    try:
        bot.answer_callback_query(call.id, "⏳ Nyiapin file CSV...")
        user_id = call.from_user.id
        
        food_data, water_data, weight_data = get_all_data_for_export(user_id)
        
        if not food_data and not water_data and not weight_data:
            bot.send_message(call.message.chat.id, "⚠️ Belum ada data yang bisa di-export. Coba catat makanan atau minum air dulu ya.")
            return
            
        # Bikin file CSV di dalam memori
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Bagian 1: Log Makanan
        writer.writerow(["=== LOG MAKANAN ==="])
        writer.writerow(["Tanggal", "Nama Makanan", "Porsi", "Kalori", "Protein (g)", "Karbo (g)", "Lemak (g)", "Gula (g)", "Waktu"])
        for row in food_data:
            writer.writerow(row)
            
        writer.writerow([])
        
        # Bagian 2: Log Air Minum
        writer.writerow(["=== LOG AIR MINUM ==="])
        writer.writerow(["Tanggal", "Jumlah (ml)", "Waktu"])
        for row in water_data:
            writer.writerow(row)
            
        writer.writerow([])
        
        # Bagian 3: Log Berat Badan
        writer.writerow(["=== LOG BERAT BADAN ==="])
        writer.writerow(["Tanggal", "Berat (kg)", "Waktu"])
        for row in weight_data:
            writer.writerow(row)
            
        # Convert ke bytes
        output.seek(0)
        file_bytes = output.getvalue().encode('utf-8')
        
        # Kirim ke Telegram
        bot.send_document(
            call.message.chat.id, 
            document=("Laporan_Fitness_Gym.csv", file_bytes), 
            caption="📊 *Laporan Fitness Lu!*\n\nBuka file ini pake Excel atau Google Sheets buat liat semua history lu."
        )
        
    except Exception as e:
        logger.error(f"[export] error: {e}")
        bot.send_message(call.message.chat.id, "❌ Gagal export data. Coba lagi nanti.")