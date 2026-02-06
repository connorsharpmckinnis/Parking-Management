import cv2
import argparse
from ultralytics import YOLO, RTDETR
import math
import numpy as np

try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except ImportError:
    SAHI_AVAILABLE = False


def label_image(img, text):
    labeled = img.copy()
    cv2.rectangle(labeled, (0, 0), (labeled.shape[1], 35), (0, 0, 0), -1)
    cv2.putText(
        labeled,
        text,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )
    return labeled

def make_grid(images):
    if not images:
        raise RuntimeError("No annotated images to display (image list is empty)")
    n = len(images)
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)

    h, w, _ = images[0].shape
    grid = []

    for r in range(rows):
        row_imgs = []
        for c in range(cols):
            idx = r * cols + c
            if idx < n:
                row_imgs.append(images[idx])
            else:
                row_imgs.append(
                    255 * (images[0] * 0 + 1).astype(images[0].dtype)
                )
        grid.append(cv2.hconcat(row_imgs))

    return cv2.vconcat(grid)

def scale_to_fit(image, max_width=1600, max_height=900):
    h, w = image.shape[:2]
    scale = min(max_width / w, max_height / h, 1.0)
    if scale < 1.0:
        image = cv2.resize(image, (int(w * scale), int(h * scale)))
    return image

def main():
    parser = argparse.ArgumentParser("YOLO Multi-Model Comparison")
    parser.add_argument("--image", required=True)
    parser.add_argument("--models", nargs="+", required=True,
                        help="List of YOLO model paths")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--classes", nargs="*", type=int, default=None)
    parser.add_argument("--device", default=None)

    parser.add_argument("--sahi", action="store_true",
                        help="Enable SAHI sliced inference")
    parser.add_argument("--tile", type=int, default=640,
                        help="SAHI slice size in pixels")
    parser.add_argument("--overlap", type=float, default=0.25,
                        help="SAHI overlap ratio")

    args = parser.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        raise RuntimeError("Failed to load image")

    annotated_images = []

    for model_path in args.models:
        print(f"Running inference with {model_path}...")
        
        

        if args.sahi:
            if not SAHI_AVAILABLE:
                raise RuntimeError("SAHI requested but not installed")

            sahi_model = AutoDetectionModel.from_pretrained(
                model_type="ultralytics",
                model_path=model_path,
                confidence_threshold=args.conf,
                device=args.device
            )

            result = get_sliced_prediction(
                image,
                sahi_model,
                slice_height=args.tile,
                slice_width=args.tile,
                overlap_height_ratio=args.overlap,
                overlap_width_ratio=args.overlap,
                verbose=0
            )

            annotated = image.copy()
            for obj in result.object_prediction_list:
                if args.classes is not None and obj.category.id not in args.classes:
                    continue

                if "-seg" in model_path and hasattr(obj, 'mask') and obj.mask is not None:
                    # Draw polygon for SAHI if mask is available
                    # SAHI's mask.full_mask is a binary mask of the whole image
                    # We can find contours to draw the polygon
                    mask = obj.mask.full_mask
                    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(annotated, contours, -1, (0, 255, 0), 2)
                else:
                    bbox = obj.bbox
                    x1, y1, x2, y2 = map(int, [bbox.minx, bbox.miny, bbox.maxx, bbox.maxy])
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 0, 0), 2)

            count = len(result.object_prediction_list)

        else:
            # define model with RT-DETR if that's hte model, otherwise it'll be YOLO
            if model_path.startswith("rtdetr"):
                model = RTDETR(model_path)
            else:
                model = YOLO(model_path)
                
            results = model.predict(
                source=image,
                conf=args.conf,
                classes=args.classes,
                device=args.device,
                verbose=False
            )

            res = results[0]
            if "-seg" in model_path and res.masks is not None:
                # Use plot with boxes=False to show only the segmentation polygons/masks
                annotated = res.plot(line_width=1, font_size=12, boxes=False)
                count = len(res.masks)
            else:
                annotated = res.plot(line_width=1, font_size=12)
                count = len(res.boxes)

        label = model_path
        if args.sahi:
            label += f" | SAHI {args.tile}px @ {args.overlap}"

        annotated = label_image(annotated, label)
        annotated_images.append(annotated)

        print(f"  → {count} detections (SAHI = {args.sahi})")

    grid = make_grid(annotated_images)

    grid = scale_to_fit(grid)
    cv2.namedWindow("YOLO Model Comparison", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        "YOLO Model Comparison",
        cv2.WND_PROP_ASPECT_RATIO,
        cv2.WINDOW_KEEPRATIO
    )
    cv2.imshow("YOLO Model Comparison", grid)
    print("Press any key to exit.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
