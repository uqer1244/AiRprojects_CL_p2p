import asyncio
import json
import random
import argparse
import websockets

async def run_client(node_id: str, start_lat: float, start_lon: float):
    """서버에 접속해서 1초마다 가상 위치를 보내는 테스트 클라이언트"""
    uri = f"ws://127.0.0.1:8000/ws/{node_id}"

    # 연결이 끊겼을 때 재시도하기 위한 무한 루프
    while True:
        try:
            # `async with`를 사용해 자동으로 연결 및 해제 관리
            async with websockets.connect(uri) as websocket:
                print(f"🚗 클라이언트 [{node_id}] 서버에 연결 성공!")

                # 1. 1초마다 위치를 보내는 작업
                async def send_location():
                    lat, lon = start_lat, start_lon
                    while True:
                        # 가상으로 위치를 조금씩 랜덤하게 변경
                        lat += random.uniform(-0.0001, 0.0001)
                        lon += random.uniform(-0.0001, 0.0001)

                        payload = {"latitude": lat, "longitude": lon}
                        await websocket.send(json.dumps(payload))
                        # print(f"[{node_id}] 위치 전송: {lat:.4f}, {lon:.4f}") # 상세 로그 확인 시 주석 해제
                        await asyncio.sleep(1)

                # 2. 서버로부터 그룹 업데이트를 받는 작업
                async def receive_updates():
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)

                        # 그룹 멤버들의 ID만 간략하게 출력
                        member_ids = [m['node_id'] for m in data.get('group_members', [])]
                        print(f"[{node_id}] 📢 그룹 업데이트! 현재 멤버: {member_ids}")

                # 두 작업을 동시에 실행
                await asyncio.gather(send_location(), receive_updates())

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            print(f"클라이언트 [{node_id}] 연결 오류: {e}. 5초 후 재접속 시도...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"클라이언트 [{node_id}] 알 수 없는 오류: {e}. 5초 후 재접속 시도...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # 터미널에서 인자를 받아 클라이언트를 실행할 수 있도록 설정
    parser = argparse.ArgumentParser(description="P2P Test Client")
    parser.add_argument("--id", required=True, help="Client's unique node ID (e.g., Car-A)")
    parser.add_argument("--lat", type=float, required=True, help="Starting latitude (e.g., 37.310)")
    parser.add_argument("--lon", type=float, required=True, help="Starting longitude (e.g., 126.830)")

    args = parser.parse_args()

    try:
        # 파싱된 인자로 클라이언트 실행
        asyncio.run(run_client(args.id, args.lat, args.lon))
    except KeyboardInterrupt:
        print(f"\n클라이언트 [{args.id}]을 종료합니다.")