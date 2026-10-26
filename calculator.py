import os
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from database import load_price_list
from config import DOWNLOADS_DIR

def calculate_project_estimate(ai_extracted_data: dict, project_name: str = "estimate") -> dict:
    current_prices = load_price_list()
    estimate_lines = []
    grand_total = 0
    not_found_keys = []

    wb = Workbook()
    ws = wb.active
    ws.title = "Estimate"
    ws.append(["Name", "Volume", "Unit", "Price", "Cost"])
    excel_row_index = 2

    for service_key, volume in ai_extracted_data.items():
        if service_key in current_prices:
            item = current_prices[service_key]
            price = item["price"]
            name = item["name"]
            unit = item["unit"]
            
            cost = price * volume
            grand_total += cost
            
            estimate_lines.append(
                f"🔹 {name}\n"
                f"   Объем: {volume} {unit} x {price} руб. = {cost:,.2f} руб."
            )
            
            ws.append([name, volume, unit, price, cost])
            excel_row_index += 1
        else:
            not_found_keys.append(service_key)

    ws.append(["ИТОГО:", "", "", "", f"=SUM(E2:E{excel_row_index-1})"])

    # Стойкий и надежный автоподбор ширины колонок Excel через индексы
    for col_idx in range(1, 6):
        max_len = 0
        for row in range(1, excel_row_index + 1):
            val = ws.cell(row=row, column=col_idx).value
            if val:
                max_len = max(max_len, len(str(val)))
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    excel_filename = f"{project_name}_смета.xlsx"
    excel_path = os.path.join(DOWNLOADS_DIR, excel_filename)
    wb.save(excel_path)

    report_text = "📋 **ПРЕДВАРИТЕЛЬНАЯ СМЕТА НА ОТДЕЛOЧНЫЕ РАБОТЫ**\n\n"
    if estimate_lines:
        report_text += "\n\n".join(estimate_lines)
    else:
        report_text += "⚠ Не удалось рассчитать ни одну позицию."

    report_text += f"\n\n💵 **ИТОГО: {grand_total:,.2f} руб.**"
    
    if not_found_keys:
        report_text += f"\n\nℹ _Примечание: Следующие коды работ не найдены в прайсе: {', '.join(not_found_keys)}_"

    txt_filename = f"{project_name}_отчет.txt"
    txt_path = os.path.join(DOWNLOADS_DIR, txt_filename)
    with open(txt_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(report_text)

    return {
        "total_sum": grand_total,
        "excel_file_path": excel_path,
        "txt_file_path": txt_path,
        "success": True
    }
    
