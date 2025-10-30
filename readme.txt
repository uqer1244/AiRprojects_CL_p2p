실행
0. main.py -> 서버 실행 -> 오라클 클라우드에서 상시로 돌아가는중
1. python p2p_client.py --id A -> GPS 데이터 대기
2. python gps_sender.py --id A -> GPS 데이터 가상으로 보내는 코드 / 웹소켓 + UDP
3. python rec.py --from-id A
4. python ./communication/websocket_server.py -> 웹소켓 서버
5. python gps_service.py -> 홀로렌즈로 gps 데이터 보내는 곳
6. python ai_main2.py -> yolo + 웹캠으로 물체 인식하는 초안