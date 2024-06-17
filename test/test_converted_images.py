import mimetypes
import os
import requests
import logging
from PIL import Image
from io import BytesIO

# Setup logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "log_file.log")

if log_file_path:
    try:
        os.remove(log_file_path)
        print("Old Log file removed")
    except Exception as e:
        print("Failed to remove old log file")

file_handler = logging.FileHandler(log_file_path)
stream_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger(__name__)

# Image formats to test
ALLOWED_FORMATS = [
    "BMP",
    "GIF",
    "HEIF",
    "ICO",
    "JPEG",
    "JPG",
    "PCX",
    "PNG",
    "PPM",
    "SGI",
    "TIF",
    "TIFF",
    "WEBP"
]

# Manually define MIME types for each format
MIME_TYPES = {
    "BMP": "image/bmp",
    "GIF": "image/gif",
    "HEIF": "image/heif",
    "ICO": "image/vnd.microsoft.icon",
    "JPEG": "image/jpeg",
    "JPG": "image/jpeg",
    "PCX": "image/pcx",
    "PNG": "image/png",
    "PPM": "image/x-portable-pixmap",
    "SGI": "image/sgi",
    "TIF": "image/tiff",
    "TIFF": "image/tiff",
    "WEBP": "image/webp"
}

# URLs for local and production servers
LOCAL_SERVER_URL = "http://0.0.0.0:8080/convert/"
PRODUCTION_SERVER_URL = "https://reformatit-backend-7ivz4pmrva-wn.a.run.app/convert/"


def convert_image(url, file_path, convert_to):
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            data = {'convert_to': convert_to}
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to convert image: {response.status_code} {response.text}")
                print(f"Failed to convert image: {response.status_code} {response.text}")
                return None
    except Exception as e:
        logger.error(f"Failed to open image: {e}")
        print(f"Failed to open image: {e}")


def test_conversion(server_url):
    for src_format in ALLOWED_FORMATS:
        print("-------------------------------------------------------------------------------------------------------")
        test_image_path = f"test_images/test.{src_format.lower()}"
        logger.info(f"Image path: {test_image_path}")
        print("***********************************************************")
        for dest_format in ALLOWED_FORMATS:
            if src_format != dest_format:
                # logger.info(f"Testing conversion from {src_format} to {dest_format}")
                # print(f"Testing conversion from {src_format} to {dest_format}")

                converted_image_data = convert_image(server_url, test_image_path, dest_format)
                if converted_image_data:
                    # Save and verify the converted image
                    # Save and verify the converted image
                    if dest_format.upper() == "HEIF":
                        # Save the HEIF image using pillow_heif
                        output_dir = "test_images_converted"
                        os.makedirs(output_dir, exist_ok=True)
                        converted_image_path = os.path.join(output_dir,
                                                            f"{src_format.lower()}_to_{dest_format.lower()}.heif")
                        with open(converted_image_path, 'wb') as out_file:
                            out_file.write(converted_image_data)
                        logger.info(f"Successfully converted {src_format} to {dest_format}")
                        print(f"Successfully converted {src_format} to {dest_format}")
                        print("***********************************************************")
                    else:
                        converted_image = Image.open(BytesIO(converted_image_data))
                        output_dir = "test_images_converted"
                        os.makedirs(output_dir, exist_ok=True)
                        converted_image_path = os.path.join(
                            output_dir,
                            f"{src_format.lower()}_to_{dest_format.lower()}.{dest_format.lower()}"
                        )

                        # Correct format strings for certain formats
                        save_path = ""
                        if dest_format.upper() == "JPG":
                            save_format = "JPEG"
                        elif dest_format.upper() == "TIF":
                            save_format = "TIFF"
                        else:
                            save_format = dest_format.upper()

                        converted_image.save(converted_image_path, save_format)
                        # Verify the conversion
                        if converted_image.format == save_format:
                            logger.info(f"Successfully converted {src_format} to {save_format}")
                            print(f"Successfully converted {src_format} to {save_format}")
                        else:
                            logger.error(f"Conversion from {src_format} to {save_format} failed")
                            print(f"Conversion from {src_format} to {save_format} failed")
                        print("***********************************************************")


def main():
    print("Choose the server to test:")
    print("1. Local server")
    print("2. Production server")
    print("3. Both")
    print("4. Quit Test")

    quit_test = False
    while not quit_test:
        choice = input("\nEnter 1, 2, 3, or 4: ")
        if choice == "1":
            test_conversion(LOCAL_SERVER_URL)
            quit_test = True
        elif choice == "2":
            test_conversion(PRODUCTION_SERVER_URL)
            quit_test = True
        elif choice == "3":
            test_conversion(LOCAL_SERVER_URL)
            test_conversion(PRODUCTION_SERVER_URL)
            quit_test = True
        elif choice == "4":
            quit_test = True
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
