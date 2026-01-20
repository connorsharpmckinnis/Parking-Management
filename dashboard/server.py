"""
Static File Server for Parking Management Dashboard
Serves static HTML/CSS/JS and proxies API requests to Control Plane
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import httpx
import os

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://control-plane:8000")

app = FastAPI(title="Parking Dashboard")

# Proxy API requests to Control Plane
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_api(path: str, request: Request):
    """Proxy all /api/* requests to the Control Plane."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{CONTROL_PLANE_URL}/{path}"
        
        # Forward query params
        if request.query_params:
            url += f"?{request.query_params}"
        
        # Forward request body for non-GET methods
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        try:
            response = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers={"Content-Type": "application/json"}
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"Content-Type": response.headers.get("content-type", "application/json")}
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Control Plane unavailable: {str(e)}")

# Serve pages at root for clean URLs
@app.get("/")
async def serve_root():
    return FileResponse("static/index.html")

@app.get("/index.html")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/inspector.html")
async def serve_inspector():
    return FileResponse("static/inspector.html")

@app.get("/add-camera.html")
async def serve_add_camera():
    return FileResponse("static/add-camera.html")

@app.get("/locations.html")
async def serve_locations():
    return FileResponse("static/locations.html")

# Mount static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
