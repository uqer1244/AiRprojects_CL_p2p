import tts  # tts.py 파일을 모듈로 임포트합니다.
import time

print("--- tts.py 모듈 임포트 테스트 ---")
print("이 스크립트는 tts.py 파일에 정의된 speak() 함수를 호출합니다.")

try:
    # 1. 첫 번째 문장 테스트
    print("\n🔊 테스트 1: '안녕하세요. 모듈 임포트 테스트입니다.'")
    tts.speak("안녕하세요. 모듈 임포트 테스트입니다.")

    print("재생 완료. 2초 후 다음 문장을 테스트합니다.")
    time.sleep(2)

    # 2. 두 번째 문장 테스트
    print("\n🔊 테스트 2: '두 번째 문장입니다.'")
    tts.speak("두 번째 문장입니다.")

    print("\n✅ 테스트가 성공적으로 완료되었습니다.")

except Exception as e:
    print(f"\n💥 테스트 중 오류 발생: {e}")
    print("   (tts.py 파일이 같은 폴더에 있는지,")
    print("    pyttsx3 라이브러리가 올바르게 설치되었는지 확인하세요.)")