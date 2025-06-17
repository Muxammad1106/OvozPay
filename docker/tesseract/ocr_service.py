"""
Tesseract OCR Microservice for OvozPay
FastAPI service for receipt text recognition
"""

import os
import tempfile
import logging
from io import BytesIO
from typing import Dict, Any, List

import pytesseract
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OvozPay OCR Service",
    description="Tesseract OCR microservice for receipt recognition",
    version="1.0.0"
)

# OCR Configuration
TESSERACT_CONFIG = {
    'lang': 'rus+eng+uzb+uzb_cyrl',
    'config': '--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя0123456789.,:-№₽$€ '
}

# Supported image formats
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']


class OCRProcessor:
    """OCR processing class"""
    
    def __init__(self):
        self.verify_tesseract_installation()
    
    def verify_tesseract_installation(self):
        """Verify Tesseract installation and languages"""
        try:
            version = pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages()
            logger.info(f"Tesseract version: {version}")
            logger.info(f"Available languages: {languages}")
            
            required_langs = ['rus', 'eng', 'uzb']
            missing_langs = [lang for lang in required_langs if lang not in languages]
            if missing_langs:
                logger.warning(f"Missing languages: {missing_langs}")
            else:
                logger.info("All required languages are available")
                
        except Exception as e:
            logger.error(f"Tesseract verification failed: {e}")
            raise
    
    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Convert PIL Image to OpenCV format
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                img_cv = img_array
            
            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            # Return original image as grayscale fallback
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    
    def extract_text(self, image: Image.Image) -> Dict[str, Any]:
        """Extract text from image using Tesseract"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image)
            
            # Convert back to PIL for Tesseract
            pil_img = Image.fromarray(processed_img)
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(
                pil_img,
                lang=TESSERACT_CONFIG['lang'],
                config=TESSERACT_CONFIG['config'],
                output_type=pytesseract.Output.DICT
            )
            
            # Extract plain text
            text = pytesseract.image_to_string(
                pil_img,
                lang=TESSERACT_CONFIG['lang'],
                config=TESSERACT_CONFIG['config']
            )
            
            # Calculate confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Parse receipt data
            receipt_data = self.parse_receipt_data(text, data)
            
            return {
                'raw_text': text.strip(),
                'confidence': avg_confidence / 100.0,  # Convert to 0-1 scale
                'receipt_data': receipt_data,
                'word_count': len([word for word in data['text'] if word.strip()]),
                'processing_metadata': {
                    'tesseract_version': str(pytesseract.get_tesseract_version()),
                    'languages_used': TESSERACT_CONFIG['lang'],
                    'psm_mode': 6,
                    'preprocessing_applied': True
                }
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                'raw_text': '',
                'confidence': 0.0,
                'receipt_data': {},
                'word_count': 0,
                'processing_metadata': {
                    'error': str(e)
                }
            }
    
    def parse_receipt_data(self, text: str, ocr_data: Dict) -> Dict[str, Any]:
        """Parse receipt-specific data from OCR text"""
        import re
        from datetime import datetime
        
        lines = text.split('\n')
        receipt_info = {
            'shop_name': None,
            'receipt_number': None,
            'date': None,
            'total_amount': 0.0,
            'items': [],
            'language_detected': 'mixed'
        }
        
        # Patterns for different data
        amount_patterns = [
            r'итого[:\s]+(\d+[\.,]?\d*)',
            r'сумма[:\s]+(\d+[\.,]?\d*)',
            r'total[:\s]+(\d+[\.,]?\d*)',
            r'jami[:\s]+(\d+[\.,]?\d*)',
            r'(\d+[\.,]?\d*)\s*сум',
            r'(\d+[\.,]?\d*)\s*sum'
        ]
        
        date_patterns = [
            r'(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})',
            r'(\d{1,2}-\d{1,2}-\d{2,4})'
        ]
        
        receipt_patterns = [
            r'чек[№\s#]*(\d+)',
            r'check[№\s#]*(\d+)',
            r'№\s*(\d+)'
        ]
        
        # Extract total amount
        for pattern in amount_patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    amount = float(match.group(1).replace(',', '.'))
                    receipt_info['total_amount'] = max(receipt_info['total_amount'], amount)
                except ValueError:
                    continue
        
        # Extract date
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                receipt_info['date'] = match.group(1)
                break
        
        # Extract receipt number
        for pattern in receipt_patterns:
            match = re.search(pattern, text.lower())
            if match:
                receipt_info['receipt_number'] = match.group(1)
                break
        
        # Extract shop name (usually first meaningful line)
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and not re.match(r'^\d+[\.,]?\d*$', line):
                if not receipt_info['shop_name']:
                    receipt_info['shop_name'] = line
                    break
        
        # Extract items (basic pattern matching)
        item_patterns = [
            r'([а-яёa-zА-ЯЁA-Z\s]+)\s+(\d+[\.,]?\d*)',
            r'([а-яёa-zА-ЯЁA-Z\s]{3,})\s+.*?(\d+[\.,]?\d*)\s*$'
        ]
        
        for line in lines:
            line = line.strip()
            if len(line) < 5:
                continue
                
            for pattern in item_patterns:
                match = re.search(pattern, line)
                if match and len(match.group(1)) > 3:
                    try:
                        item_name = match.group(1).strip()
                        item_price = float(match.group(2).replace(',', '.'))
                        if item_price > 0:
                            receipt_info['items'].append({
                                'name': item_name,
                                'price': item_price
                            })
                    except (ValueError, IndexError):
                        continue
        
        # Detect language
        cyrillic_chars = len(re.findall(r'[а-яёА-ЯЁ]', text))
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if cyrillic_chars > latin_chars * 2:
            receipt_info['language_detected'] = 'ru'
        elif latin_chars > cyrillic_chars * 2:
            receipt_info['language_detected'] = 'en'
        else:
            receipt_info['language_detected'] = 'mixed'
        
        return receipt_info


# Initialize OCR processor
ocr_processor = OCRProcessor()


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OvozPay OCR Service", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Tesseract availability
        version = pytesseract.get_tesseract_version()
        languages = pytesseract.get_languages()
        
        return {
            "status": "healthy",
            "tesseract_version": str(version),
            "available_languages": languages,
            "required_languages": ["rus", "eng", "uzb"],
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/status")
async def get_status():
    """Get service status and configuration"""
    try:
        return {
            "service": "OvozPay OCR",
            "version": "1.0.0",
            "tesseract_config": TESSERACT_CONFIG,
            "supported_formats": SUPPORTED_FORMATS,
            "tesseract_version": str(pytesseract.get_tesseract_version()),
            "available_languages": pytesseract.get_languages()
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/process_receipt")
async def process_receipt(file: UploadFile = File(...)):
    """Process receipt image and extract text"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported: {SUPPORTED_FORMATS}"
        )
    
    try:
        # Read image
        image_data = await file.read()
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Process image with OCR
        result = ocr_processor.extract_text(image)
        
        # Return results
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "file_size": len(image_data),
            "image_dimensions": image.size,
            "ocr_results": result
        })
        
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/extract_text")
async def extract_text_only(file: UploadFile = File(...)):
    """Extract only text without receipt parsing"""
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        # Read and process image
        image_data = await file.read()
        image = Image.open(BytesIO(image_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text only
        processed_img = ocr_processor.preprocess_image(image)
        pil_img = Image.fromarray(processed_img)
        
        text = pytesseract.image_to_string(
            pil_img,
            lang=TESSERACT_CONFIG['lang'],
            config=TESSERACT_CONFIG['config']
        )
        
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "extracted_text": text.strip()
        })
        
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "ocr_service:app",
        host="0.0.0.0",
        port=8001,
        workers=2,
        log_level="info"
    ) 