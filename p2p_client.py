import asyncio
import json
import random
import argparse
import websockets
import socket
import atexit
import time
import os  # os 라이브러리 추가
from typing import Dict, Tuple
from dotenv import load_dotenv  # dotenv 라이브러리 추가

load_dotenv()

# --- P2P(UDP) 통신을 위한 프로토콜 클래스 ---
class PeerProtocol:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.transport = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        print(f"[{self.node_id}] P2P UDP 소켓이 {transport.get_extra_info('sockname')} 에서 열렸습니다.")

    def datagram_received(self, data: bytes, addr: tuple):
        decoded_data = data.decode()
        if not decoded_data.startswith("p2p_heartbeat"):
            print(f"[{self.node_id}] 📥 (UDP) P2P 메시지 수신 from {addr}: {decoded_data}")

    def error_received(self, exc: Exception):
        print(f"[{self.node_id}] P2P UDP 오류 발생: {exc}")

    def connection_lost(self, exc: Exception):
        print(f"[{self.node_id}] P2P UDP 소켓이 닫혔습니다.")


# --- 외부 명령 수신용 프로토콜 클래스 ---
class CommandProtocol:
    def __init__(self, p2p_transport: asyncio.DatagramTransport, p2p_peers: Dict, my_node_id: str,
                 websocket_queue: asyncio.Queue, gps_queue: asyncio.Queue, first_gps_event: asyncio.Event):
        self.p2p_transport = p2p_transport
        self.p2p_peers = p2p_peers
        self.my_node_id = my_node_id
        self.websocket_queue = websocket_queue
        self.gps_queue = gps_queue
        self.first_gps_event = first_gps_event

    def connection_made(self, transport):
        print(f"✅ [{self.my_node_id}] 외부 명령 수신 대기 중 on {transport.get_extra_info('sockname')}")

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode())
            if "gps" in message:
                gps_data = message["gps"]
                if "latitude" in gps_data and "longitude" in gps_data:
                    self.gps_queue.put_nowait(gps_data)
                    if not self.first_gps_event.is_set():
                        self.first_gps_event.set()
                return

            target_id = message.get("target_id")
            content = message.get("content")
            if not content: return

            if not target_id:  # 그룹 전체 방송
                print(f"📣 [{self.my_node_id}] 외부 명령 수신: 그룹 전체에 '{content}' 방송")
                full_message = f"[{self.my_node_id}의 방송]: {content}"
                if self.p2p_transport and self.p2p_peers:
                    for peer_id, peer_addr in self.p2p_peers.items():
                        self.p2p_transport.sendto(full_message.encode(), peer_addr)
                        relay_msg = {"type": "p2p_relay", "target_id": peer_id, "content": full_message}
                        self.websocket_queue.put_nowait(relay_msg)
                else:
                    print("   -> 경고: 방송을 보낼 P2P 피어가 없습니다.")
            else:  # 특정 대상에게 귓속말
                print(f"📣 [{self.my_node_id}] 외부 명령 수신: [{target_id}]에게 '{content}' 전송")
                full_message = f"[{self.my_node_id}의 귓속말]: {content}"
                if self.p2p_transport and target_id in self.p2p_peers:
                    target_addr = self.p2p_peers[target_id]
                    self.p2p_transport.sendto(full_message.encode(), target_addr)
                    relay_msg = {"type": "p2p_relay", "target_id": target_id, "content": full_message}
                    self.websocket_queue.put_nowait(relay_msg)
                else:
                    print(f"   -> 오류: 타겟 [{target_id}]를 모르거나 P2P가 준비되지 않음")
        except Exception as e:
            print(f"잘못된 외부 명령 수신: {e}")

    def error_received(self, exc):
        print(f"외부 명령 소켓 오류: {exc}")



# --- 메인 클라이언트 로직 ---
async def run_client(node_id: str, p2p_port_req: int, cmd_port_req: int):
    #server_uri = f"ws://127.0.0.1:8000/ws/{node_id}"
    base_server_uri = os.getenv("SERVER_URI")
    if not base_server_uri:
        print("🚨 오류: .env 파일에 SERVER_URI가 설정되지 않았습니다.")
        return

    server_uri = f"{base_server_uri}{node_id}"
    my_p2p_peers: Dict[str, Tuple[str, int]] = {}
    p2p_transport: asyncio.DatagramTransport = None
    websocket_queue = asyncio.Queue()
    gps_queue = asyncio.Queue()
    first_gps_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    try:
        p2p_transport, _ = await loop.create_datagram_endpoint(lambda: PeerProtocol(node_id),
                                                               local_addr=('0.0.0.0', p2p_port_req))
        actual_p2p_port = p2p_transport.get_extra_info('sockname')[1]
        cmd_transport, _ = await loop.create_datagram_endpoint(
            lambda: CommandProtocol(p2p_transport, my_p2p_peers, node_id, websocket_queue, gps_queue, first_gps_event),
            local_addr=('127.0.0.1', cmd_port_req)
        )
        actual_cmd_port = cmd_transport.get_extra_info('sockname')[1]
        print(f"✅ 포트 자동 할당 -> P2P: {actual_p2p_port}, Command: {actual_cmd_port}")

        try:
            try:
                with open("p2p_ports.json", "r") as f:
                    port_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                port_data = {}
            port_data[node_id] = actual_cmd_port
            with open("p2p_ports.json", "w") as f:
                json.dump(port_data, f, indent=4)
            print(f"📄 공유 파일(p2p_ports.json)에 내 명령 포트({actual_cmd_port})를 기록했습니다.")

            def cleanup_port_file():
                try:
                    with open("p2p_ports.json", "r") as f:
                        final_port_data = json.load(f)
                    if node_id in final_port_data: del final_port_data[node_id]
                    with open("p2p_ports.json", "w") as f:
                        json.dump(final_port_data, f, indent=4)
                    print(f"\n📄 공유 파일에서 [{node_id}]의 포트 정보를 삭제했습니다.")
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

            atexit.register(cleanup_port_file)
        except Exception as e:
            print(f"공유 파일 쓰기 오류: {e}")

    except OSError as e:
        print(f"UDP 포트를 열 수 없습니다: {e}")
        return

    print(f"\n[{node_id}] 클라이언트 시작. 첫 GPS 데이터를 기다립니다...")
    await first_gps_event.wait()
    print(f"🛰️ [{node_id}] 첫 GPS 데이터 수신 완료! 메인 서버에 연결을 시작합니다.")

    while True:
        try:
            async with websockets.connect(server_uri) as websocket:
                print(f"🚗 클라이언트 [{node_id}] 서버에 연결 성공!")

                async def send_p2p_heartbeat():
                    while True:
                        await asyncio.sleep(5)
                        if p2p_transport and my_p2p_peers:
                            message = b'p2p_heartbeat'
                            for peer_addr in my_p2p_peers.values():
                                p2p_transport.sendto(message, peer_addr)

                async def websocket_sender():
                    while True:
                        message = await websocket_queue.get()
                        await websocket.send(json.dumps(message))

                async def handle_server_messages():
                    async for message in websocket:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type == "p2p_message":
                            print(f"[{node_id}] 📥 (RELAY) P2P 메시지 수신 from [{data['from_id']}]: {data['content']}")
                        elif msg_type == "group_update":
                            members = data.get("data", [])
                            print(f"[{node_id}] 📢 그룹 업데이트! 멤버: {[m['node_id'] for m in members]}")
                            current_peer_ids = {m['node_id'] for m in members}
                            for peer_id in list(my_p2p_peers.keys()):
                                if peer_id not in current_peer_ids:
                                    del my_p2p_peers[peer_id]
                                    print(f"[{node_id}] ❌ {peer_id}와 P2P 연결 목록에서 제거.")
                            for member in members:
                                peer_id = member["node_id"]
                                if peer_id != node_id and peer_id not in my_p2p_peers:
                                    req_msg = {"type": "p2p_request", "target_id": peer_id, "sender_id": node_id,
                                               "port": actual_p2p_port}
                                    await websocket.send(json.dumps(req_msg))
                        elif msg_type == "p2p_request":
                            sender_id, sender_ip, sender_port = data["sender_id"], data["ip"], data["port"]
                            print(f"[{node_id}] 🤝 [{sender_id}]로부터 P2P 연결 요청 수신.")
                            my_p2p_peers[sender_id] = (sender_ip, sender_port)
                            res_msg = {"type": "p2p_response", "target_id": sender_id, "sender_id": node_id,
                                       "port": actual_p2p_port}
                            await websocket.send(json.dumps(res_msg))
                            if p2p_transport: p2p_transport.sendto(f"Punch from {node_id}".encode(),
                                                                   (sender_ip, sender_port))
                        elif msg_type == "p2p_response":
                            sender_id, sender_ip, sender_port = data["sender_id"], data["ip"], data["port"]
                            print(f"[{node_id}] 🤝 [{sender_id}]로부터 P2P 연결 응답 수신.")
                            my_p2p_peers[sender_id] = (sender_ip, sender_port)
                            if p2p_transport: p2p_transport.sendto(f"Punch from {node_id}".encode(),
                                                                   (sender_ip, sender_port))

                async def send_location():
                    current_location = await gps_queue.get()
                    while True:
                        await websocket.send(json.dumps(current_location))
                        try:
                            new_gps = await asyncio.wait_for(gps_queue.get(), timeout=1.0)
                            current_location = new_gps
                            print(f"🛰️ 외부 GPS 데이터 수신: {current_location}")
                        except asyncio.TimeoutError:
                            await asyncio.sleep(1)

                await asyncio.gather(
                    handle_server_messages(), send_location(),
                    send_p2p_heartbeat(), websocket_sender()
                )
        except Exception as e:
            print(f"클라이언트 [{node_id}] 연결 오류: {e}. 5초 후 재시도...")
            my_p2p_peers.clear()
            await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P Hybrid Client - Waits for GPS")
    parser.add_argument("--id", help="[Optional] Client's unique node ID")
    parser.add_argument("--port", type=int, default=0, help="UDP port for P2P (default: 0 = auto)")
    parser.add_argument("--cmd-port", type=int, default=0, help="UDP port for internal commands (default: 0 = auto)")
    args = parser.parse_args()
    if not args.id:
        adjectives = ["Brave", "Clever", "Fast", "Silent", "Wise", "Happy"]
        nouns = ["Lion", "Tiger", "Fox", "Eagle", "Wolf", "Panda"]
        node_id = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
        print(f"✨ ID가 지정되지 않아 자동으로 생성합니다: {node_id}")
    else:
        node_id = args.id
    try:
        asyncio.run(run_client(node_id, args.port, args.cmd_port))
    except KeyboardInterrupt:
        print(f"\n클라이언트 [{node_id}]을 종료합니다.")