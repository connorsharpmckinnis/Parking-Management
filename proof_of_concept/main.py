from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import cv2
import sys
import db
from monitor import ParkingMonitor

app = FastAPI()

# Mount static files if needed (for css)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Global Monitor Instance
monitor = None

@app.on_event("startup")
def startup_event():
    db.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logs = db.get_recent_logs(20)
    monitor_running = monitor.running if monitor else False
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "logs": logs, 
        "running": monitor_running
    })

@app.post("/configure")
async def configure_camera(
    ip: str = Form(...), 
    username: str = Form(""), 
    password: str = Form(""),
    interval: int = Form(5)
):
    global monitor
    
    # Construct URL based on user example:
    # http://connor:@LinuxSucks1873!@10.9.4.215/axis-cgi/media.cgi?container=mp4&video=1&audio=0&videocodec=h264
    # Note: URL encoding might be needed for special chars in password. 
    # For simplicity, we stick to f-string insertion as requested.
    
    if username and password:
        # Check if @ is in password, might cause issues if not escaped, but sticking to simple construction.
        url = f"http://{username}:{password}@{ip}/axis-cgi/media.cgi?container=mp4&video=1&audio=0&videocodec=h264"
    else:
        url = ip # Fallback if they provide full URL or no auth
        
    # Stop existing
    if monitor:
        monitor.stop()
        
    monitor = ParkingMonitor(stream_url=url, interval=interval)
    monitor.start()
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/stop")
async def stop_monitoring():
    global monitor
    if monitor:
        monitor.stop()
    return RedirectResponse(url="/", status_code=303)

@app.get("/video_feed")
def video_feed():
    if not monitor or not monitor.running:
        return "Not running"
        
    def iter_frames():
        while True:
            if monitor:
                frame = monitor.get_frame()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
    return StreamingResponse(iter_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
