import io
import base64
import ddddocr
import cairosvg
from PIL import Image, ImageOps

class CaptchaParser:
    def __init__(self):
        self.ocr = ddddocr.DdddOcr()

    def parse_captcha(self, base64_str):
        base64_str = base64_str.split(",")[1]
        decoded_data = base64.b64decode(base64_str)
        
        png_data = cairosvg.svg2png(bytestring=decoded_data)
        image = Image.open(io.BytesIO(png_data))
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, (1, 1), image)

        self.ocr.set_ranges(6)
        result = self.ocr.classification(background, probability=True)
        s = ""
        for i in result['probability']:
            s += result['charsets'][i.index(max(i))]

        return s