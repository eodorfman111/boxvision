"""
Kybermart CV Demo — Warehouse Box Detection, Tracking, Counting & Dimension Estimate
Portfolio demonstration: runs on AI-generated warehouse dock footage.
"""

import base64
import json
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import requests
import supervision as sv
from ultralytics import YOLO

warnings.filterwarnings("ignore", category=FutureWarning)  # sv.ByteTrack deprecation noise

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("ROBOFLOW_API_KEY") or open(".env").read().split("=", 1)[1].strip()

BOX_MODEL_PATH = "models/kybermart_box.pt"   # custom YOLO26x, trained on labeled dock footage
CONTEXT_MODEL = "stage-3-bon9u/4"            # forklift, worker, pallets (Roboflow public model)

VIDEO_IN = Path("footage/dock_demo.mp4")
VIDEO_OUT = Path("output/kybermart_demo_annotated.mp4")
STATS_OUT = Path("output/kybermart_stats.json")

BOX_CONF = 0.5
BOX_IOU = 0.4
CONTEXT_CONF = 25

ASSUMED_WORKER_HEIGHT_CM = 173  # avg adult height, used as the single calibration reference
LINE_START = sv.Point(0, 520)
LINE_END = sv.Point(1280, 520)  # roughly across the conveyor, tuned for this clip's framing

CLASS_COLORS = {
    "cardboard-box": sv.Color.from_hex("#3ddc84"),
    "forklift": sv.Color.from_hex("#ff9800"),
    "worker": sv.Color.from_hex("#4fc3f7"),
    "Pallets": sv.Color.from_hex("#ce93d8"),
}
NAME_TO_ID = {"cardboard-box": 0, "forklift": 1, "worker": 2, "Pallets": 3}


def infer(model_id: str, frame_bytes: bytes, confidence: int) -> list[dict]:
    b64 = base64.b64encode(frame_bytes).decode()
    resp = requests.post(
        f"https://detect.roboflow.com/{model_id}",
        params={"api_key": API_KEY, "confidence": confidence},
        data=b64,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("predictions", [])


def infer_boxes_local(box_model: YOLO, frame: np.ndarray) -> sv.Detections:
    result = box_model.predict(frame, conf=BOX_CONF, iou=BOX_IOU, verbose=False)[0]
    dets = sv.Detections.from_ultralytics(result)
    return dets


def predictions_to_detections(box_dets: sv.Detections, context_preds: list[dict]) -> sv.Detections:
    boxes, class_ids, class_names, confs = [], [], [], []
    for xyxy, conf in zip(box_dets.xyxy, box_dets.confidence):
        boxes.append(list(xyxy))
        class_ids.append(NAME_TO_ID["cardboard-box"])
        class_names.append("cardboard-box")
        confs.append(float(conf))
    for p in context_preds:
        name = p["class"]
        if name not in NAME_TO_ID:
            continue
        boxes.append([p["x"] - p["width"] / 2, p["y"] - p["height"] / 2, p["x"] + p["width"] / 2, p["y"] + p["height"] / 2])
        class_ids.append(NAME_TO_ID[name])
        class_names.append(name)
        confs.append(p["confidence"])

    if not boxes:
        return sv.Detections.empty()

    dets = sv.Detections(
        xyxy=np.array(boxes, dtype=float),
        confidence=np.array(confs, dtype=float),
        class_id=np.array(class_ids, dtype=int),
    )
    dets.data["class_name"] = np.array(class_names)
    return dets


def estimate_dims_cm(dets: sv.Detections, pixels_per_cm: float | None):
    """Approximate real-world W x H per detection using the worker-height calibration.
    Returns a list of strings aligned with dets, empty string where not applicable."""
    labels = []
    for i in range(len(dets)):
        name = dets.data["class_name"][i]
        if name != "cardboard-box" or not pixels_per_cm:
            labels.append("")
            continue
        x1, y1, x2, y2 = dets.xyxy[i]
        w_cm = (x2 - x1) / pixels_per_cm
        h_cm = (y2 - y1) / pixels_per_cm
        labels.append(f"~{w_cm:.0f}x{h_cm:.0f}cm")
    return labels


def main():
    box_model = YOLO(BOX_MODEL_PATH)
    cap = cv2.VideoCapture(str(VIDEO_IN))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    VIDEO_OUT.parent.mkdir(exist_ok=True)
    writer = cv2.VideoWriter(str(VIDEO_OUT), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    # IOU-based tracking (ByteTrack/SORT) is unreliable for identity persistence across a dense pile
    # of 40+ overlapping, mostly-stationary boxes -- no threshold tuning fixes that cleanly, it's the
    # wrong tool for that sub-problem. Still used for the visible per-box trace/ID in the video overlay
    # and for line-crossing counts, where objects are more isolated; NOT used as a "boxes ever seen" stat.
    tracker = sv.ByteTrack(frame_rate=int(fps))
    line_zone = sv.LineZone(start=LINE_START, end=LINE_END, triggering_anchors=[sv.Position.CENTER])

    box_annotator = sv.BoxAnnotator(color=sv.ColorPalette(list(CLASS_COLORS.values())), thickness=1)
    label_annotator = sv.LabelAnnotator(color=sv.ColorPalette(list(CLASS_COLORS.values())), text_scale=0.28, text_thickness=1, text_padding=2)
    trace_annotator = sv.TraceAnnotator(color=sv.ColorPalette(list(CLASS_COLORS.values())), thickness=1, trace_length=20)
    line_annotator = sv.LineZoneAnnotator(thickness=2, text_scale=0.6, color=sv.Color.WHITE)

    frame_idx = 0
    seen_box_ids = set()
    peak_concurrent_boxes = 0
    box_dim_samples = []  # (w_cm, h_cm) for boxes seen with a valid calibration
    last_pixels_per_cm = None

    with ThreadPoolExecutor(max_workers=1) as pool:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1

            ok_enc, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buf.tobytes()

            # context model (forklift/worker) hits the Roboflow API concurrently
            # while the custom box model runs locally on this thread
            fut_ctx = pool.submit(infer, CONTEXT_MODEL, frame_bytes, CONTEXT_CONF)
            box_dets = infer_boxes_local(box_model, frame)
            ctx_preds = fut_ctx.result()

            dets = predictions_to_detections(box_dets, ctx_preds)
            dets = tracker.update_with_detections(dets)

            # calibrate pixels-per-cm off any worker detected this frame
            worker_mask = dets.data.get("class_name", np.array([])) == "worker"
            if worker_mask.any():
                worker_heights_px = (dets.xyxy[worker_mask][:, 3] - dets.xyxy[worker_mask][:, 1])
                last_pixels_per_cm = float(np.median(worker_heights_px)) / ASSUMED_WORKER_HEIGHT_CM

            line_zone.trigger(dets)

            box_mask = dets.data.get("class_name", np.array([])) == "cardboard-box"
            concurrent_boxes = int(box_mask.sum())
            peak_concurrent_boxes = max(peak_concurrent_boxes, concurrent_boxes)
            if dets.tracker_id is not None and box_mask.any():
                seen_box_ids.update(int(t) for t in dets.tracker_id[box_mask])

            dim_labels = estimate_dims_cm(dets, last_pixels_per_cm)
            for i in range(len(dets)):
                name = dets.data["class_name"][i]
                if name == "cardboard-box" and dim_labels[i]:
                    box_dim_samples.append(dim_labels[i])

            labels = []
            for i in range(len(dets)):
                name = dets.data["class_name"][i]
                if name == "cardboard-box":
                    # no per-box ID here -- identity churns too fast in this dense a pile to show honestly
                    labels.append(dim_labels[i] if dim_labels[i] else "box")
                else:
                    tid = dets.tracker_id[i] if dets.tracker_id is not None else -1
                    labels.append(f"#{tid} {name}")

            movable_mask = dets.data.get("class_name", np.array([])) != "cardboard-box"
            annotated = frame.copy()
            annotated = trace_annotator.annotate(annotated, dets[movable_mask])
            annotated = box_annotator.annotate(annotated, dets)
            annotated = label_annotator.annotate(annotated, dets, labels=labels)
            annotated = line_annotator.annotate(annotated, line_zone)

            overlay = annotated.copy()
            cv2.rectangle(overlay, (10, 10), (330, 90), (20, 20, 20), -1)
            cv2.addWeighted(overlay, 0.55, annotated, 0.45, 0, annotated)
            cv2.putText(annotated, f"Boxes in frame: {concurrent_boxes}  (peak {peak_concurrent_boxes})", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(annotated, f"Line count  in:{line_zone.in_count}  out:{line_zone.out_count}", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(annotated, f"Frame {frame_idx}/{total_frames}", (20, 82),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

            writer.write(annotated)
            print(f"frame {frame_idx}/{total_frames}  boxes_now={concurrent_boxes}  peak={peak_concurrent_boxes}  distinct_ids_seen={len(seen_box_ids)}")

    cap.release()
    writer.release()

    stats = {
        "total_frames": total_frames,
        "fps": fps,
        "peak_concurrent_boxes": peak_concurrent_boxes,
        "distinct_box_ids_seen": len(seen_box_ids),
        "line_in_count": int(line_zone.in_count),
        "line_out_count": int(line_zone.out_count),
        "sample_dimension_estimates_cm": box_dim_samples[:20],
        "note": "Dimension estimates are approximate, calibrated off a single assumed worker height (173cm) per frame — a real deployment would use a depth camera or fixed calibration target for production accuracy.",
    }
    STATS_OUT.write_text(json.dumps(stats, indent=2))
    print("\nDone.")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
