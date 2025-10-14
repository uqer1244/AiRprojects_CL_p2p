import asyncio
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Tuple
import redis.asyncio as aioredis

# --- 설정 ---
GROUPING_DISTANCE_M = 500
REDIS_URL = "redis://localhost"

# --- FastAPI 앱 및 Redis 클라이언트 설정 ---
app = FastAPI()
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

active_connections: Dict[str, WebSocket] = {}


# --- 핵심 로직: Redis의 위치기반 기능 활용 ---
async def update_and_get_group(node_id: str, location: Tuple[float, float]) -> List[Dict]:
    await redis_client.geoadd("vehicles", (location[1], location[0], node_id))

    # [DEBUG] GEOSEARCH 실행 로그
    print(f"--- 🚗 {node_id}가 GEOSEARCH 실행 (중심: {location}) ---")
    nearby_vehicles = await redis_client.geosearch(
        "vehicles",
        longitude=location[1],
        latitude=location[0],
        radius=GROUPING_DISTANCE_M,
        unit="m",
        withcoord=True,
    )
    # [DEBUG] GEOSEARCH 결과 로그
    print(f"    -> 찾은 차량: {[v[0] for v in nearby_vehicles]}")

    group_members = []
    for member_info in nearby_vehicles:
        node_name, (lon, lat) = member_info
        group_members.append({"node_id": node_name, "location": (lat, lon)})
    return group_members


# --- 서버 측 Pub/Sub 리스너 ---
async def group_update_listener():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("group_updates")
    print("📢 그룹 업데이트 리스너 시작됨.")
    async for message in pubsub.listen():
        if message["type"] == "message":
            update_info = json.loads(message["data"])

            # [DEBUG] 리스너가 받은 메시지와 전송 대상 로그
            group_members_list = update_info.get("group_members", [])
            target_ids = [m['node_id'] for m in group_members_list]
            print(f"--- 📢 리스너가 그룹 업데이트 감지 (대상: {target_ids}) ---")

            for member in group_members_list:
                node_id = member["node_id"]
                if node_id in active_connections:
                    conn = active_connections[node_id]
                    try:
                        # PUSH 메시지 형식 통일
                        await conn.send_json({"type": "group_update", "data": group_members_list})
                    except Exception as e:
                        print(f"    -> PUSH 실패: {node_id} ({e})")


@app.on_event("startup")
async def startup_event():
    await redis_client.flushdb()
    asyncio.create_task(group_update_listener())


# --- 서버 측 웹소켓 엔드포인트 ---
@app.websocket("/ws/{node_id}")
async def websocket_endpoint(websocket: WebSocket, node_id: str):
    await websocket.accept()
    active_connections[node_id] = websocket
    print(f"✅ 차량 연결됨: {node_id} (총 {len(active_connections)}대)")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # P2P 시그널링 중계 로직 (이전과 동일)
            if message.get("type") in ["p2p_request", "p2p_response"]:
                target_id = message.get("target_id")
                if target_id in active_connections:
                    message["ip"] = websocket.client.host
                    target_conn = active_connections[target_id]
                    await target_conn.send_json(message)
                continue

            # 위치 업데이트 로직
            loc_tuple = (message["latitude"], message["longitude"])
            await redis_client.hset(f"peer:{node_id}", mapping={
                "node_id": node_id,
                "location": f"{loc_tuple[0]},{loc_tuple[1]}",
                "last_seen": time.time()
            })

            group_members = await update_and_get_group(node_id, loc_tuple)

            # Redis Pub/Sub 채널에 그룹 정보 발행
            # 메시지 형식 통일
            await redis_client.publish("group_updates", json.dumps({"group_members": group_members}))

    except WebSocketDisconnect:
        await redis_client.zrem("vehicles", node_id)
        del active_connections[node_id]
        print(f"❌ 차량 연결 끊김: {node_id} (총 {len(active_connections)}대)")