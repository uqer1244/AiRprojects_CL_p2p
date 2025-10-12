1. main.py -> GPS 서버, 각 차량의 GPS위치를 1초마다 받아서 그룹을 지어주는 역할
   + p2p 통신을 위한 p2p 포트(외부)에 대한 정보를 보내줌
2. p2p_client.py -> GPS서버로 클라이언트 (GPS 위치)를 1초마다 보냄
   + GPS서버에서 자신이 속한 그룹을 리턴받고, 그 그룹내부에서 p2p 통신
3. send_message.py -> p2p.client.py에 내부 포트가 있는데, 그 포트를 사용하도록 하는 레퍼런스 파일
  (다른 기능 만들때, 참고해서 만들면 됨)
4. p2p_ports.json -> p2p 포트(내부), id 자동생성 할때, 기록하는 용도
5. gps_sender.py -> 내부포트로 GPS 데이터 보내주는 예시

내부포트 : 클라이언트 내부에서 프로세서 사이의 통신을 위한 포트 (자동생성, p2p_ports.json에 기록)
외부포트 : 클라이언트 사이에서 통신을 위한 포트 (main.py 서버에 있음)

redis-server << 터미널에서 실행 필요

실행
1. main.py -> 서버 실행
2. p2p_client.py -> GPS 데이터 대기
3. gps_sender.py -> GPS 데이터 송신
4. send_message.py -> p2p 그룹 데이터 송신