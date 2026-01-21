import io
import httpx
import cv2
import numpy as np
from PIL import Image
import random

def decode_qr_image(file_bytes: bytes) -> str | None:
    """
    Decodes a QR code from image bytes using OpenCV and returns the URL.
    """
    try:
        # Convert image bytes to a NumPy array that OpenCV can process
        image = Image.open(io.BytesIO(file_bytes))
        
        # Convert PIL image to an OpenCV image (NumPy array)
        # It's converted to grayscale automatically by the detector if needed
        open_cv_image = np.array(image) 
        
        # Initialize the QR code detector
        detector = cv2.QRCodeDetector()

        # Detect and decode the QR code
        decoded_text, points, _ = detector.detectAndDecode(open_cv_image)

        if points is not None and decoded_text:
            return decoded_text
    except Exception as e:
        # Log the error for debugging
        print(f"Error decoding QR image with OpenCV: {e}")
    return None

async def analyze_url_redirects(url: str) -> tuple[str, int]:
    """
    Follows redirects to find the final URL and returns a dummy risk score.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            final_url = str(response.url)
            # Dummy risk score for now
            risk_score = random.randint(0, 100)
            return final_url, risk_score
    except httpx.RequestError as e:
        print(f"Error analyzing URL {url}: {e}")
        return url, 99 # Assign a high risk score on error