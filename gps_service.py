# # src/gps_service.py
# import asyncio
# import json
# from flask import Flask, request
# import websockets
# import threading

# # --- 설정 ---
# # main.py가 실행 중인 서버의 주소 (같은 컴퓨터면 localhost)
# MAIN_SERVER_URI = "ws://localhost:8090" 
# # 아이폰 데이터 수신을 위한 Flask 서버 설정
# FLASK_PORT = 8000
# FLASK_HOST = "0.0.0.0"

# # --- 실시간 데이터 저장 ---
# latest_gps_position = { "latitude": None, "longitude": None }

# # --- Flask 서버 (아이폰 데이터 수신용) ---
# app = Flask(__name__)

# @app.route("/data", methods=["POST"])
# def data():
#     """아이폰의 Sensor Logger 앱에서 location 데이터를 수신합니다."""
#     global latest_gps_position
#     if request.method == "POST":
#         try:
#             payload = json.loads(request.data).get('payload', [])
#             for d in payload:
#                 if d.get("name") == "location":
#                     values = d.get("values", {})
#                     lat, lon = values.get('latitude'), values.get('longitude')
#                     if lat is not None and lon is not None:
#                         latest_gps_position = { "latitude": lat, "longitude": lon }
#                         print(f"📍 GPS 수신: {latest_gps_position}")
#         except Exception as e:
#             print(f"데이터 처리 중 오류 발생: {e}")
#     return "success"

# # --- WebSocket 클라이언트 (main.py 서버로 데이터 전송) ---
# async def run_websocket_client():
#     """1초마다 메인 서버로 최신 GPS 좌표를 전송합니다."""
#     while True:
#         try:
#             async with websockets.connect(MAIN_SERVER_URI) as websocket:
#                 print(f"✅ 메인 서버에 연결됨: {MAIN_SERVER_URI}")
#                 while True:
#                     if latest_gps_position["latitude"] is not None:
#                         message = json.dumps({
#                             "type": "GPS_POSITION_UPDATE",
#                             "payload": latest_gps_position
#                         })
#                         await websocket.send(message)
#                         print(f"-> 메인 서버로 GPS 전송: {message}")
#                     await asyncio.sleep(1) # 1초 간격
#         except Exception:
#             print(f"메인 서버 연결 실패. 5초 후 재시도...")
#             await asyncio.sleep(5)

# # --- 메인 실행 로직 ---
# if __name__ == '__main__':
#     # 1. 별도 스레드에서 WebSocket 클라이언트 실행
#     def run_async_loop():
#         asyncio.run(run_websocket_client())
    
#     client_thread = threading.Thread(target=run_async_loop)
#     client_thread.daemon = True
#     client_thread.start()

#     # 2. 메인 스레드에서 Flask 서버 실행
#     print(f"📡 아이폰 GPS 데이터 수신 대기 중... (http://<your-ip>:{FLASK_PORT}/data)")
#     app.run(port=FLASK_PORT, host=FLASK_HOST, debug=False)


#연결 확인 버전
# # src/gps_service.py
# import asyncio
# import json
# from flask import Flask, request, render_template_string
# import websockets
# import threading
# import uuid

# # --- 설정 ---
# MAIN_SERVER_URI = "ws://localhost:8090"
# FLASK_PORT = 8000
# FLASK_HOST = "0.0.0.0"

# # --- 실시간 데이터 저장 ---
# latest_gps_position = {"latitude": None, "longitude": None}

# # --- Flask 서버 설정 ---
# app = Flask(__name__)
# import logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

# # --- 웹 페이지 UI 템플릿 (기존과 동일) ---
# HTML_TEMPLATE = """
# <!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>GPS Pinpoint Controller</title><style>body{font-family:sans-serif;max-width:600px;margin:auto;padding:20px}.container{border:1px solid #ccc;padding:20px;border-radius:8px}h2,h3{text-align:center}.form-group{margin-bottom:15px}label{display:block;margin-bottom:5px}input{width:95%;padding:8px;border:1px solid #ddd;border-radius:4px}button{width:100%;padding:10px;background-color:#007bff;color:white;border:none;border-radius:4px;cursor:pointer}button:hover{background-color:#0056b3}.status{margin-top:20px;background-color:#f0f0f0;padding:10px;border-radius:4px}</style></head><body><div class="container"><h2>Pinpoint Controller</h2><form action="/add_pinpoint" method="post"><div class="form-group"><label for="lat">위도 (Latitude):</label><input type="number" step="any" id="lat" name="latitude" required></div><div class="form-group"><label for="lon">경도 (Longitude):</label><input type="number" step="any" id="lon" name="longitude" required></div><div class="form-group"><label for="label">이름 (Label):</label><input type="text" id="label" name="label" required></div><button type="submit">HoloLens에 핀포인트 추가</button></form><div class="status"><h3>실시간 GPS 상태</h3><p><strong>아이폰 GPS:</strong> <span id="gps_status">수신 대기 중...</span></p></div></div><script>setInterval(async()=>{const response=await fetch('/get_gps');const data=await response.json();const statusEl=document.getElementById('gps_status');if(data.latitude){statusEl.textContent=`위도: ${data.latitude.toFixed(6)}, 경도: ${data.longitude.toFixed(6)}`}else{statusEl.textContent='수신 대기 중...'}},1000)</script></body></html>
# """

# # --- 웹 페이지 및 API 엔드포인트 ---
# @app.route("/")
# def index():
#     return render_template_string(HTML_TEMPLATE)

# @app.route("/get_gps")
# def get_gps():
#     return json.dumps(latest_gps_position)

# # ✨ --- 핵심 수정 사항: 아이폰 데이터 수신 로직 복원 ---
# @app.route("/data", methods=["POST"])
# def data():
#     """아이폰의 Sensor Logger 앱에서 location 데이터를 수신합니다."""
#     global latest_gps_position
#     if request.method == "POST":
#         try:
#             # 아이폰이 보낸 JSON 데이터에서 'payload' 리스트를 가져옵니다.
#             payload = json.loads(request.data).get('payload', [])
#             # payload 안의 각 센서 데이터를 확인합니다.
#             for d in payload:
#                 # 센서 이름이 'location'인 경우에만 처리합니다.
#                 if d.get("name") == "location":
#                     values = d.get("values", {})
#                     lat, lon = values.get('latitude'), values.get('longitude')
#                     # 위도, 경도 값이 모두 유효한 경우에만 변수를 업데이트합니다.
#                     if lat is not None and lon is not None:
#                         latest_gps_position = {"latitude": lat, "longitude": lon}
#                         # 터미널에 수신 성공 로그를 출력합니다. (디버깅용)
#                         print(f"📍 GPS 수신 성공: {latest_gps_position}")
#         except Exception as e:
#             print(f"데이터 처리 중 오류 발생: {e}")
#     return "success"

# @app.route("/add_pinpoint", methods=["POST"])
# def add_pinpoint():
#     """웹 UI에서 받은 핀포인트 정보를 메인 서버로 전송합니다."""
#     try:
#         lat = float(request.form['latitude'])
#         lon = float(request.form['longitude'])
#         label = request.form['label']
#         pinpoint_id = str(uuid.uuid4())

#         message = json.dumps({
#             "type": "ADD_PINPOINT",
#             "payload": { "id": pinpoint_id, "latitude": lat, "longitude": lon, "label": label }
#         })
#         asyncio.run_coroutine_threadsafe(broadcast_message(message), get_async_loop())
        
#         print(f"✨ 핀포인트 전송: {message}")
#         return "핀포인트가 HoloLens로 전송되었습니다. <a href='/'>돌아가기</a>"
#     except Exception as e:
#         return f"오류 발생: {e} <a href='/'>돌아가기</a>"

# # --- WebSocket 클라이언트 로직 (기존과 동일) ---
# ws_connection = None
# async_loop = None

# async def run_websocket_client():
#     global ws_connection, async_loop
#     async_loop = asyncio.get_running_loop()
    
#     while True:
#         try:
#             async with websockets.connect(MAIN_SERVER_URI) as websocket:
#                 ws_connection = websocket
#                 print(f"✅ 메인 서버에 연결됨: {MAIN_SERVER_URI}")
#                 while True:
#                     if latest_gps_position["latitude"] is not None:
#                         gps_message = json.dumps({
#                             "type": "GPS_POSITION_UPDATE",
#                             "payload": latest_gps_position
#                         })
#                         await ws_connection.send(gps_message)
#                     await asyncio.sleep(1)
#         except Exception:
#             ws_connection = None
#             print(f"메인 서버 연결 실패. 5초 후 재시도...")
#             await asyncio.sleep(5)

# async def broadcast_message(message):
#     if ws_connection:
#         await ws_connection.send(message)

# def get_async_loop():
#     return async_loop
    
# # --- 메인 실행 로직 (기존과 동일) ---
# if __name__ == '__main__':
#     def run_async():
#         asyncio.run(run_websocket_client())

#     client_thread = threading.Thread(target=run_async, daemon=True)
#     client_thread.start()

#     print(f"📡 GPS 컨트롤러 UI 접속: http://127.0.0.1:{FLASK_PORT}")
#     print(f"📱 아이폰 데이터 수신 주소: http://<your-ip>:{FLASK_PORT}/data")
#     app.run(port=FLASK_PORT, host=FLASK_HOST, debug=False, use_reloader=False)


#gps만 heading
# src/gps_service.py
import asyncio
import json
from flask import Flask, request, render_template_string
import websockets
import threading
import uuid

# --- 설정 ---
# websocket_server.py가 실행 중인 PC의 IP 주소로 변경하세요.
MAIN_SERVER_URI = "ws://localhost:8090" 
FLASK_PORT = 8000
FLASK_HOST = "0.0.0.0"

# --- 실시간 데이터 저장 ---
latest_gps_position = {"latitude": None, "longitude": None}
latest_heading = {"heading": None} # 🔥 1. 나침반 값을 저장할 변수 추가

# --- Flask 서버 ---
app = Flask(__name__)
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- 웹 페이지 UI ---
# 🔥 2. 웹 UI에 Calibrate 버튼과 나침반 상태 표시 추가
HTML_TEMPLATE = """
<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>GPS & Gyro Controller</title><style>body{font-family:sans-serif;max-width:600px;margin:auto;padding:20px}.container{border:1px solid #ccc;padding:20px;border-radius:8px;margin-bottom:20px}h2,h3{text-align:center}.form-group{margin-bottom:15px}label{display:block;margin-bottom:5px}input{width:95%;padding:8px;border:1px solid #ddd;border-radius:4px}button{width:100%;padding:10px;background-color:#007bff;color:white;border:none;border-radius:4px;cursor:pointer}.btn-calibrate{background-color:#28a745}.status{margin-top:20px;background-color:#f0f0f0;padding:10px;border-radius:4px}p{margin:5px 0}</style></head><body><div class="container"><h2>Remote Calibration</h2><form action="/calibrate_now" method="post"><button type="submit" class="btn-calibrate">현재 휴대폰 방향으로 Calibrate 실행</button></form></div><div class="container"><h2>Pinpoint Controller</h2><form action="/add_pinpoint" method="post"><div class="form-group"><label for="lat">위도 (Latitude):</label><input type="number" step="any" id="lat" name="latitude" required></div><div class="form-group"><label for="lon">경도 (Longitude):</label><input type="number" step="any" id="lon" name="longitude" required></div><div class="form-group"><label for="label">이름 (Label):</label><input type="text" id="label" name="label" required></div><button type="submit">HoloLens에 핀포인트 추가</button></form></div><div class="status"><h3>실시간 센서 상태</h3><p><strong>GPS:</strong> <span id="gps_status">수신 대기 중...</span></p><p><strong>나침반 (Heading):</strong> <span id="heading_status">수신 대기 중...</span></p></div><script>setInterval(async()=>{const gps_res=await fetch('/get_gps');const gps_data=await gps_res.json();const gpsEl=document.getElementById('gps_status');if(gps_data.latitude){gpsEl.textContent=`위도: ${gps_data.latitude.toFixed(6)}, 경도: ${gps_data.longitude.toFixed(6)}`}else{gpsEl.textContent='수신 대기 중...'};const heading_res=await fetch('/get_heading');const heading_data=await heading_res.json();const headingEl=document.getElementById('heading_status');if(heading_data.heading!==null){headingEl.textContent=`${heading_data.heading.toFixed(2)}°`}else{headingEl.textContent='수신 대기 중...'}},1000)</script></body></html>
"""

# --- 웹 페이지 및 API 엔드포인트 ---
@app.route("/")
def index(): return render_template_string(HTML_TEMPLATE)

@app.route("/get_gps")
def get_gps(): return json.dumps(latest_gps_position)

@app.route("/get_heading")
def get_heading(): return json.dumps(latest_heading)

@app.route("/data", methods=["POST"])
def data():
    """아이폰의 Sensor Logger 앱에서 location 및 heading 데이터를 수신합니다."""
    global latest_gps_position, latest_heading

    try:
        payload = json.loads(request.data).get('payload', [])
        for d in payload:
            values = d.get("values", {})
            if d.get("name") == "location":
                lat, lon = values.get('latitude'), values.get('longitude')
                if lat is not None and lon is not None:
                    latest_gps_position = {"latitude": lat, "longitude": lon}
            
            # 🔥 'heading' 또는 'compass' 이름을 모두 확인하도록 수정
            elif d.get("name") in ["heading", "compass"]:
                
                # 앱에서 보내주는 정확한 필드 이름을 모르므로, 가능성 있는 모든 이름을 순서대로 확인합니다.
                # (trueHeading, heading, compass, magneticHeading 등)
                heading = values.get("trueHeading", 
                                     values.get("heading", 
                                                values.get("magneticBearing")))

                if heading is not None and heading >= 0: # (heading이 -1인 경우는 보통 유효하지 않은 값)
                    latest_heading = {"heading": heading}
                    print(f"🧭 나침반 수신: {heading}") # 디버깅용 로그
                    
    except Exception: pass
    return "success"

# 🔥 4. Calibrate 실행을 위한 새 엔드포인트 추가
@app.route("/calibrate_now", methods=["POST"])
def calibrate_now():
    """웹 UI의 버튼 클릭 시, 현재 나침반 값으로 Calibrate 메시지를 보냅니다."""
    if latest_heading["heading"] is not None:
        message = json.dumps({
            "type": "CALIBRATE_WITH_HEADING",
            "payload": latest_heading
        })
        # 백그라운드 스레드에서 실행 중인 WebSocket 클라이언트로 메시지 전송 요청
        asyncio.run_coroutine_threadsafe(broadcast_message_to_main_server(message), get_async_loop())
        print(f"✨ Calibrate 요청 전송: {message}")
        return "Calibrate 요청이 HoloLens로 전송되었습니다. <a href='/'>돌아가기</a>"
    else:
        return "오류: 아직 나침반 데이터가 수신되지 않았습니다. <a href='/'>돌아가기</a>"

@app.route("/add_pinpoint", methods=["POST"])
def add_pinpoint():
    """웹 UI에서 받은 핀포인트 정보를 메인 서버로 전송합니다."""
    try:
        message = json.dumps({
            "type": "ADD_PINPOINT",
            "payload": {
                "id": str(uuid.uuid4()),
                "latitude": float(request.form['latitude']),
                "longitude": float(request.form['longitude']),
                "label": request.form['label']
            }})
        asyncio.run_coroutine_threadsafe(broadcast_message_to_main_server(message), get_async_loop())
        print(f"✨ 핀포인트 전송: {message}")
        return "핀포인트가 HoloLens로 전송되었습니다. <a href='/'>돌아가기</a>"
    except Exception as e:
        return f"오류 발생: {e}. <a href='/'>돌아가기</a>"

# --- WebSocket 클라이언트 로직 (기존과 동일) ---
ws_connection, async_loop = None, None

async def run_websocket_client():
    global ws_connection, async_loop
    async_loop = asyncio.get_running_loop()
    while True:
        try:
            async with websockets.connect(MAIN_SERVER_URI) as websocket:
                ws_connection = websocket
                print(f"✅ 메인 서버에 연결됨: {MAIN_SERVER_URI}")
                while True:
                    if latest_gps_position["latitude"] is not None:
                        gps_message = json.dumps({"type": "GPS_POSITION_UPDATE", "payload": latest_gps_position})
                        await ws_connection.send(gps_message)
                    await asyncio.sleep(1) # 1초마다 GPS 정보 전송
        except Exception:
            ws_connection = None
            print(f"메인 서버 연결 실패. 5초 후 재시도...")
            await asyncio.sleep(5)

async def broadcast_message_to_main_server(message):
    if ws_connection: await ws_connection.send(message)

def get_async_loop(): return async_loop
    
# --- 메인 실행 로직 ---
if __name__ == '__main__':
    def run_async(): asyncio.run(run_websocket_client())
    client_thread = threading.Thread(target=run_async, daemon=True)
    client_thread.start()

    print(f"📡 GPS 컨트롤러 UI 접속: http://127.0.0.1:{FLASK_PORT}")
    print(f"📱 아이폰 데이터 수신 주소: http://<your-ip>:{FLASK_PORT}/data")
    app.run(port=FLASK_PORT, host=FLASK_HOST, debug=False, use_reloader=False)