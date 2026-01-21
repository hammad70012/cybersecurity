import os
import platform
import sys

# Fix for pyzbar DLL loading on Windows
if platform.system() == "Windows":
    pyzbar_path = None
    # Find the pyzbar directory in site-packages
    for path in sys.path:
        if "site-packages" in path and os.path.isdir(os.path.join(path, "pyzbar")):
            pyzbar_path = os.path.join(path, "pyzbar")
            break
    
    # Add the pyzbar directory to the PATH environment variable
    if pyzbar_path and pyzbar_path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = f"{pyzbar_path};{os.environ.get('PATH', '')}"

import json
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, get_session
from models import Base, Scan
from utils.scanner import decode_qr_image, analyze_url_redirects

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Connecting to Redis...")
    await redis_client.ping()
    logger.info("Connected to Redis.")
    
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")
    
    yield
    
    # Shutdown
    logger.info("Closing Redis connection...")
    await redis_client.close()
    logger.info("Redis connection closed.")

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/scan")
async def scan_qr_code(
    file: UploadFile = File(...), 
    session: AsyncSession = Depends(get_session)
):
    contents = await file.read()
    
    original_url = decode_qr_image(contents)
    if not original_url:
        raise HTTPException(status_code=400, detail="Could not decode QR code from image.")

    # Check cache first
    cached_result = await redis_client.get(original_url)
    if cached_result:
        logger.info(f"Cache hit for URL: {original_url}")
        return json.loads(cached_result)

    logger.info(f"Cache miss for URL: {original_url}. Analyzing...")
    final_url, risk_score = await analyze_url_redirects(original_url)
    
    # For this project, we'll consider a high risk score as "unsafe"
    is_safe = risk_score < 75

    # Save to database
    new_scan = Scan(
        original_url=original_url,
        final_url=final_url,
        is_safe=is_safe,
        risk_score=risk_score
    )
    session.add(new_scan)
    await session.commit()
    await session.refresh(new_scan)
    
    logger.info(f"Saved scan {new_scan.id} to database.")

    # Prepare and cache the result
    result = {
        "id": new_scan.id,
        "scanned_at": new_scan.scanned_at.isoformat(),
        "original_url": new_scan.original_url,
        "final_url": new_scan.final_url,
        "is_safe": new_scan.is_safe,
        "risk_score": new_scan.risk_score
    }
    
    # Cache result for 1 hour (3600 seconds)
    await redis_client.set(original_url, json.dumps(result), ex=3600)
    
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
