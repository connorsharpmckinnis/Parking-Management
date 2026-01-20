from fastapi import FastAPI, Request, HTTPException
import httpx
import os

app = FastAPI(title="Telemetry Ingest Service")

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://control-plane:8000")

@app.post("/telemetry/{camera_id}")
async def proxy_telemetry(camera_id: str, request: Request):
    """
    In the future, this service will handle massive loads, 
    validation, and async queuing to the database.
    For the POC, it simply proxies to the Control Plane.
    """
    body = await request.json()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{CONTROL_PLANE_URL}/cameras/{camera_id}/event",
                json=body,
                timeout=5.0
            )
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Control Plane unreachable: {e}")

@app.get("/health")
async def health():
    return {"status": "ingest service online"}
