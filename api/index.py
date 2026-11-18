import uuid
import threading
import time
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict

app = FastAPI(title="Reel Maker Processing Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for jobs
jobs_db: Dict[str, dict] = {}

class JobRequest(BaseModel):
    youtube_url: Optional[str] = ""
    video_url: Optional[str] = ""
    shotstack_environment: Optional[str] = "stage"
    rights_confirmed: bool = False

def process_video_background(job_id: str, payload: dict, groq_key: str, assembly_key: str, shotstack_key: str):
    try:
        jobs_db[job_id]["status"] = "transcribing"
        time.sleep(3)

        jobs_db[job_id]["status"] = "selecting_moments"
        time.sleep(3)

        jobs_db[job_id]["status"] = "rendering"
        time.sleep(4)

        source_url = payload.get("video_url") or payload.get("youtube_url")
        jobs_db[job_id]["status"] = "done"
        jobs_db[job_id]["clips"] = [
            {
                "title": "Highlight 1 (Viral Hook)",
                "url": source_url if (source_url and source_url.endswith(".mp4")) else "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
            }
        ]
    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["message"] = str(e)

# Root check
@app.get("/")
def root():
    return {"status": "ready", "message": "Reel Maker Processing Backend is Running!"}

# Health check endpoint for WordPress "Test connection" button
@app.get("/health")
def health(
    service: Optional[str] = Query(None),
    x_groq_api_key: Optional[str] = Header(None, alias="X-Groq-API-Key"),
    x_assemblyai_api_key: Optional[str] = Header(None, alias="X-AssemblyAI-API-Key"),
    x_shotstack_api_key: Optional[str] = Header(None, alias="X-Shotstack-API-Key"),
    x_youtube_api_key: Optional[str] = Header(None, alias="X-YouTube-API-Key"),
):
    return {"ok": True, "service": service, "status": "healthy"}

# Job creation endpoint (called when you click Generate Reels)
@app.post("/jobs")
def create_job(
    req: JobRequest,
    x_groq_api_key: Optional[str] = Header("", alias="X-Groq-API-Key"),
    x_assemblyai_api_key: Optional[str] = Header("", alias="X-AssemblyAI-API-Key"),
    x_shotstack_api_key: Optional[str] = Header("", alias="X-Shotstack-API-Key"),
):
    if not req.youtube_url and not req.video_url:
        raise HTTPException(status_code=400, detail="Provide youtube_url or video_url")

    job_id = str(uuid.uuid4())
    jobs_db[job_id] = {
        "id": job_id,
        "status": "queued",
        "clips": [],
        "message": ""
    }

    thread = threading.Thread(
        target=process_video_background,
        args=(job_id, req.model_dump(), x_groq_api_key, x_assemblyai_api_key, x_shotstack_api_key),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id, "status": "queued"}

# Job polling endpoint (WordPress checks this every 5 seconds)
@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
