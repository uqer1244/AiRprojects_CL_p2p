# risk_assessor.py
from collections import deque
from typing import List, Dict, Any, Optional, Tuple

def area_xyxy(b):
    x1, y1, x2, y2 = b
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)

def center_xyxy(b):
    x1, y1, x2, y2 = b
    return (0.5 * (x1 + x2), 0.5 * (y1 + y2))

def point_in_rect(pt, rect):
    x, y = pt
    x1, y1, x2, y2 = rect
    return (x1 <= x <= x2) and (y1 <= y <= y2)

def make_safety_zone(w: int, h: int,
                     width_ratio: float = 0.40,
                     height_ratio: float = 0.35,
                     bottom_margin_ratio: float = 0.05):
    sw = int(w * width_ratio)
    sh = int(h * height_ratio)
    cx = w // 2
    bottom = h - int(h * bottom_margin_ratio)
    x1 = int(cx - sw // 2)
    x2 = int(cx + sw // 2)
    y2 = bottom
    y1 = max(0, y2 - sh)
    return [x1, y1, x2, y2]

class _TrackState:
    def __init__(self, track_id: int):
        self.id = track_id
        self.area_hist = deque(maxlen=64)
        self.warn1_sent = False
        self.warn2_sent = False
        self.warn3_sent = False
        self.last_bbox = None

class RiskAssessor:
    """
    경고1: 안전구역(하단 중앙 사각형) 안에 track 중심이 들어오면
    경고2: 최근 5프레임 대비 면적 20% 이상 증가 AND (5중 4프레임 이상 증가 추세)
    경고3: 경고2 충족 상태에서 현재 bbox 면적이 프레임의 50% 이상
    """
    GROWTH_WINDOW = 5
    GROWTH_TOTAL_RATIO = 0.20
    OCCUPANCY_RATIO_FOR_WARN3 = 0.50

    SAFETY_ZONE_W = 0.40
    SAFETY_ZONE_H = 0.35
    SAFETY_ZONE_BOTTOM_MARGIN = 0.05

    def __init__(self):
        self._frame_w = None
        self._frame_h = None
        self._safety_rect = None
        self._tracks: Dict[int, _TrackState] = {}

    def set_frame_size(self, w: int, h: int):
        """경고3와 안전구역 계산을 위해 매 프레임 혹은 최초 1회 호출."""
        if (self._frame_w, self._frame_h) != (w, h):
            self._frame_w, self._frame_h = w, h
            self._safety_rect = make_safety_zone(
                w, h,
                self.SAFETY_ZONE_W,
                self.SAFETY_ZONE_H,
                self.SAFETY_ZONE_BOTTOM_MARGIN
            )

    def reset_track(self, track_id: int):
        self._tracks[track_id] = _TrackState(track_id)

    def _ensure_track(self, track_id: int) -> _TrackState:
        if track_id not in self._tracks:
            self.reset_track(track_id)
        return self._tracks[track_id]

    def assess(self, detections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        detections: [{"id": int, "bbox":[x1,y1,x2,y2], "cls": int|str|None, "conf": float|None}]
        return: {"alerts":[{level, track_id, reason, bbox}], "safety_rect":[x1,y1,x2,y2]} | None
        """
        if self._frame_w is None or self._frame_h is None:
            # 프레임 크기 설정이 안되었으면 판단 불가
            return None

        alerts = []
        frame_area = float(self._frame_w * self._frame_h)

        for det in detections:
            tid = int(det["id"])
            bbox = det["bbox"]
            tr = self._ensure_track(tid)
            tr.last_bbox = bbox

            # 면적 히스토리 갱신
            tr.area_hist.append(area_xyxy(bbox))

            # 경고1: 안전구역 진입
            if not tr.warn1_sent and self._safety_rect is not None:
                cx, cy = center_xyxy(bbox)
                if point_in_rect((cx, cy), self._safety_rect):
                    alerts.append({
                        "level": "경고1",
                        "track_id": tid,
                        "reason": "안전구역 진입",
                        "bbox": bbox
                    })
                    tr.warn1_sent = True

            # 경고2: 5프레임 누적 20%↑ + 상승 추세
            if not tr.warn2_sent and len(tr.area_hist) >= (self.GROWTH_WINDOW + 1):
                a_now = tr.area_hist[-1]
                a_prev = tr.area_hist[-1 - self.GROWTH_WINDOW]
                total_growth = ((a_now - a_prev) / a_prev) if a_prev > 0 else 0.0

                inc_count = 0
                # window 내 증가 프레임 카운트(5중 4 이상)
                for k in range(1, self.GROWTH_WINDOW + 1):
                    if tr.area_hist[-k] > tr.area_hist[-k-1]:
                        inc_count += 1
                mostly_increasing = (inc_count >= (self.GROWTH_WINDOW - 1))

                if total_growth >= self.GROWTH_TOTAL_RATIO and mostly_increasing:
                    alerts.append({
                        "level": "경고2",
                        "track_id": tid,
                        "reason": f"5프레임 누적 +{int(total_growth*100)}% 증가",
                        "bbox": bbox
                    })
                    tr.warn2_sent = True

            # 경고3: 경고2 충족 + 화면 50% 점유
            if tr.warn2_sent and not tr.warn3_sent:
                cur_area = tr.area_hist[-1]
                if frame_area > 0 and (cur_area / frame_area) >= self.OCCUPANCY_RATIO_FOR_WARN3:
                    alerts.append({
                        "level": "경고3",
                        "track_id": tid,
                        "reason": "화면 50% 점유",
                        "bbox": bbox
                    })
                    tr.warn3_sent = True

        if alerts:
            return {"alerts": alerts, "safety_rect": self._safety_rect}
        return None