import datetime
import uvicorn
import os
import asyncio
import logging
from PIL import Image
import pillow_heif

from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Form
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# INIT APP -
app = FastAPI()

# Consts
MAX_FILE_SIZE = 10 * 1024 * 1024
DELETE_IMG_AFTER_SECONDS = 3600  # FOR PROD -> clears images every hour on the server via coroutine
# DELETE_IMG_AFTER_SECONDS = 60  # FOR DEV
TIMEOUT_IMG = 10  # TIMEOUT FOR SERVER REQUESTS
TEMP_IMAGE_DIR = "temp_images"

# Allowed image formats/types
ALLOWED_FORMATS = [
    "BMP",
    "GIF",
    "HEIF",
    "ICO",
    "IM",
    "JPEG",
    "JPG",
    "PCX",
    "PNG",
    "PPM",
    "SGI",
    "SPIDER",
    "TIFF",
    "WEBP"
]
ALLOWED_CONTENT_TYPES = {
    "image/bmp",
    "image/gif",
    "image/heif",
    "image/vnd.microsoft.icon",
    "image/im",
    "image/jpeg",
    "image/jpg",
    "image/pcx",
    "image/png",
    "image/x-portable-pixmap",
    "image/sgi",
    "image/spider",
    "image/tiff",
    "image/webp"
}

# Register HEIF plugin for heif conversion
pillow_heif.register_heif_opener()

# Configure Logs
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
current_time = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
log_file_path = os.path.join(log_dir, current_time + ".log")

file_handler = logging.FileHandler(log_file_path)
stream_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger(__name__)


# Middleware to log requests and responses
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Add middleware to redirect HTTP to HTTPS
# app.add_middleware(HTTPSRedirectMiddleware)

# Init Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)


# Coroutine to clean up the images on the server periodically - conservation of storage.
async def periodic_cleanup():
    while True:
        now = datetime.datetime.now().timestamp()
        for filename in os.listdir(TEMP_IMAGE_DIR):
            file_path = os.path.join(TEMP_IMAGE_DIR, filename)
            if os.path.isfile(file_path):
                file_creation_time = os.path.getctime(file_path)
                if now - file_creation_time > DELETE_IMG_AFTER_SECONDS:
                    try:
                        os.remove(file_path)
                        logger.info(f"Automatically deleted image file: {file_path}")
                    except Exception as e:
                        logger.error(f"Exception during periodic cleanup: {e}")
        await asyncio.sleep(DELETE_IMG_AFTER_SECONDS)


@app.on_event("startup")
async def startup_event():
    # Ensure temp_images dir exists
    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)
    # THIS CANNOT BE SET TO AWAIT - THE SERVER WILL HANG
    asyncio.create_task(periodic_cleanup())


@app.post("/test/")
@app.get("/test/")
@limiter.limit("10/minute")
async def test(request: Request):
    print(f"Testing {request.url}")
    response_data = {"message": "This is a test response", "url": str(request.url)}
    return JSONResponse(content=response_data)



@app.post("/convert/")
@limiter.limit("5/minute")
async def convert_image(request: Request, file: UploadFile = File(...), convert_to: str = Form(...)):
    try:
        ######################################################
        # Cybersecurity policies start here
        ######################################################
        # Check if file size is within limit
        contents = await file.read()
        print(f"Converted to: {convert_to}")
        if len(contents) > MAX_FILE_SIZE:
            logger.warning(f"File too large: {len(contents)}")
            raise HTTPException(status_code=413, detail="File too large")

        # Check for the correct format
        if convert_to.upper() not in ALLOWED_FORMATS:
            logger.info("Invalid conversion format")
            raise HTTPException(status_code=400, detail="Invalid conversion format")

        # Check for the correct content-Type Validation
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            logger.info("Invalid file type")
            raise HTTPException(status_code=400, detail="Invalid file type")

        ######################################################
        # Cybersecurity policies end here
        ######################################################
        # Reset the file pointer after reading contents
        file.file.seek(0)

        # Wrap image conversion logic in async method to enable timeout
        async def get_output_path(convert_img_to: str):
            # Open and convert the image
            img = Image.open(file.file)
            old_format = img.format
            img = img.convert("RGB")

            # Ensure temp_images dir exists
            output_dir = "temp_images/"
            os.makedirs(output_dir, exist_ok=True)

            # Save the image to the temporary image directory
            out_path = os.path.join(output_dir, f"converted_image.{convert_img_to.lower()}")
            img.save(out_path, convert_img_to.upper())

            logger.info(f"Image converted successfully. Image converted from {old_format} to {convert_img_to}")

            return out_path

        # Get the output path with an expected timeout for the server request.
        output_path = await asyncio.wait_for(get_output_path(convert_to), timeout=TIMEOUT_IMG)

        return FileResponse(output_path, media_type=f"image/{convert_to.lower()}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout while converting image")
        raise HTTPException(status_code=504, detail="Timeout while converting image")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
