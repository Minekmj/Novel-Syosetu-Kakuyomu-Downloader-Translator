<div align="center">

![](https://raw.githubusercontent.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/refs/heads/main/main.ico?v=2)

# MINE DOWNLOADER <br/> ~ Novel(Syosetu, Kakuyomu) Downloader & Translator ~

[![최신 버전](https://img.shields.io/github/v/release/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator?display_name=tag&sort=date)](https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/latest)

</div>

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

  * 자동 최신 버전 다운로드 기능 (.exe)

  * 업데이트 내역 알림이 기능

## 스크린샷

<div align="center">

![프로그램 메인](https://github.com/user-attachments/assets/8e9cdee6-0266-4583-8218-8a255d2ad514)

<p align="center"><i>프로그램 메인 화면 (목록 화면)</i></p>

![ai 번역](https://github.com/user-attachments/assets/94418491-d1ae-4a12-b8fc-8b913c99909a)

<p align="center"><i>ai 번역기 화면</i></p>

![나로우 파인더](https://github.com/user-attachments/assets/ae4733e2-c2f7-4230-99df-f212d099d965)

<p align="center"><i>나로우 파인더 메인 화면</i></p>

![카쿠요무 파인더](https://github.com/user-attachments/assets/516e64c8-72bf-4ee6-844b-0ba40ea43136)

<p align="center"><i>카쿠요무 파인더 메인 화면</i></p>

<img width="200" height="300" alt="Image" src="https://github.com/user-attachments/assets/8f60b459-851e-4489-9c6a-cb575fdffee9" />

<p align="center"><i>EPUB 출력 결과 표지 예시</i></p>

<h3 align="center"><i><b>스크린샷 기준 버전 (v1.1.2)</b></i></p>

</div>

<br/>
<br/>

## 스크린샷 - 테마

<details>

<summary><b>테마보기</b></summary>

<div align="center">

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/759f988c-8ef5-4045-bf29-1d01b4b25922" />

다크

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/62317ec9-6d0f-49c1-bb41-51b7cafe1380" />

라이트

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/84e177e3-e120-463f-a596-adc4af24ba43" />

블루

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/87c20051-7676-4d5d-b173-1a809a13682f" />

퍼플

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/93d7a504-9e85-446f-a04c-3c10907be86b" />

시안

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/bdefe340-4284-4123-a8a1-a0772e16076b" />

그린

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/25d4b2c6-f61c-4cef-ac15-7c8fd6b57ec0" />

레드

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/35a92352-aa22-416b-ae2f-75ca0d6af823" />

오렌지

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/a73e3a19-023e-4892-9ce2-5c3732784bd0" />

핑크

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/1f6913f1-4a44-4bf9-af21-d4c7d4de38a2" />

옐로우

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/358be041-cbbc-4670-a4a6-9e5be12540af" />

엠버

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/1ce1b656-1330-4681-9d52-858e9bc45331" />

틸

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/dd179041-5439-4f1f-a837-f21253add54d" />

인디고

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/22ca54e0-603e-40de-9d48-cb0fd3471deb" />

슬레이트

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/d204e4c8-07fb-4aa2-bc75-7dab03404a93" />

모노

<img width="952" height="732" alt="Image" src="https://github.com/user-attachments/assets/319c3f1d-3871-413f-8544-e1d18972cac7" />

OLED

<h3 align="center"><i><b>스크린샷 기준 버전 (v1.1.2)</b></i></p>

</details>

</div>

## 설치 및 실행 방법

*(현재 윈도우 만을 지원합니다. 추후 리눅스와 맥os를 지원할 예정입니다.)*

### 1. EXE 다운로드

[exe 다운로드 (v1.1.2)](https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/download/v1.1.2/Novel-Syosetu-Kakuyomu-Downloader-Translator-v1.1.2.exe)

혹은 아래와 같이

### 1. 저장소 클론

```bash
git clone https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator.git
cd novel-syosetu-kakuyomu-downloader-translator

```

### 2. 가상환경 생성 및 활성화

#### 필수 사항 : python3.12 이상

프로젝트 독립 환경 구성을 위해 가상환경 생성을 권장합니다.

* **Windows**:
```bash
#Command Prompt
python -m venv venv
venv\Scripts\activate.bat
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

*(https://pytorch.org/get-started/locally/ 접속, 필요한 버전 따로 찾아 설치)*

2. **`config.py` 파일 설정 변경**
`config.py` 파일 내 `USE_LOCAL_AI` 옵션을 `True`로 수정합니다.
```python
# config.py
DATA_FILE = "./data.json"
USE_LOCAL_AI = True  # CUDA 코어가 있는 그래픽카드 환경 시 True로 설정

```

## 의견 보내기

의견은 다음 링크

<b><i>

[의견 보내기 홈페이지 링크](https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/opinion/home.html)

</i></b>

로 보내주세요.

## 면책 조항

본 프로그램은 개인 연구 및 학습 목적으로 제작된 웹 크롤링 및 번역 지원 도구입니다.

* 본 프로그램은 웹 소설 플랫폼(소설가가 되자, 카쿠요무 등)의 콘텐츠를 수집·번역하는 기능을 제공할 뿐이며, 수집된 콘텐츠의 저작권은 원작자 및 해당 플랫폼에 있습니다.
* 프로그램 사용으로 인해 발생하는 저작권 침해, IP 차단, 서비스 이용약관 위반 등 모든 법적·행정적 책임은 사용자 본인에게 있습니다.
* 개발자는 본 프로그램의 사용, 오용, 구동 불능 또는 번역 결과물로 인해 발생하는 직접적·간접적 손해에 대해 어떠한 법적 책임도 지지 않습니다.