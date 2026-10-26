import os
import fitz
from config import DOWNLOADS_DIR

def convert_pdf_to_images(pdf_file_path: str) -> list:
    if not os.path.exists(pdf_file_path):
        return []

    base_name = os.path.basename(pdf_file_path)
    folder_name = os.path.splitext(base_name)
    
    project_images_dir = os.path.join(DOWNLOADS_DIR, folder_name)
    os.makedirs(project_images_dir, exist_ok=True)

    image_paths = []

    try:
        doc = fitz.open(pdf_file_path)
        
        # Проходим циклом по абсолютно всем страницам проекта
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Оптимальный зум 1.5 экономит память и оставляет текст четким
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            image_name = f"page_{page_num + 1}.jpg"
            image_path = os.path.join(project_images_dir, image_name)
            
            pix.save(image_path)
            image_paths.append(image_path)
            
            pix = None
            
        doc.close()
    except Exception as e:
        print(f"Error: {e}")
        return []

    return image_paths
    
