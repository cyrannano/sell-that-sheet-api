from PIL import Image
import io
import base64
import requests

from django.conf import settings
from rest_framework import status

def perform_ocr(image_full_path:str) -> str:
    """
    Function to perform OCR on an image
    :param image_path: path to the image
    :return: text extracted from the image
    """
    # Open the image file using Pillow
    with Image.open(image_full_path) as img:
        # Convert the image to RGB if it's in a different mode (e.g., CMYK)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Save the image to a BytesIO object
        image_io = io.BytesIO()
        img.save(image_io, format='JPEG')
        image_data = image_io.getvalue()

        # Check the size and resize if necessary
        max_size = 1 * 1024 * 1024  # 1MB in bytes
        if len(image_data) > max_size:
            # Calculate the reduction factor
            reduction_factor = 0.9  # Start by reducing quality by 10%
            quality = 90

            # Reduce image size iteratively until it's under 1MB
            while len(image_data) > max_size and quality > 10:
                image_io = io.BytesIO()
                img.save(image_io, format='JPEG', quality=quality)
                image_data = image_io.getvalue()
                quality = int(quality * reduction_factor)

            # If the image is still too large, resize its dimensions
            if len(image_data) > max_size:
                width, height = img.size
                resize_factor = 0.9  # Reduce dimensions by 10% each iteration

                while len(image_data) > max_size and width > 100 and height > 100:
                    width = int(width * resize_factor)
                    height = int(height * resize_factor)
                    img_resized = img.resize((width, height), Image.ANTIALIAS)
                    image_io = io.BytesIO()
                    img_resized.save(image_io, format='JPEG', quality=quality)
                    image_data = image_io.getvalue()

            # Final check
            if len(image_data) > max_size:
                raise ValueError('Image size exceeds 1MB limit')

    # Convert image data to Base64
    base64_image = (
            'data:image/jpeg;base64,'
            + base64.b64encode(image_data).decode('utf-8')
    )

    # Send to OCR API
    api_key = settings.OCR_API_KEY
    if not api_key:
        raise ValueError('OCR API key is missing')

    ocr_response = requests.post(
        'https://api.ocr.space/parse/image',
        data={
            'base64Image': base64_image,
            'OCREngine': '2',
        },
        headers={
            'apikey': api_key,
        },
    )
    ocr_response.raise_for_status()

    ocr_result_json = ocr_response.json()
    parsed_text = (
        ocr_result_json.get('ParsedResults', [{}])[0].get('ParsedText', '')
    )

    return parsed_text