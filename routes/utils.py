from google import genai
from google.genai import types
from fastapi import HTTPException
from PIL import Image
from io import BytesIO
import logging
import os
from routes.prompts import FACT_CHECK_SYSTEM_PROMPT, TRANSCRIBE_IMAGE_PROMPT, OCR_IMAGE_PROMPT

genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
logger = logging.getLogger("fact_check_service")

def ask_gemini(descriptions: dict) -> str:
    """
    Ask Gemini model to analyze the provided descriptions and return a structured JSON response with stronger deep analysis,
    including potential web search for supporting information.
    """
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro-preview-05-06",
        config=types.GenerateContentConfig(
            system_instruction=FACT_CHECK_SYSTEM_PROMPT
        ),
        contents=str(descriptions)
    )
    if not response.text:
        raise RuntimeError("Gemini model returned empty response")
    return response.text

async def prepare_image_for_gemma(file):
    """
    Prepare the image file for processing by converting it to RGB format and returning it as a Gemini Part.
    """
    image_bytes = await file.read()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    rgb_image_bytes = buffer.read()

    return types.Part.from_bytes(
        data=rgb_image_bytes,
        mime_type="image/png"
    )

def transcript_image(image) -> str:
    """
    Transcribe the provided image using the VLM model.
    """
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[TRANSCRIBE_IMAGE_PROMPT, image],
        )
        return response.text

    except Exception as e:
        logger.error(f"Image processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Image processing failed")

def ocr_image(image, language) -> str:
    """
    Perform OCR on the provided image using the VLM model.
    """
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[OCR_IMAGE_PROMPT(language), image]
        )
        return response.text

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="OCR processing failed")