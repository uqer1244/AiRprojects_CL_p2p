# # websocket_server.py
# import asyncio
# import websockets

# class WebSocketServer:
#     """
#     websockets v10+ 호환 핸들러: 인자 1개(websocket)
#     start(): 서버 실행(영구 대기)
#     broadcast(msg): 연결된 모든 클라이언트로 전송
#     """
#     def __init__(self, host="0.0.0.0", port=8090):
#         self.host = host
#         self.port = port
#         self.connected = set()

#     async def _handler(self, websocket):
#         # 경로가 필요하면 getattr(websocket, "path", None)
#         self.connected.add(websocket)
#         try:
#             async for _ in websocket:
#                 pass
#         except websockets.ConnectionClosed:
#             pass
#         finally:
#             self.connected.discard(websocket)

#     async def start(self):
#         async with websockets.serve(self._handler, self.host, self.port):
#             print(f"🚀 WebSocket server listening on ws://{self.host}:{self.port}")
#             await asyncio.Future()  # run forever

#     async def broadcast(self, message: str):
#         if not self.connected:
#             return
#         dead = set()
#         for ws in list(self.connected):
#             try:
#                 await ws.send(message)
#             except websockets.ConnectionClosed:
#                 dead.add(ws)
#         if dead:
#             self.connected.difference_update(dead)




# src/communication/websocket_server.py
# import asyncio
# import json
# import websockets

# class WebSocketServer:
#     def __init__(self, host="0.0.0.0", port=8090):
#         self.host = host
#         self.port = port
#         self.connected = set()
#         self.latest_gps_data = None # HoloLens가 접속 시 바로 받을 수 있도록 최신 GPS 데이터 저장

#     async def _handler(self, websocket):
#         self.connected.add(websocket)
#         print(f"🔗 클라이언트 연결: {websocket.remote_address} (총 {len(self.connected)}명)")
        
#         # 새 클라이언트(HoloLens 등)에게 최신 GPS 데이터가 있으면 즉시 전송
#         if self.latest_gps_data:
#             try:
#                 await websocket.send(self.latest_gps_data)
#             except websockets.ConnectionClosed:
#                 pass

#         try:
#             # 클라이언트(gps_service.py)로부터 메시지 수신
#             async for message in websocket:
#                 try:
#                     data = json.loads(message)
#                     # GPS 서비스로부터 GPS 업데이트 메시지를 받으면,
#                     if data.get("type") == "GPS_POSITION_UPDATE":
#                         self.latest_gps_data = message # 최신 데이터 저장
#                         # 이 메시지를 보낸 GPS 서비스를 제외한 모든 클라이언트(HoloLens 등)에게 방송
#                         broadcast_tasks = [
#                             ws.send(message) for ws in self.connected if ws != websocket
#                         ]
#                         if broadcast_tasks:
#                             await asyncio.gather(*broadcast_tasks)
#                 except Exception:
#                     # 다른 타입의 메시지(예: HoloLens가 보내는 메시지)는 무시
#                     pass
#         except websockets.ConnectionClosed:
#             pass
#         finally:
#             self.connected.discard(websocket)
#             print(f"🔗 클라이언트 연결 해제: {websocket.remote_address} (총 {len(self.connected)}명)")

#     async def start(self):
#         async with websockets.serve(self._handler, self.host, self.port):
#             print(f"🚀 WebSocket 서버 listening on ws://{self.host}:{self.port}")
#             await asyncio.Future()

#     async def broadcast(self, message: str):
#         """YOLO 위험 경고(RISK_ALERT) 방송용 함수"""
#         if self.connected:
#             # ✨ 버그 수정: asyncio.gather를 사용하여 모든 send 작업을 확실히 await 함
#             # 여러 클라이언트에 동시에 메시지를 보냅니다.
#             await asyncio.gather(*[ws.send(message) for ws in self.connected])




#실행가능
# src/communication/websocket_server.py
# import asyncio
# import json
# import websockets

# class WebSocketServer:
#     def __init__(self, host="0.0.0.0", port=8090):
#         self.host = host
#         self.port = port
#         self.connected = set()
#         self.latest_gps_data = None
#         self.pinpoints = {}

#     async def _handler(self, websocket):
#         self.connected.add(websocket)
#         print(f"🔗 클라이언트 연결: {websocket.remote_address} (총 {len(self.connected)}명)")
        
#         if self.latest_gps_data: await websocket.send(self.latest_gps_data)
#         for pin_msg in self.pinpoints.values(): await websocket.send(pin_msg)

#         try:
#             async for message in websocket:
#                 try:
#                     data = json.loads(message)
#                     msg_type = data.get("type")

#                     if msg_type in ["GPS_POSITION_UPDATE", "ADD_PINPOINT"]:
#                         # ✨ [디버그 로그 1] 메시지 수신 확인
#                         print(f"Received message of type '{msg_type}' from a client.")
                        
#                         if msg_type == "ADD_PINPOINT":
#                             pin_id = data.get("payload", {}).get("id")
#                             if pin_id: self.pinpoints[pin_id] = message
#                         elif msg_type == "GPS_POSITION_UPDATE":
#                             self.latest_gps_data = message
                        
#                         # ✨ [디버그 로그 2] HoloLens로 방송 확인
#                         print(f"Broadcasting '{msg_type}' to other clients...")
#                         tasks = [ws.send(message) for ws in self.connected if ws != websocket]
#                         if tasks: await asyncio.gather(*tasks)
#                         print("Broadcast complete.")

#                 except Exception as e:
#                     print(f"Error processing message: {e}")
#         except websockets.ConnectionClosed:
#             pass
#         finally:
#             self.connected.discard(websocket)
#             print(f"🔗 클라이언트 연결 해제: {websocket.remote_address} (총 {len(self.connected)}명)")

#     async def start(self):
#         async with websockets.serve(self._handler, self.host, self.port):
#             print(f"🚀 WebSocket 서버 listening on ws://{self.host}:{self.port}")
#             await asyncio.Future()

#     async def broadcast(self, message: str):
#         if self.connected:
#             # print(f"Broadcasting RISK_ALERT to {len(self.connected)} clients.") # 필요 시 주석 해제
#             await asyncio.gather(*[ws.send(message) for ws in self.connected])



#gps만 heading
# src/communication/websocket_server.py
import asyncio
import json
import websockets

class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=8090):
        self.host = host
        self.port = port
        self.connected = set()
        self.latest_gps_data = None
        # 서버에 핀포인트 목록을 저장하여, 새로 접속하는 클라이언트에게도 전송
        self.pinpoints = {} 

    async def _handler(self, websocket):
        self.connected.add(websocket)
        print(f"🔗 클라이언트 연결: {websocket.remote_address} (총 {len(self.connected)}명)")
        
        # 새 클라이언트에게 기존 핀포인트 목록과 최신 GPS 데이터 즉시 전송
        if self.latest_gps_data:
            await websocket.send(self.latest_gps_data)
        for pin_msg in self.pinpoints.values():
            await websocket.send(pin_msg)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    # 🔥 1. Calibrate 메시지도 방송 목록에 추가
                    # GPS, 핀포인트, 또는 Calibrate 메시지를 받으면, 보낸이를 제외한 모두에게 방송
                    if msg_type in ["GPS_POSITION_UPDATE", "ADD_PINPOINT", "CALIBRATE_WITH_HEADING"]:
                        if msg_type == "ADD_PINPOINT":
                            pin_id = data.get("payload", {}).get("id")
                            if pin_id: self.pinpoints[pin_id] = message
                        elif msg_type == "GPS_POSITION_UPDATE":
                            self.latest_gps_data = message
                        
                        # 메시지를 보낸 클라이언트를 제외한 모든 클라이언트에게 전송
                        tasks = [ws.send(message) for ws in self.connected if ws != websocket]
                        if tasks: await asyncio.gather(*tasks)

                except Exception as e:
                    print(f"메시지 처리 오류: {e}")
        except websockets.ConnectionClosed:
            pass
        finally:
            self.connected.discard(websocket)
            print(f"🔗 클라이언트 연결 해제: {websocket.remote_address} (총 {len(self.connected)}명)")

    async def start(self):
        async with websockets.serve(self._handler, self.host, self.port):
            print(f"🚀 WebSocket 서버 listening on ws://{self.host}:{self.port}")
            await asyncio.Future()

    async def broadcast(self, message: str):
        """YOLO 위험 경고 등 모든 클라이언트에게 방송하는 함수"""
        if self.connected:
            await asyncio.gather(*[ws.send(message) for ws in self.connected])

# # 이 파일을 직접 실행할 경우를 위한 코드
# if __name__ == "__main__":
#     server = WebSocketServer()
#     asyncio.run(server.start())