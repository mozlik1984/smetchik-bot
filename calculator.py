import os
from openpyxl import Workbook
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
            
            estimate_lines.append(f"- {name}: {volume} {unit} x {price} = {cost:,.2f}")
            ws.append([name, volume, unit, price, cost])
            excel_row_index += 1
        else:
            not_found_keys.append(service_key)

    ws.append(["TOTAL:", "", "", "", f"=SUM(E2:E{excel_row_index-1})"])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col.column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    excel_filename = f"{project_name}_estimate.xlsx"
    excel_path = os.path.join(DOWNLOADS_DIR, excel_filename)
    wb.save(excel_path)

    report_text = "ESTIMATE REPORT\n\n"
    if estimate_lines:
        report_text += "\n".join(estimate_lines)
    else:
        report_text += "No positions calculated."

    report_text += f"\n\nTOTAL: {grand_total:,.2f}"

    txt_filename = f"{project_name}_report.txt"
    txt_path = os.path.join(DOWNLOADS_DIR, txt_filename)
    with open(txt_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(report_text)

    return {
        "total_sum": grand_total,
        "excel_file_path": excel_path,
        "txt_file_path": txt_path,
        "success": True
    }
  
