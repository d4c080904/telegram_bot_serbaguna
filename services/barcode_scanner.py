import cv2
import numpy as np
import httpx
import logging

logger = logging.getLogger(__name__)

def decode_barcode(image_bytes: bytes) -> str:
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
        
        # --- TRIK BARU: Tambahin border putih (quiet zone) ---
        # Ini bikin OpenCV lebih gampang mendeteksi barcode
        img = cv2.copyMakeBorder(img, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=[255, 255, 255])
        
        detector = cv2.barcode.BarcodeDetector()
        retval, decoded_info, decoded_type, points = detector.detectAndDecode(img)
        
        if retval and decoded_info:
            return decoded_info[0]
        return None
    except Exception as e:
        logger.error(f"Error decoding barcode: {e}")
        return None

async def get_product_from_openfoodfacts(barcode: str) -> dict:
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    product = data.get('product', {})
                    nutriments = product.get('nutriments', {})
                    
                    raw_cat = product.get('categories', 'Makanan/Minuman Olahan')
                    kategori = raw_cat.split(',')[0].strip().capitalize() if raw_cat else "Makanan/Minuman Olahan"
                    
                    return {
                        "nama": product.get('product_name', 'Produk Tanpa Nama'),
                        "kategori": kategori,
                        "kalori": round(float(nutriments.get('energy-kcal_100g', 0)), 1),
                        "protein": round(float(nutriments.get('proteins_100g', 0)), 1),
                        "karbo": round(float(nutriments.get('carbohydrates_100g', 0)), 1),
                        "lemak": round(float(nutriments.get('fat_100g', 0)), 1),
                        "gula": round(float(nutriments.get('sugars_100g', 0)), 1)
                    }
            return None
        except Exception as e:
            logger.error(f"OpenFoodFacts API error: {e}")
            return None