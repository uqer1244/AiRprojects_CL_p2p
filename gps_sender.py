# gps_sender.py
import socket
import json
import argparse
import time
import random


def send_gps_data(target_node_id: str, lat: float, lon: float):
    """공유 파일에서 클라이언트의 명령 포트를 찾아 GPS 데이터를 보냅니다."""
    try:
        with open("p2p_ports.json", "r") as f:
            port_data = json.load(f)
    except Exception as e:
        print(f"오류: p2p_ports.json 파일을 읽을 수 없습니다. ({e})")
        return

    command_port = port_data.get(target_node_id)
    if not command_port:
        print(f"오류: 실행 중인 클라이언트 '{target_node_id}'를 찾을 수 없습니다.")
        return

    command = {
        "gps": {
            "latitude": lat,
            "longitude": lon
        }
    }

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(json.dumps(command).encode(), ("127.0.0.1", command_port))
    print(f"✅ [{target_node_id}]에게 GPS 데이터 ({lat:.5f}, {lon:.5f}) 전송 완료.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send GPS Data to a P2P Client")
    parser.add_argument("--id", required=True, help="Node ID of the target client")
    args = parser.parse_args()

    # 테스트를 위해 0.5초마다 가상 GPS 데이터를 생성하여 보냄
    lat, lon = 37.310, 126.830  # 초기 위치
    while True:
        send_gps_data(args.id, lat, lon)
        time.sleep(0.5)