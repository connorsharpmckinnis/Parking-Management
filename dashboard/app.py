import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
import cv2
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Configuration
CONTROL_PLANE_URL = "http://control-plane:8000"
APP_VERSION = "0.8.1"

st.set_page_config(
    page_title="Parking Management Dashboard",
    page_icon="🚗",
    layout="wide"
)

def format_timestamp(ts_str):
    """Converts UTC ISO timestamp to EST/New York for display."""
    if not ts_str:
        return "Never"
    try:
        if isinstance(ts_str, datetime):
            dt = ts_str
        else:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            
        est_dt = dt.astimezone(ZoneInfo("America/New_York"))
        return est_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ts_str

def get_cameras():
    try:
        response = requests.get(f"{CONTROL_PLANE_URL}/cameras", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch cameras: {e}")
    return []

def get_events():
    try:
        response = requests.get(f"{CONTROL_PLANE_URL}/events", params={"limit": 100}, timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch events: {e}")
    return []

def capture_frame(stream_url):
    """Captures a single frame from the RTSP stream."""
    try:
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
             return None, "Could not open stream"
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None, "Failed to read frame"
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame), None
    except Exception as e:
        return None, str(e)

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Live Monitor", "Data Inspector", "Add Camera"])

if page != "Add Camera" and st.sidebar.button("Refresh Data"):
    st.rerun()

# --- Page: Live Monitor ---
def show_live_monitor():
    st.title("📹 Live Camera Monitor")
    st.caption("Auto-refreshing every 10 seconds")

    cameras = get_cameras()
    
    if not cameras:
        st.warning("No cameras found or Control Plane offline.")
    else:
        # Metrics Row
        total_cams = len(cameras)
        active_cams = sum(1 for c in cameras if c.get('status') == 'healthy')
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cameras", total_cams)
        col2.metric("Active Streams", active_cams, delta=f"{active_cams/total_cams:.0%}" if total_cams > 0 else "")
        col3.metric("System Status", "Online" if total_cams > 0 else "Offline")

        st.markdown("---")
        
        # Camera Grid
        cols = st.columns(3)
        for idx, cam in enumerate(cameras):
            with cols[idx % 3]:
                status_color = "🟢" if cam.get('status') == 'healthy' else "🔴"
                desired = cam.get('desired_state', 'stopped')
                is_running = desired == 'running'
                
                with st.container():
                    st.subheader(f"{status_color} {cam['name']}")
                    st.caption(f"ID: {cam['id']}")
                    st.text(f"Location: {cam.get('location', 'N/A')}")
                    st.text(f"State: {'Running' if is_running else 'Stopped'}")
                    
                    last_event = cam.get('last_event_time')
                    st.text(f"Last Update: {format_timestamp(last_event)}")
                    
                    with st.expander("Manage"):
                        cam_id = cam['id']
                        if is_running:
                            if st.button("⏹ Stop", key=f"stop_{cam_id}"):
                                res = requests.patch(f"{CONTROL_PLANE_URL}/cameras/{cam_id}", 
                                                     json={"desired_state": "stopped"}, timeout=5)
                                if res.ok:
                                    st.success("Stopping...")
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {res.text}")
                        else:
                            if st.button("▶ Start", key=f"start_{cam_id}"):
                                res = requests.patch(f"{CONTROL_PLANE_URL}/cameras/{cam_id}", 
                                                     json={"desired_state": "running"}, timeout=5)
                                if res.ok:
                                    st.success("Starting...")
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {res.text}")
                        
                        st.markdown("---")
                        if st.button("🗑 Delete Permanently", key=f"del_{cam_id}", type="secondary"):
                            res = requests.delete(f"{CONTROL_PLANE_URL}/cameras/{cam_id}", timeout=5)
                            if res.status_code == 204:
                                st.success("Deleted!")
                                st.rerun()
                            else:
                                 st.error(f"Failed: {res.text}")
    
    st.markdown("---")
    st.caption(f"v{APP_VERSION} | Parking Management System")

# --- Page: Data Inspector ---
def show_data_inspector():
    st.title("🗄️ Data Inspector")
    st.caption("Auto-refreshing every 10 seconds")
    
    tab1, tab2 = st.tabs(["Cameras", "Occupancy Events (Raw)"])
    
    with tab1:
        st.subheader("Registered Cameras")
        cameras = get_cameras()
        if cameras:
            df_cams = pd.DataFrame(cameras)
            if 'last_event_time' in df_cams.columns:
                df_cams['last_event_time'] = df_cams['last_event_time'].apply(format_timestamp)
            st.dataframe(df_cams, use_container_width=True)
        else:
            st.info("No data available.")

    with tab2:
        st.subheader("Recent Occupancy Events")
        events = get_events()
        if events:
            df_events = pd.DataFrame(events)
            if 'timestamp' in df_events.columns:
                 df_events['timestamp'] = df_events['timestamp'].apply(format_timestamp)
            st.dataframe(df_events, use_container_width=True)
        else:
            st.info("No occupancy events recorded yet.")
    
    st.markdown("---")
    st.caption(f"v{APP_VERSION} | Parking Management System")

# --- Page: Add Camera ---
def show_add_camera():
    st.title("➕ Add Smart Camera")
    
    with st.form("camera_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Camera Name", "New Camera")
            location = st.text_input("Location", "Main Entry")
        with col2:
            ip_addr = st.text_input("IP Address", "10.9.4.215")
            user = st.text_input("Username", "connor")
            pwd = st.text_input("Password", type="password")
            connection_type = st.selectbox("Connection Type", ["fiber", "edge"])
            
            stream_url = f"http://{user}:{pwd}@{ip_addr}/axis-cgi/media.cgi?container=mp4&video=1&audio=0&videocodec=h264"
            st.caption(f"Final URL: http://{user}:{'*' * len(pwd)}@{ip_addr}/...")
        
        st.markdown("### Detection Zones")
        st.info("Enter details above and click 'Capture Frame' to define parking spots.")
        
        image_state = st.session_state.get('last_capture', None)
        capture_btn = st.form_submit_button("Capture Frame from Stream")
        
        if capture_btn and stream_url:
            with st.spinner("Connecting to camera..."):
                img, err = capture_frame(stream_url)
                if img:
                    st.session_state['last_capture'] = img
                    st.session_state['orig_size'] = img.size
                    image_state = img
                    st.success("Frame captured!")
                else:
                    st.error(f"Capture failed: {err}")

    # Drawing State Init
    if 'drawing_points' not in st.session_state: st.session_state['drawing_points'] = []
    if 'zones' not in st.session_state: st.session_state['zones'] = []
    if 'orig_size' not in st.session_state: st.session_state['orig_size'] = (640, 480)

    def get_canvas_json(zones):
        objects = []
        for zone in zones:
            pts = zone['points']
            path_data = [["M", pts[0][0], pts[0][1]], ["L", pts[1][0], pts[1][1]], ["L", pts[2][0], pts[2][1]], ["L", pts[3][0], pts[3][1]], ["z"]]
            objects.append({"type": "path", "path": path_data, "fill": "rgba(0, 255, 0, 0.3)", "stroke": "#00FF00", "strokeWidth": 2})
        return {"objects": objects}

    if image_state:
        orig_w, orig_h = st.session_state['orig_size']
        scale_x, scale_y = orig_w / 640, orig_h / 480

        st.markdown(f"**Step 2: Define Parking Zones**")
        st.write(f"Click the 4 corners of a spot. Completed: **{len(st.session_state['zones'])}**")
        
        canvas_key = f"canvas_stable_{len(st.session_state['zones'])}"
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 0, 0.3)", stroke_width=2, stroke_color="#FFFF00",
            background_image=image_state, initial_drawing=get_canvas_json(st.session_state['zones']),
            update_streamlit=True, height=480, width=640, drawing_mode="point", point_display_radius=5, key=canvas_key,
        )
        
        if canvas_result.json_data is not None:
            raw_objects = canvas_result.json_data["objects"]
            user_points = [o for o in raw_objects if o.get("type") == "circle" and o.get("radius") == 5]
            current_canvas_pts = [[int(o["left"]+5), int(o["top"]+5)] for o in user_points]
            
            if len(current_canvas_pts) != len(st.session_state['drawing_points']):
                st.session_state['drawing_points'] = current_canvas_pts
                if len(st.session_state['drawing_points']) >= 4:
                    st.session_state['zones'].append({"points": st.session_state['drawing_points'][:4]})
                    st.session_state['drawing_points'] = []
                    st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Undo Last Point") and st.session_state['drawing_points']:
                st.session_state['drawing_points'] = []
                st.rerun()
        with col2:
            if st.button("Clear All"):
                st.session_state['zones'] = []; st.session_state['drawing_points'] = []
                st.rerun()

        st.markdown("---")
        if st.button("🚀 Register Camera", use_container_width=True):
            if not st.session_state['zones']:
                st.warning("Define at least one zone.")
            else:
                scaled_zones = []
                for zone in st.session_state['zones']:
                    scaled_pts = [[int(p[0]*scale_x), int(p[1]*scale_y)] for p in zone['points']]
                    scaled_zones.append({"points": scaled_pts})

                payload = {
                    "name": name, "location": location, "stream_url": stream_url,
                    "connection_type": connection_type, "desired_state": "running",
                    "geometry": scaled_zones
                }
                
                try:
                    res = requests.post(f"{CONTROL_PLANE_URL}/cameras", json=payload, timeout=5)
                    if res.status_code == 201:
                        st.success("Registered!")
                        st.balloons()
                        st.session_state['zones'] = []; st.session_state['drawing_points'] = []
                    else: st.error(f"Failed: {res.text}")
                except Exception as e: st.error(f"Error: {e}")
    
    st.markdown("---")
    st.caption(f"v{APP_VERSION} | Parking Management System")

# --- Routing Logic ---
if page == "Live Monitor":
    show_live_monitor()
elif page == "Data Inspector":
    show_data_inspector()
elif page == "Add Camera":
    show_add_camera()

# --- Unified Auto-Refresh ---
if page in ["Live Monitor", "Data Inspector"]:
    time.sleep(10)
    st.rerun()
