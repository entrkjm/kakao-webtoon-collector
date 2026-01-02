#!/usr/bin/env python3
"""
로컬 테스트 스크립트: Cloud Functions를 로컬에서 테스트

두 가지 방법으로 테스트 가능:
1. Functions Framework 사용 (HTTP 서버)
2. 직접 함수 호출 (더 빠름)
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# src 디렉토리도 경로에 추가
src_path = project_root / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))

# functions_framework 없이도 테스트 가능하도록 모킹
try:
    import functions_framework
except ImportError:
    # functions_framework가 없으면 모킹
    class functions_framework:
        @staticmethod
        def http(func):
            return func
    import sys
    sys.modules['functions_framework'] = functions_framework

from main import main

# Flask Request 객체 생성 (테스트용)
class TestRequest:
    def get_json(self, silent=True):
        return {
            'date': '2026-01-01',
            'sort_keys': ['popularity', 'views'],
            'collect_all_weekdays': False
        }

if __name__ == "__main__":
    print("=== Cloud Functions 로컬 테스트 ===\n")
    
    # 환경 변수 설정 (GCS/BigQuery 업로드 비활성화)
    import os
    os.environ['UPLOAD_TO_GCS'] = 'false'
    os.environ['UPLOAD_TO_BIGQUERY'] = 'false'
    
    request = TestRequest()
    
    try:
        result, status_code = main(request)
        
        print(f"\n상태 코드: {status_code}")
        print(f"결과: {result}")
        
        if status_code == 200:
            print("\n✅ 테스트 성공!")
        else:
            print("\n❌ 테스트 실패!")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
