from fastapi import FastAPI, UploadFile
import shutil
from app.services.analyzer import analyze_audio

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze(file: UploadFile):
    path = f"temp_{file.filename}"
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = analyze_audio(path)
    return result
