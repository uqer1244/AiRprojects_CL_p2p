import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import cv2

# ──────────────────────────────── 경로 설정 ────────────────────────────────
THIS_FILE = Path(__file__).resolve()
SRC_DIR = THIS_FILE.parent if THIS_FILE.parent.name != "core" else THIS_FILE.parent.parent
if SRC_DIR.as_posix() not in sys.path:
    sys.path.append(SRC_DIR.as_posix())

# ──────────────────────────────── 모듈 import ────────────────────────────────
from core.risk_assessor import RiskAssessor
from core.yolo_processor import YOLOProcessor
from communication.websocket_server import WebSocketServer

SHOW = True  # 시각화 활성화 여부


# ──────────────────────────────── 모델 경로 확인 ────────────────────────────────
def resolve_model_path(cli_value: Optional[str]) -> str:
    """
    --model 인자가 없을 때 yolov8n.pt 자동 탐색
    """
    candidates = []
    if cli_value:
        p = Path(cli_value)
        candidates.append(p if p.is_absolute() else Path.cwd() / cli_value)

    core_dir = SRC_DIR / "core"
    candidates += [
        core_dir / "yolov8n.pt",
        SRC_DIR / "yolov8n.pt",
        Path.cwd() / "yolov8n.pt",
    ]

    for c in candidates:
        if c.exists():
            print(f"🧭 Using YOLO model file: {c}")
            return c.as_posix()

    print("🧭 Local model not found, using default yolov8n.pt (auto-download).")
    return "yolov8n.pt"


# ──────────────────────────────── 시각화 함수 ────────────────────────────────
def draw_overlay(frame, tracks, alerts, fps: float, safe_occ_ratio: float):
    """
    프레임 위에 객체 바운딩박스, 경고 텍스트, 안전거리 임계선, 점유율 표시
    """
    # 1️⃣ 바운딩박스
    for det in tracks:
        x1, y1, x2, y2 = map(int, det["bbox"])
        tid = det["id"]
        color = (0, 200, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"ID{tid}", (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # 2️⃣ 경고 표시
    if alerts:
        y = 28
        for a in alerts:
            msg = f'[{a["level"]}] T{a["track_id"]} - {a["reason"]}'
            cv2.putText(frame, msg, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y += 26

    # 3️⃣ FPS 표시
    cv2.putText(frame, f"{fps:.1f} FPS", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # 4️⃣ 안전거리 임계 박스 (하단 중앙)
    h, w = frame.shape[:2]
    frame_area = w * h
    thr_area = frame_area * safe_occ_ratio
    side = int(max(20, thr_area ** 0.5))
    cx = w // 2
    y2 = h - 20
    x1 = max(5, cx - side // 2)
    y1 = max(5, y2 - side)
    cv2.rectangle(frame, (x1, y1), (x1 + side, y2), (50, 220, 50), 2)
    cv2.putText(frame, f"안전거리 임계 (≈{int(safe_occ_ratio * 100)}%)",
                (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 220, 50), 2)

    # 5️⃣ 각 객체 점유율 바
    for det in tracks:
        bx1, by1, bx2, by2 = map(int, det["bbox"])
        occ = ((bx2 - bx1) * (by2 - by1)) / frame_area if frame_area > 0 else 0.0
        bar_h = int((by2 - by1) * min(1.0, occ / safe_occ_ratio))
        bar_x = bx1 - 8
        bar_y = by2 - bar_h
        color = (0, 0, 255) if occ >= safe_occ_ratio else (0, 255, 255)
        cv2.rectangle(frame, (bar_x, by1), (bar_x + 6, by2), (50, 50, 50), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + 6, by2), color, -1)
        cv2.putText(frame, f"{int(occ*100)}%", (bar_x - 38, by2 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


# ──────────────────────────────── 메인 비동기 루프 ────────────────────────────────
async def run(args):
    """
    전체 파이프라인 실행
    1. WebSocket 서버 시작
    2. YOLO 추적 모델 초기화
    3. 위험도 평가 수행
    4. 실시간 프레임 처리 및 경고 방송
    """
    ws_server = WebSocketServer(args.ws_host, args.ws_port)
    asyncio.create_task(ws_server.start())

    model_path = resolve_model_path(args.model)
    yolo = YOLOProcessor(model_path, conf_thres=args.conf)
    assessor = RiskAssessor()

    def results_to_tracks(result):
        """YOLO 결과를 추적 객체 리스트로 변환"""
        tracks = []
        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            ids = boxes.id.cpu().numpy() if boxes.id is not None else None
            cls = boxes.cls.cpu().numpy() if boxes.cls is not None else None
            conf = boxes.conf.cpu().numpy()
            for i, bb in enumerate(xyxy):
                tracks.append({
                    "id": int(ids[i]) if ids is not None else i,
                    "bbox": [float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])],
                    "cls": int(cls[i]) if cls is not None else None,
                    "conf": float(conf[i]),
                })
        return tracks

    last_t = time.time()

    try:
        results = yolo.track_stream(source=args.source)
        for result in results:
            frame = result.orig_img
            if frame is None:
                await asyncio.sleep(0)
                continue

            if assessor._frame_w is None:
                h, w = frame.shape[:2]
                assessor.set_frame_size(w, h)

            tracks = results_to_tracks(result)
            risk = assessor.assess(tracks)
            alerts = risk["alerts"] if risk else []

            # ⚠️ 위험 감지 시 콘솔 + WebSocket 전송
            for a in alerts:
                payload = {
                    "type": "RISK_ALERT",
                    "ts": time.time(),
                    "level": a["level"],
                    "track_id": a["track_id"],
                    "reason": a["reason"],
                    "bbox": a["bbox"],
                }
                print(json.dumps(payload, ensure_ascii=False))
                asyncio.create_task(ws_server.broadcast(json.dumps(payload, ensure_ascii=False)))

            if SHOW:
                fps = 1.0 / max(1e-6, time.time() - last_t)
                last_t = time.time()
                safe_ratio = getattr(RiskAssessor, "SAFE_OCCUPANCY_FOR_WARN1", 0.08)
                draw_overlay(frame, tracks, alerts, fps, safe_ratio)
                cv2.imshow("V2V Risk Monitor", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            await asyncio.sleep(0)

    except Exception as e:
        print(f"[INFO] LoadStreams 실패, 폴백 모드로 전환: {e}")
        cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        if not cap.isOpened():
            raise SystemExit("폴백 모드 카메라 실패")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if assessor._frame_w is None:
                h, w = frame.shape[:2]
                assessor.set_frame_size(w, h)

            result = yolo.model.track(
                source=frame, conf=yolo.conf_thres,
                tracker="bytetrack.yaml", stream=False, verbose=False, persist=True
            )[0]

            tracks = results_to_tracks(result)
            risk = assessor.assess(tracks)
            alerts = risk["alerts"] if risk else []

            for a in alerts:
                payload = {
                    "type": "RISK_ALERT",
                    "ts": time.time(),
                    "level": a["level"],
                    "track_id": a["track_id"],
                    "reason": a["reason"],
                    "bbox": a["bbox"],
                }
                print(json.dumps(payload, ensure_ascii=False))
                asyncio.create_task(ws_server.broadcast(json.dumps(payload, ensure_ascii=False)))

            if SHOW:
                fps = 1.0 / max(1e-6, time.time() - last_t)
                last_t = time.time()
                safe_ratio = getattr(RiskAssessor, "SAFE_OCCUPANCY_FOR_WARN1", 0.08)
                draw_overlay(frame, tracks, alerts, fps, safe_ratio)
                cv2.imshow("V2V Risk Monitor (Fallback)", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            await asyncio.sleep(0)
        cap.release()

    cv2.destroyAllWindows()


# ──────────────────────────────── 실행 시작 ────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, default=None, help="YOLO 모델 경로 또는 이름")
    ap.add_argument("--source", type=str, default="0", help="카메라 인덱스 또는 파일 경로")
    ap.add_argument("--conf", type=float, default=0.25, help="confidence threshold")
    ap.add_argument("--ws_host", type=str, default="0.0.0.0")
    ap.add_argument("--ws_port", type=int, default=8090)
    args = ap.parse_args()

    asyncio.run(run(args))