<div align="center">

<img src="https://raw.githubusercontent.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/refs/heads/main/main.ico?v=2" width="128" height="128">

# MINE DOWNLOADER

### Novel (Syosetu · Kakuyomu) Downloader & Translator

<p>
  <a href="https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/latest">
    <img src="https://img.shields.io/github/v/release/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator?display_name=tag&sort=date" alt="Latest Release">
  </a>
  
  <a href="https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases">
    <img src="https://img.shields.io/github/downloads/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/total" alt="Downloads">
  </a>

  <a href="https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator">
    <img src="https://img.shields.io/github/stars/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator" alt="Stars">
  </a>
</p>

<p>
일본 웹소설 플랫폼의 작품을 검색하고 회차를 수집한 뒤,<br>
번역 및 EPUB 전자책 변환까지 한 곳에서 처리할 수 있는 Windows Desktop Application입니다.
</p>

<br/>

<a href="https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/latest.html">
  <img src="https://img.shields.io/badge/Download-Latest%20Version-2ea44f?style=for-the-badge&logo=windows&logoColor=white" alt="Download Latest Version">
</a>

</div>

<h2/>

## 소개

<b>MINE DOWNLOADER</b>는 일본 웹소설 플랫폼인 <b>소설가가 되자(Syosetu)</b>와 <b>카쿠요무(Kakuyomu)</b>를 대상으로 작품 검색, 회차 수집, 신규 회차 확인, 번역, EPUB 변환 등을 하나의 프로그램에서 처리할 수 있도록 만든 통합형 Desktop Application입니다.

웹에서 작품을 하나씩 확인하고 다운로드하는 과정을 줄이고, 수집한 소설을 번역하거나 EPUB 전자책 형태로 정리할 수 있도록 구성되어 있습니다.

현재 Windows 환경을 지원하며, 향후 Linux 및 macOS 지원을 고려하고 있습니다.

## 주요 기능

### 웹소설 검색 및 수집

* 내부 태그 및 카테고리를 이용한 작품 검색
* 작품 상세 정보 확인
* 소설가가 되자(Syosetu) 작품 검색 및 회차 수집
* 카쿠요무(Kakuyomu) 작품 검색 및 회차 수집
* 작품의 전체 회차 일괄 다운로드
* 기존에 저장한 작품의 신규 회차 확인
* 작품 목록 및 다운로드 정보 관리

### 번역

* Google Gemini API를 이용한 번역
* Naver Papago API 연동
* 긴 소설을 여러 단위로 나누어 처리하는 번역 방식
* 번역 결과를 EPUB 변환 과정과 연계 가능

### EPUB 변환

수집한 TXT 또는 번역된 텍스트를 EPUB 전자책으로 변환할 수 있습니다.

* TXT → EPUB 변환
* EPUB CSS 스타일 적용
* 작품 제목 및 정보 반영
* 표지 이미지 적용
* 전자책에 맞춘 문단 및 줄바꿈 처리
* 로컬 AI 모델을 이용한 문단 구분 최적화

로컬 AI 기능을 사용하는 경우 `mDeBERTa-v3-base-mnli-xnli` 모델을 이용하여 텍스트의 문단 구분을 보조합니다.

### 프로그램 UI

* PySide6 기반 Desktop GUI
* 별도의 Tkinter 기반 시작 화면
* 다운로드 및 번역 작업의 진행 상황 표시
* 멀티스레드 기반 작업 처리
* 16가지 커스텀 테마
* QSS 기반 UI 스타일
* 최신 버전 EXE 자동 다운로드

## 스크린샷

<div align="center">

<img src="https://github.com/user-attachments/assets/8e9cdee6-0266-4583-8218-8a255d2ad514" alt="프로그램 메인 화면">

<p><i>프로그램 메인 화면 · 작품 및 다운로드 목록</i></p>

<img src="https://github.com/user-attachments/assets/94418491-d1ae-4a12-b8fc-8b913c99909a" alt="AI 번역 화면">

<p><i>번역 화면</i></p>

<img src="https://github.com/user-attachments/assets/ae4733e2-c2f7-4230-99df-f212d099d965" alt="나로우 파인더">

<p><i>소설가가 되자 작품 검색</i></p>

<img src="https://github.com/user-attachments/assets/516e64c8-72bf-4ee6-844b-0ba40ea43136" alt="카쿠요무 파인더">

<p><i>카쿠요무 작품 검색</i></p>

<img width="200" height="300" src="https://github.com/user-attachments/assets/8f60b459-851e-4489-9c6a-cb575fdffee9" alt="EPUB 표지">

<p><i>EPUB 출력 결과 예시</i></p>

<br>

<p><b>스크린샷 기준 버전 · v1.1.2</b></p>

</div>

<h2/>

## 테마

프로그램은 기본 테마 외에도 다양한 색상의 커스텀 테마를 제공합니다.

<details>
<summary><b>테마 보기</b></summary>

<br>

<div align="center">

<img width="952" height="732" src="https://github.com/user-attachments/assets/759f988c-8ef5-4045-bf29-1d01b4b25922" alt="Dark Theme">

<p><b>Dark</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/62317ec9-6d0f-49c1-bb41-51b7cafe1380" alt="Light Theme">

<p><b>Light</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/84e177e3-e120-463f-a596-adc4af24ba43" alt="Blue Theme">

<p><b>Blue</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/87c20051-7676-4d5d-b173-1a809a13682f" alt="Purple Theme">

<p><b>Purple</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/93d7a504-9e85-446f-a04c-3c10907be86b" alt="Cyan Theme">

<p><b>Cyan</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/bdefe340-4284-4123-a8a1-a0772e16076b" alt="Green Theme">

<p><b>Green</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/25d4b2c6-f61c-4cef-ac15-7c8fd6b57ec0" alt="Red Theme">

<p><b>Red</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/35a92352-aa22-416b-ae2f-75ca0d6af823" alt="Orange Theme">

<p><b>Orange</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/a73e3a19-023e-4892-9ce2-5c3732784bd0" alt="Pink Theme">

<p><b>Pink</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/1f6913f1-4a44-4bf9-af21-d4c7d4de38a2" alt="Yellow Theme">

<p><b>Yellow</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/358be041-cbbc-4670-a4a6-9e5be12540af" alt="Amber Theme">

<p><b>Amber</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/1ce1b656-1330-4681-9d52-858e9bc45331" alt="Teal Theme">

<p><b>Teal</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/dd179041-5439-4f1f-a837-f21253add54d" alt="Indigo Theme">

<p><b>Indigo</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/22ca54e0-603e-40de-9d48-cb0fd3471deb" alt="Slate Theme">

<p><b>Slate</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/d204e4c8-07fb-4aa2-bc75-7dab03404a93" alt="Mono Theme">

<p><b>Mono</b></p>

<img width="952" height="732" src="https://github.com/user-attachments/assets/319c3f1d-3871-413f-8544-e1d18972cac7" alt="OLED Theme">

<p><b>OLED</b></p>

<br>

<p><b>스크린샷 기준 버전 · v1.1.2</b></p>

</div>

</details>

## 다운로드

### Windows EXE

Python이나 별도의 개발 환경을 설치하지 않고 바로 실행하려면 EXE 버전을 사용할 수 있습니다.

<div align="center">

<a href="https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/latest.html">
  <img src="https://img.shields.io/badge/Download-Latest%20Version-2ea44f?style=for-the-badge&logo=windows&logoColor=white" alt="Download Latest Version">
</a>

<br/>

<br/>

<br/>

<a href="https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/latest">
  <img src="https://img.shields.io/badge/View%20All%20Releases-GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="View All Releases">
</a>

</div>

> EXE 버전은 별도의 Python 설치 없이 사용할 수 있습니다.

<h2/>

## 설치 및 실행

현재 Windows 환경을 지원합니다.

### 요구 사항

* Windows
* Python 3.12 이상
* 인터넷 연결
* 번역 API 사용 시 해당 API의 사용 권한 및 API Key

### 1. 저장소 클론

```bash
git clone https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator.git
cd Novel-Syosetu-Kakuyomu-Downloader-Translator
```

### 2. 가상환경 생성

Python 프로젝트의 독립적인 환경 구성을 위해 가상환경 사용을 권장합니다.

**Windows Command Prompt**

```bash
python -m venv venv
venv\Scripts\activate.bat
```

**Windows PowerShell**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. 기본 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 프로그램 실행

```bash
python run.py
```

<h2/>

## 로컬 AI 문단 분석

EPUB 변환 과정에서 문단 구분과 줄바꿈을 보다 자연스럽게 처리하고 싶은 경우 로컬 AI 기능을 사용할 수 있습니다.

이 기능은 `mDeBERTa-v3-base-mnli-xnli` 모델을 사용하며, CUDA를 지원하는 NVIDIA GPU 환경에서 사용하는 것을 권장합니다.

### 1. 추가 패키지 설치

```bash
pip install -r requirements_ai.txt
```

`requirements_ai.txt`에 포함된 PyTorch 버전은 사용 중인 CUDA 환경에 맞춰 조정해야 할 수 있습니다.

PyTorch의 CUDA 지원 버전은 다음 페이지에서 확인할 수 있습니다.

https://pytorch.org/get-started/locally/

### 2. 로컬 AI 활성화

`config.py`에서 다음 옵션을 변경합니다.

```python
DATA_FILE = "./data.json"
USE_LOCAL_AI = True
```

`USE_LOCAL_AI`를 `True`로 설정하면 EPUB 변환 과정에서 로컬 AI 기반 문단 분석 기능이 활성화됩니다.

> 로컬 AI 기능은 선택 사항이며, 일반적인 다운로드 및 EPUB 변환 기능을 사용하는 데 반드시 필요한 것은 아닙니다.

<h2/>

## 의견 및 문제 제보

프로그램 사용 중 발견한 문제나 개선 사항, 기능 추가 요청 등이 있다면 의견 페이지를 통해 알려주세요.

<div align="center">

<a href="https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/opinion/home.html">
  <img src="https://img.shields.io/badge/Send%20Feedback-의견%20보내기-5865F2?style=for-the-badge" alt="Send Feedback">
</a>

</div>

<h2/>

## 지원 플랫폼

| 플랫폼     | 지원 여부 |
| ------- | ----- |
| Windows | O    |
| Linux   | X    |
| macOS   | X    |

<h2/>

## 면책 조항

본 프로그램은 개인 연구 및 학습을 목적으로 제작된 웹 크롤링 및 번역 지원 도구입니다.

* 본 프로그램은 웹소설 플랫폼의 콘텐츠를 수집하고 번역할 수 있는 기능을 제공하지만, 수집되는 콘텐츠의 저작권은 해당 원작자 및 권리자에게 있습니다.
* 프로그램을 이용하여 다운로드하거나 생성한 콘텐츠의 이용에 대한 책임은 사용자에게 있습니다.
* 각 웹소설 플랫폼의 이용약관, robots.txt, API 정책 및 기타 관련 규정을 사용자가 직접 확인하고 준수해야 합니다.
* 프로그램의 사용으로 인해 발생할 수 있는 저작권 침해, 서비스 이용 제한, IP 차단, 계정 제한 및 기타 법적·행정적 문제에 대해 개발자는 책임을 지지 않습니다.
* 번역 기능을 통해 생성된 결과물의 정확성이나 완전성을 보장하지 않습니다.
* 프로그램의 사용 또는 번역 결과물로 인해 발생하는 직접적·간접적 손해에 대해 개발자는 책임을 지지 않습니다.

<h2> </h2>

<div align="center">

### MINE DOWNLOADER

Novel Downloader & Translator

<sub>Syosetu · Kakuyomu</sub>

<br>
<br>

<a href="https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator/releases/latest">Releases</a>
  ·   <a href="https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/opinion/home.html">Feedback</a>
  ·   <a href="https://github.com/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator">GitHub</a>

</div>
