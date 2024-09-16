import requests
from requests import Session
from urllib.parse import urljoin
from parsel import Selector
from PIL import Image
import pytesseract
import tempfile
import os
import time
import re

class BTKSorgu:
    def __init__(self, sorgu_url: str):
        self.ana_sayfa = "https://internet2.btk.gov.tr"
        self.sorgu_sayfasi = "https://internet2.btk.gov.tr/sitesorgu/"
        self.sorgu_url = self._temizle_url(sorgu_url)
        self.oturum = Session()
        self.oturum.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    def _temizle_url(self, url: str) -> str:
        return re.search(r"(?:https?://)?(?:www\.)?([^/]+)", url).group(1)

    def __captcha_ver(self):
        try:
            ilk_bakis = self.oturum.get(self.sorgu_sayfasi, allow_redirects=True)
            tum_resimler = Selector(ilk_bakis.text).xpath("//img/@src").getall()
            captcha_yolu = next((yol for yol in tum_resimler if 'captcha' in yol.lower()), None)

            if not captcha_yolu:
                return None

            captcha_url = urljoin(self.ana_sayfa, captcha_yolu)
            captcha_response = self.oturum.get(captcha_url, stream=True)
            captcha_response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_filename = temp_file.name
                temp_file.write(captcha_response.content)

            try:
                image = Image.open(temp_filename)
                captcha_harfleri = pytesseract.image_to_string(image).strip().replace(" ", "")
                return captcha_harfleri if captcha_harfleri else None
            finally:
                os.unlink(temp_filename)

        except Exception:
            return None

    def karar_ver(self):
        captcha = self.__captcha_ver()
        if not captcha:
            return "Captcha alınamadı veya okunamadı. Lütfen tekrar deneyin."

        try:
            karar_sayfasi = self.oturum.post(
                url=self.sorgu_sayfasi,
                data={
                    "deger": self.sorgu_url,
                    "ipw": "",
                    "kat": "",
                    "tr": "",
                    "eg": "",
                    "ayrintili": 0,
                    "submit": "Sorgula",
                    "security_code": captcha
                }
            )
            karar_sayfasi.raise_for_status()

            secici = Selector(karar_sayfasi.text)
            hatali_kod = secici.xpath("//div[@class='icerik']/ul/li/text()").get()
            erisim_var = secici.xpath("//div[@class='yazi2']/text()").get()
            erisim_yok = secici.xpath("//span[@class='yazi2_2']/text()").get()

            return hatali_kod or erisim_var or erisim_yok or "Sonuç bulunamadı."

        except Exception:
            return "Sorgulama sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin."

    def __repr__(self) -> str:
        return self.karar_ver()