"""
Whisper Voice Recognition Microservice for OvozPay
FastAPI service for speech-to-text processing
"""

import os
import tempfile
import logging
from io import BytesIO
from typing import Dict, Any, List, Optional
from datetime import datetime

import whisper
import torch
import librosa
import soundfile as sf
from pydub import AudioSegment
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OvozPay Whisper Service",
    description="Whisper AI microservice for voice recognition",
    version="1.0.0"
)

# Whisper Configuration
SUPPORTED_MODELS = ['tiny', 'base', 'small', 'medium', 'large']
DEFAULT_MODEL = 'base'
SUPPORTED_LANGUAGES = {
    'ru': 'russian',
    'en': 'english', 
    'uz': 'uzbek',
    'auto': 'automatic detection'
}

# Audio processing settings
AUDIO_CONFIG = {
    'sample_rate': 16000,
    'channels': 1,
    'format': 'wav'
}

# Supported audio formats
SUPPORTED_FORMATS = ['.mp3', '.wav', '.ogg', '.m4a', '.mp4', '.webm', '.oga']


class WhisperProcessor:
    """Whisper AI processing class"""
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        self.load_model()
    
    def load_model(self):
        """Load Whisper model"""
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name, device=self.device)
            logger.info(f"Model {self.model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def switch_model(self, model_name: str):
        """Switch to different Whisper model"""
        if model_name not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")
        
        if model_name != self.model_name:
            logger.info(f"Switching from {self.model_name} to {model_name}")
            self.model_name = model_name
            self.load_model()
    
    def preprocess_audio(self, audio_data: bytes, original_format: str) -> str:
        """Preprocess audio for optimal Whisper input"""
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=original_format, delete=False) as temp_input:
                temp_input.write(audio_data)
                temp_input_path = temp_input.name
            
            # Convert audio using pydub
            audio = AudioSegment.from_file(temp_input_path)
            
            # Convert to mono, 16kHz
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)
            
            # Export as WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
                temp_output_path = temp_output.name
                audio.export(temp_output_path, format='wav')
            
            # Clean up input file
            os.unlink(temp_input_path)
            
            return temp_output_path
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            # Cleanup
            if 'temp_input_path' in locals() and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            raise
    
    def transcribe_audio(
        self, 
        audio_path: str, 
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        try:
            # Prepare options
            options = {
                "task": task,  # "transcribe" or "translate"
                "fp16": False,  # Use fp32 for better compatibility
            }
            
            if language and language != 'auto':
                options["language"] = language
            
            # Transcribe
            logger.info(f"Transcribing audio with model {self.model_name}")
            result = self.model.transcribe(audio_path, **options)
            
            # Process results
            return self.process_transcription_result(result)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def process_transcription_result(self, result: Dict) -> Dict[str, Any]:
        """Process Whisper transcription result"""
        try:
            # Extract main text
            text = result.get('text', '').strip()
            
            # Extract segments information
            segments = result.get('segments', [])
            
            # Calculate confidence scores
            confidence_scores = []
            for segment in segments:
                if 'avg_logprob' in segment:
                    # Convert log probability to confidence score (0-1)
                    confidence = min(1.0, max(0.0, (segment['avg_logprob'] + 1.0)))
                    confidence_scores.append(confidence)
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            # Extract language information
            detected_language = result.get('language', 'unknown')
            
            # Process segments for detailed analysis
            processed_segments = []
            for segment in segments:
                processed_segments.append({
                    'start': segment.get('start', 0),
                    'end': segment.get('end', 0),
                    'text': segment.get('text', '').strip(),
                    'confidence': min(1.0, max(0.0, (segment.get('avg_logprob', -1.0) + 1.0)))
                })
            
            return {
                'text': text,
                'language': detected_language,
                'confidence': avg_confidence,
                'segments': processed_segments,
                'segments_count': len(segments),
                'total_duration': segments[-1]['end'] if segments else 0,
                'model_used': self.model_name,
                'processing_metadata': {
                    'device': self.device,
                    'model_name': self.model_name,
                    'segments_processed': len(segments),
                    'has_segments': len(segments) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Result processing failed: {e}")
            return {
                'text': result.get('text', ''),
                'language': result.get('language', 'unknown'),
                'confidence': 0.5,
                'segments': [],
                'segments_count': 0,
                'total_duration': 0,
                'model_used': self.model_name,
                'processing_metadata': {
                    'error': str(e)
                }
            }


# Initialize Whisper processor
whisper_processor = WhisperProcessor()


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "OvozPay Whisper Service", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test model availability
        model_info = {
            "status": "healthy",
            "model_loaded": whisper_processor.model is not None,
            "current_model": whisper_processor.model_name,
            "device": whisper_processor.device,
            "supported_models": SUPPORTED_MODELS,
            "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
            "timestamp": str(datetime.now())
        }
        
        return model_info
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/status")
async def get_status():
    """Get service status and configuration"""
    return {
        "service": "OvozPay Whisper",
        "version": "1.0.0",
        "current_model": whisper_processor.model_name,
        "available_models": SUPPORTED_MODELS,
        "supported_languages": SUPPORTED_LANGUAGES,
        "supported_formats": SUPPORTED_FORMATS,
        "audio_config": AUDIO_CONFIG,
        "device": whisper_processor.device,
        "torch_version": torch.__version__
    }


@app.get("/models")
async def get_available_models():
    """Get available Whisper models"""
    return {
        "current_model": whisper_processor.model_name,
        "available_models": {
            "tiny": "~39 MB, fastest, least accurate",
            "base": "~74 MB, good speed/accuracy balance",
            "small": "~244 MB, better accuracy",
            "medium": "~769 MB, very good accuracy",
            "large": "~1550 MB, best accuracy"
        },
        "supported_languages": SUPPORTED_LANGUAGES
    }


@app.post("/switch_model")
async def switch_model(model_name: str = Form(...)):
    """Switch to different Whisper model"""
    try:
        if model_name not in SUPPORTED_MODELS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported model. Available: {SUPPORTED_MODELS}"
            )
        
        old_model = whisper_processor.model_name
        whisper_processor.switch_model(model_name)
        
        return {
            "success": True,
            "message": f"Switched from {old_model} to {model_name}",
            "current_model": model_name
        }
        
    except Exception as e:
        logger.error(f"Model switch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Model switch failed: {str(e)}")


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    task: str = Form("transcribe")
):
    """Transcribe audio file to text"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {SUPPORTED_FORMATS}"
        )
    
    # Validate language
    if language not in SUPPORTED_LANGUAGES and language != 'auto':
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    
    # Validate task
    if task not in ['transcribe', 'translate']:
        raise HTTPException(
            status_code=400,
            detail="Task must be 'transcribe' or 'translate'"
        )
    
    try:
        # Read audio data
        audio_data = await file.read()
        
        # Preprocess audio
        processed_audio_path = whisper_processor.preprocess_audio(audio_data, file_ext)
        
        try:
            # Transcribe
            whisper_language = None if language == 'auto' else language
            result = whisper_processor.transcribe_audio(
                processed_audio_path, 
                language=whisper_language,
                task=task
            )
            
            # Return results
            return JSONResponse(content={
                "success": True,
                "filename": file.filename,
                "file_size": len(audio_data),
                "transcription": result
            })
            
        finally:
            # Clean up processed audio file
            if os.path.exists(processed_audio_path):
                os.unlink(processed_audio_path)
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.post("/transcribe_simple")
async def transcribe_simple(file: UploadFile = File(...)):
    """Simple transcription with automatic language detection"""
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        # Read and process
        audio_data = await file.read()
        file_ext = os.path.splitext(file.filename.lower())[1]
        
        processed_audio_path = whisper_processor.preprocess_audio(audio_data, file_ext)
        
        try:
            result = whisper_processor.transcribe_audio(processed_audio_path)
            
            return JSONResponse(content={
                "success": True,
                "text": result['text'],
                "language": result['language'],
                "confidence": result['confidence']
            })
            
        finally:
            if os.path.exists(processed_audio_path):
                os.unlink(processed_audio_path)
        
    except Exception as e:
        logger.error(f"Simple transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.get("/languages")
async def get_supported_languages():
    """Get supported languages"""
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "note": "Use 'auto' for automatic language detection"
    }


if __name__ == "__main__":
    uvicorn.run(
        "whisper_service:app",
        host="0.0.0.0",
        port=8002,
        workers=1,  # Whisper models are memory intensive, use single worker
        log_level="info"
    ) 