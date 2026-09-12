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
    <img src="https://img.shields.io/github/license/Minekmj/Novel-Syosetu-Kakuyomu-Downloader-Translator" alt="License">
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
  * 하위 플렛폼(녹턴, 미드나이트) 지원
  * 나로우 플렛폼은 이미지를 지원합니다.
* 카쿠요무(Kakuyomu) 작품 검색 및 회차 수집
* 작품의 전체 회차 일괄 다운로드
* 기존에 저장한 작품의 신규 회차 확인
* 작품 목록 및 다운로드 정보 관리
* 원문 형식의 다운로드 기능

### 번역

* Google Gemini API를 이용한 번역
  * 다중 모델 동시 사용 지원
  * 젬마 모델 지원
* Naver Papago를 이용한 일반 번역
* 청크 방식의 분할 번역
* 사용자 지정 번역 프롬포트 설정 가능
* 동적 작품별 용어집으로 번역 일관성 기능
  * 작품별로 각각 자동 지정
* 완료된 번역을 검사하여 일본어를 한국어로 대체하는 검사 기능

### EPUB 변환

수집한 TXT 또는 번역된 텍스트를 EPUB 전자책으로 변환할 수 있습니다.

* TXT → EPUB 변환
* EPUB CSS 스타일 적용
* 작품 제목 및 정보 반영
* 표지 이미지 적용
* 전자책에 맞춘 문단 및 줄바꿈 처리
* 로컬 AI 모델을 이용한 문단 구분 최적화
* 나로우 플렛폼 이미지 지원

로컬 AI 기능을 사용하는 경우 `mDeBERTa-v3-base-mnli-xnli` 모델을 이용하여 텍스트의 문단 구분을 보조합니다.

### 프로그램 UI

* PySide6 기반 Desktop GUI
* 별도의 Tkinter 기반 시작 화면
* 다운로드 및 번역 작업의 진행 상황 표시
* 멀티스레드 기반 작업 처리
* 16가지 커스텀 테마
* QSS 기반 UI 스타일
* 최신 버전 EXE 자동 다운로드

## 다운로드

### Windows EXE

Python이나 별도의 개발 환경을 설치하지 않고 바로 실행하려면 EXE 버전을 사용할 수 있습니다.

<a href="https://minekmj.github.io/Novel-Syosetu-Kakuyomu-Downloader-Translator/latest.html">
  <img src="https://img.shields.io/badge/Download-Latest%20Version-2ea44f?style=for-the-badge&logo=windows&logoColor=white" alt="Download Latest Version">
</a>

<br/>

> EXE 버전은 별도의 Python 설치 없이 사용할 수 있습니다.

<h2/>

## 설치 및 실행

현재 Windows 환경을 지원합니다.

### 요구 사항

* Windows
* Python 3.12 이상

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
