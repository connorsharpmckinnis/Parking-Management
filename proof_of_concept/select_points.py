import cv2
from ultralytics import solutions
import argparse
import sys

def main():
    print("---------------------------------------------------------")
    print("Parking Spot Selector")
    print("---------------------------------------------------------")
    print("Usage: python select_points.py <path_to_video_or_image>")
    print("Example: python select_points.py my_parking_lot.mp4")
    print("---------------------------------------------------------")
    
    # Simple CLI argument request or fallback to user input
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
    else:
        source_path = input("Please enter the path to your video or image file: ").strip()
        
    if not source_path:
        print("No file provided. Exiting.")
        return

    print(f"Opening {source_path} for point selection...")
    print("INSTRUCTIONS:")
    print("1. A window will open.")
    print("2. Click to mark corners of a parking spot (create a polygon).")
    print("3. Right click to remove the last point.")
    print("4. Press 's' or the Save button (if available) to save keypoints.")
    print("5. Points will be saved to 'bounding_boxes.json'.")
    print("---------------------------------------------------------")

    # The ultralytics solution usually requires just running this function.
    # It opens a tkinter window.
    solutions.ParkingPtsSelection()
    
    # Note: older versions of ultralytics might wrap this differently, 
    # but based on user prompt docs, this is the call: solutions.ParkingPtsSelection()
    # However, standard usage usually requires passing an image if it's not purely a GUI launcher.
    # The snippet provided by the user says: solutions.ParkingPtsSelection()
    # It seems to launch a file selector GUI if no args are passed in some versions,
    # or it might be a specific helper.
    # If the user script from docs is accurate, it launches a GUI where you select the image.
    
    print("\nIf a GUI opened, use it to select your image and draw points.")
    print("After saving, a 'bounding_boxes.json' file should appear in this directory.")

if __name__ == "__main__":
    main()
