from pathlib import Path
from pypdf import PdfReader

pdf_path = Path(r"c:\Users\User\Desktop\project work\AMANI LINE\Amani_Line_Rights_Support_System_Blueprint.pdf")
out_path = Path(r"c:\Users\User\Desktop\project work\AMANI LINE\blueprint_text.txt")

reader = PdfReader(str(pdf_path))
text = "\n".join(page.extract_text() or "" for page in reader.pages)
out_path.write_text(text, encoding="utf-8")
print(f"Extracted {len(reader.pages)} pages to {out_path}")
print(text[:20000])
