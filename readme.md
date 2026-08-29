# Novel(Syosetu, Kakuyomu) Downloader & Translator

일본 소설 플랫폼(소설가가 되자, 카쿠요무)의 웹소설 수집, 태그 검색, 번역, EPUB 전자책 변환을 일괄 처리하는 통합 Desktop GUI 애플리케이션입니다.

## 주요 기능

* **웹소설 검색 및 크롤링**

  * 내부 태그 카테고리 기반 소설 검색 및 상세 정보 조회 및 추가 기능

  * 소설가가 되자(Syosetu), 카쿠요무(Kakuyomu) 회차별 일괄 다운로드 및 신규 회차 감지

  * 소설가가 되자(Syosetu), 카쿠요무(Kakuyomu) 소설 내부 목록 저장

* **AI & Papago 번역**

  * Google Gemini API 기반 맞춤형 번역

  * Naver Papago API 번역 연동

* **EPUB 전자책 자동 생성**

  * 수집 및 번역된 TXT 파일의 EPUB 포맷 변환 및 CSS 스타일링 적용

  * 타이틀 표지 이미지 자동 생성

  * 로컬 AI 모델(mDeBERTa) 기반 문단 단락 구분 및 라인 브레이크 최적화

    - 사용시 `requirements_ai.txt`의 `torch` 버전 설정 및 `pip install -r requirements_ai.txt`  추가 설치, config.py 내부 USE\_LOCAL\_AI를 `True`로 변경 필요

    - 요구 사항 cuda 코어

* **GUI 및 사용자 편의**

  * PySide6 기반 화면 UI 및 Tkinter 기반 스플래시 스크린 로더

  * 16가지 커스텀 테마(다크, 라이트, OLED, 블루, 퍼플 등) 선택 및 QSS 스타일 적용

  * 멀티스레드 기반 다운로드 및 번역 진행 상황 실시간 제공

## 설치 및 실행 방법

*(현재 윈도우 만을 지원합니다. 추후 리눅스와 맥os를 지원할 예정입니다.)*

### 1. 저장소 클론

```bash
git clone https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator.git
cd novel-syosetu-kakuyomu-downloader-translator

```

### 2. 가상환경 생성 및 활성화

프로젝트 독립 환경 구성을 위해 가상환경 생성을 권장합니다.

* **Windows**:
```bash
python -m venv venv
call venv\Scripts\activate

```

### 3. 기본 패키지 설치 및 프로그램 실행

```bash
# 기본 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python run.py

```

### 4. CUDA 기반 로컬 AI 문단 분석 설정 (선택 사항)

NVIDIA GPU(CUDA 코어) 환경이 구축된 시스템에서는 로컬 AI 모델(`mDeBERTa-v3-base-mnli-xnli`)을 활성화하여 문단 단락 구분을 최적화하고 더욱 매끄러운 EPUB 변환이 가능합니다.

1. **추가 의존성 패키지 설치**

```bash
pip install -r requirements_ai.txt

```

*(참고: `requirements_ai.txt` 내 `torch` 패키지 등은 사용 중인 시스템의 CUDA 버전에 맞춰 설치해야 합니다.)*

2. **`config.py` 파일 설정 변경**
`config.py` 파일 내 `USE_LOCAL_AI` 옵션을 `True`로 수정합니다.
```python
# config.py
DATA_FILE = "./data.json"
USE_LOCAL_AI = True  # CUDA 코어가 있는 그래픽카드 환경 시 True로 설정

```

## 면책 조항

본 프로그램은 개인 연구 및 학습 목적으로 제작된 웹 크롤링 및 번역 지원 도구입니다.

* 본 프로그램은 웹 소설 플랫폼(소설가가 되자, 카쿠요무 등)의 콘텐츠를 수집·번역하는 기능을 제공할 뿐이며, 수집된 콘텐츠의 저작권은 원작자 및 해당 플랫폼에 있습니다.
* 프로그램 사용으로 인해 발생하는 저작권 침해, IP 차단, 서비스 이용약관 위반 등 모든 법적·행정적 책임은 사용자 본인에게 있습니다.
* 개발자는 본 프로그램의 사용, 오용, 구동 불능 또는 번역 결과물로 인해 발생하는 직접적·간접적 손해에 대해 어떠한 법적 책임도 지지 않습니다.