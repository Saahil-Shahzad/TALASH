import os
from PyPDF2 import PdfReader, PdfWriter

# Path to your original PDF
input_pdf_path = r"C:\Coding\Assignments\Talash\backend\data\combined_cvs_doc\Handler (8).pdf"

# Folder to save split PDFs
output_folder = r"C:\Coding\Assignments\Talash\backend\data\raw_cvs"
os.makedirs(output_folder, exist_ok=True)

# Read the PDF
reader = PdfReader(input_pdf_path)

current_writer = PdfWriter()
file_count = 1

for i, page in enumerate(reader.pages):
    # Check if the page is blank
    text = page.extract_text()
    if text is None or text.strip() == "":
        # Save current CV if writer has pages
        if len(current_writer.pages) > 0:
            output_path = os.path.join(output_folder, f"cv_{file_count}.pdf")
            with open(output_path, "wb") as f_out:
                current_writer.write(f_out)
            print(f"Saved: {output_path}")
            file_count += 1
            current_writer = PdfWriter()
    else:
        current_writer.add_page(page)

# Save the last CV if any pages left
if len(current_writer.pages) > 0:
    output_path = os.path.join(output_folder, f"cv_{file_count}.pdf")
    with open(output_path, "wb") as f_out:
        current_writer.write(f_out)
    print(f"Saved: {output_path}")