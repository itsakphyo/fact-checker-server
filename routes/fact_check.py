import os
import json
import logging
from PIL import Image
from io import BytesIO
from pydantic import BaseModel, field_validator
from typing import Optional, Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from dotenv import load_dotenv
from routes.utils import ask_gemini, prepare_image_for_gemma, transcript_image, ocr_image

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

router = APIRouter()

# Prepare Gemini client
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# Prepare Google Translate client
cred_dict = json.loads(os.getenv("GOOGLE_CREDENTIAL_JSON"))
credentials = service_account.Credentials.from_service_account_info(cred_dict)
translate_client = translate.Client(credentials=credentials)

# Prepare logger
logger = logging.getLogger("fact_check_service")

# Define request and response models
class FactCheckRequest(BaseModel):
    description: Optional[str] = None
    language: Optional[str] = "en"

    @field_validator('description', mode='after')
    @classmethod
    def require_description_or_image(cls, v):
        return v

# -- Endpoint for fact-checking with description and optional image --
@router.post("/fact-check")
async def fact_check(
    file: Optional[UploadFile] = File(None),
    description: Optional[str] = Form(None),
    language: Optional[str] = Form("English"),
) -> JSONResponse:
    """
    Fact-check a description with an optional image file.
    If an image is provided, it will be transcribed and OCR will be performed. 
    The description and image will be sent to the Gemini model for analysis.
    """
    if not description and not file:
        raise HTTPException(status_code=400, detail="Either description or image file must be provided.")

    if description and len(description) > 1000:
        raise HTTPException(status_code=400, detail="Description is too long. Maximum length is 1000 characters.")
   
    descriptions = {}

    if file is None:
        translated_description = translate_client.translate(
                description, target_language="en"
            )["translatedText"]
        descriptions["User provided description"] = translated_description
        response = ask_gemini(descriptions)
        return JSONResponse(content={"result": response})

    if file:
        
        if description:
            translated_description = translate_client.translate(
                description, target_language="en"
            )["translatedText"]
            descriptions["User provided description"] = translated_description

        try:
            image_part = await prepare_image_for_gemma(file)

            # Transcribe the image
            image_transcription = transcript_image(image_part)
            descriptions["User provided image transcription"] = image_transcription

            # Get OCR for the image
            image_ocr = ocr_image(image_part, language)
            descriptions["Extracted text form image with OCR"] = image_ocr

        except OSError:
            raise HTTPException(status_code=400, detail="Image processing error. OS error occurred while reading the image file.")
        except IOError:
            raise HTTPException(status_code=400, detail="Image processing error. IO error occurred while reading the image file.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Try with image error: {str(e)}")
        
        
        response = ask_gemini(descriptions)
        return JSONResponse(content={"result": response})

