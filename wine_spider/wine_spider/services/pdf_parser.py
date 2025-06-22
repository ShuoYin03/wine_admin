import PyPDF2
from io import BytesIO

class PDFParser:
    def __init__(self, pdf_file=None):
        self.pdf_file = pdf_file

    def parse(self, pdf_file=None):
        if pdf_file:
            self.pdf_file = pdf_file
        pdf_reader = PyPDF2.PdfReader(BytesIO(self.pdf_file))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    
    def parse_from_file(self, file_path=None):
        if file_path:
            self.pdf_file = file_path
        with open(self.pdf_file, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
