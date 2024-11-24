import os
import json
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from uuid import uuid4

from utils.file import dump_uploaded_file
from indic_ocr.ocr import OCR

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

## --------------- Authentication --------------- ##

PRODUCTION_MODE = True

security = HTTPBasic()

# Load credentials
with open('credentials.json') as f:
    CREDENTIALS = json.load(f)

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if not PRODUCTION_MODE:
        return True
    
    correct_username = secrets.compare_digest(credentials.username, CREDENTIALS["username"])
    correct_password = secrets.compare_digest(credentials.password, CREDENTIALS["password"])
    
    if correct_username and correct_password:
        return True
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

## --------------- OCR Configuration --------------- ##

CONFIGS_PATH = 'configs/*.json'

IMAGES_FOLDER = os.path.join('images', 'server')
OUTPUT_FOLDER = os.path.join(IMAGES_FOLDER, 'output')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class OCR_ConfigName(str, Enum):
    easy_ocr = "easy_ocr"
    google_ocr = "google_ocr"

DEFAULT_CONFIG_NAME = OCR_ConfigName.easy_ocr

LOADED_MODELS = {}

def get_model(config_name: str, additional_langs: Optional[List[str]] = None):
    code_name = config_name
    if additional_langs:
        additional_langs = sorted(additional_langs)
        code_name += '--' + '_'.join(additional_langs)
    
    if code_name in LOADED_MODELS:
        return LOADED_MODELS[code_name]
    
    print(f'Loading model {code_name}')
    config = CONFIGS_PATH.replace('*', config_name)
    model = OCR(config, additional_langs)
    
    LOADED_MODELS[code_name] = model
    return model

def perform_ocr(img_path: str, config_name: str, additional_langs: List[str] = []):
    ocr = get_model(config_name, additional_langs)
    return ocr.process_img(img_path, None, OUTPUT_FOLDER)

## -------------- API ENDPOINTS -------------- ##

@app.post("/ocr")
async def ocr(
    image: UploadFile = File(...),
    config: OCR_ConfigName = Form(DEFAULT_CONFIG_NAME),
    additional_langs: List[str] = Form([]),
    credentials: HTTPBasicCredentials = Depends(security)
):
    if not authenticate(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    img_path = dump_uploaded_file(image.filename, await image.read(), OUTPUT_FOLDER)
    output_path = perform_ocr(img_path, config, additional_langs)
    
    with open(output_path + '.json', 'r', encoding='utf-8') as f:
        result = json.load(f)
    
    return result

@app.get("/ocr_test")
async def ocr_test(credentials: HTTPBasicCredentials = Depends(security)):
    if not authenticate(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    content = """
    <body>
    <form action="/ocr" enctype="multipart/form-data" method="post">
    <input name="image" type="file" accept="image/*">
    <input type="submit">
    </form>
    </body>
    """
    return HTMLResponse(content=content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

