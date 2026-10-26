import os
import fitz
from config import DOWNLOADS_DIR

def convert_pdf_to_images(pdf_file_path: str) -> list:
    if not os.path.exists(pdf_file_path):
        return []

    base_name = os.path.basename(pdf_file_path)
    folder_name = os.path.splitext(base_name)[0]
    
    project_images_dir = os.path.join(DOWNLOADS_DIR, folder_name)
    os.makedirs(project_images_dir, exist_ok=True)

    image_paths = []

    try:
        # Открываем PDF
        doc = fitz.open(pdf_file_path)
        
        # Для диагностики на бесплатном тарифе берем ТОЛЬКО первую страницу
        # Это сэкономит оперативную память и не уронит сервер
        if len(doc) > 0:
            page = doc.load_page(0)
            
            # Снижаем zoom с 3 до 1.5 для жесткой экономии ОЗУ
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            image_name = "page_1.jpg"
            image_path = os.path.join(project_images_dir, image_name)
            
            pix.save(image_path)
            image_paths.append(image_path)
            
            # Очищаем память
            pix = None
            
        doc.close()
    except Exception as e:
        print(f"Error: {e}")
        return []

    return image_paths
    
