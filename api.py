#!/usr/bin/env python3
"""
FastAPI server for OCR pipeline
Accepts image uploads and returns structured appointment/medicine data
"""
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from core.ocr_pipeline import OCRPipeline

# Setup logger
logger = logging.getLogger("pj_ocr69.api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Initialize FastAPI app
app = FastAPI(
    title="OCR Pipeline API",
    description="Extract appointment and medicine label information from images",
    version="1.0.0",
)

# Initialize pipeline (shared across requests)
pipeline = OCRPipeline()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "PJ_OCR69 OCR API"
    }


@app.post("/ocr/process")
async def process_image(file: UploadFile = File(...)):
    """
    Process an image and extract structured data
    
    Args:
        file: Image file (JPG, PNG, etc.)
    
    Returns:
        JSON with status, document_type, and extracted data
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(valid_extensions)}"
            )
        
        logger.info(f"Processing file: {file.filename}")
        
        # Save uploaded file to temp location
        with NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        
        try:
            # Run pipeline
            result = pipeline.run(tmp_path)
            
            # Extract final_output (this has the clean 3-field format)
            final_output = result.get("final_output", {})
            
            # Enrich response with metadata
            response = {
                "filename": file.filename,
                "file_size": len(contents),
                **final_output,
            }
            
            logger.info(f"Processed {file.filename} -> {final_output.get('document_type', 'Unknown')}")
            return JSONResponse(content=response, status_code=200)
        
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error processing file {file.filename}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


@app.get("/")
def root():
    """API info"""
    return {
        "service": "OCR Pipeline API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "process_image": "/ocr/process (POST)",
        },
        "docs": "/docs",
    }


if __name__ == "__main__":
    import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        workers=int(os.getenv("WORKERS", "1"))
    )
