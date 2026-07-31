# ECOS·FRED 월별 데이터 수집기와 GitHub 자동화 설계

## 1. 목적

터미널에서 명령 한 번으로 최근 5년의 한국은행 기준금리, 미국 철강
생산자물가지수, 연준 목표금리 범위 중간값을 수집한다. API가 반환한 원본 JSON을 보존하고, 지표를
월 기준으로 결합한 CSV를 만든다.

같은 프로그램을 GitHub Actions에서도 매월 1일 오전 9시 30분
`Asia/Seoul` 기준으로 실행한다. 실행할 때마다 새 원본 JSON을 추가하고
최신 CSV를 수현님 공개 저장소에 자동 커밋한다.

이 프로젝트의 첫 번째 성공 기준은 사용자가 다음 명령을 직접 실행하고,
생성된 원본과 월별 표의 위치를 설명할 수 있는 것이다.

```bash
python3 collect_data.py
```

## 2. 사용자와 운영 환경

- 사용자는 프로그래밍과 터미널을 처음 접하는 입문자이다.
- 사용자에게 보이는 진행 상황과 오류 메시지는 쉬운 한국어로 작성한다.
- 실행 전후에 무엇을 읽고, 무엇을 만들며, 외부에 어떤 요청을 보내는지
  README에서 설명한다.
- 작업 경로는 `/Users/suhyeonhong/Documents/GitHub/ToSuhyeon`이다.
- 지원 기준은 macOS에 설치된 Python 3.9.6 이상이다.
- Python 표준 라이브러리만 사용하며 외부 패키지를 설치하지 않는다.
- GitHub 연결 계정은 `suhyeonhong-bit`이다.
- 자동화 대상은 원본 저장소를 fork해 만드는 공개 저장소
  `suhyeonhong-bit/ToSuhyeon`이다.

## 3. 범위

### 포함

- `.env`에서 `FRED_API_KEY`와 `ECOS_API_KEY` 읽기
- 실행 월에서 5년 전 같은 월부터 실행 월까지의 월별 데이터 요청
- FRED `WPU1017` 미국 철강 생산자물가지수 수집
- FRED `DFEDTARU`·`DFEDTARL` 연준 목표금리 상단·하단 수집 및 월별 중간값 계산
- ECOS `722Y001` 통계표의 `0101000` 한국은행 기준금리 수집
- 성공적으로 받은 API 응답을 원본 JSON으로 별도 보관
- 네 지표를 `YYYY-MM` 기준으로 결합한 CSV 생성
- 설정, 응답 파싱, 월별 결합, 오류 처리를 자동 테스트
- 초보자용 실행 및 결과 확인 방법을 README에 추가
- GitHub Actions에서 매월 1일 오전 9시 30분 `Asia/Seoul` 기준으로 실행
- GitHub 화면에서 수동으로 실행할 수 있는 `workflow_dispatch` 제공
- 자동 테스트 통과 후 생성 데이터만 GitHub에 자동 커밋

### 제외

- 노션 또는 Google Sheets 연동
- 그래프와 대시보드
- 상관관계 분석이나 투자 판단
- 5년을 초과하는 기간 선택 기능
- 명령행 옵션과 설정 화면
- 원본 `yealu/ToSuhyeon` 저장소 변경
- GitHub Actions가 코드나 문서를 자동 수정하는 기능

## 4. 데이터 정의

### FRED 철강 생산자물가지수

- 제공처: Federal Reserve Bank of St. Louis FRED API
- 시리즈 ID: `WPU1017`
- 주기: 월
- 요청 형식: JSON
- 값의 의미: 미국 철강 관련 생산자물가지수
- 누락 표기 `.`은 숫자로 바꾸지 않고 결측값으로 처리한다.

요청은
`https://api.stlouisfed.org/fred/series/observations`에 다음 파라미터를
보낸다.

- `series_id=WPU1017`
- `file_type=json`
- `observation_start=YYYY-MM-01`
- `observation_end=YYYY-MM-DD`
- `sort_order=asc`
- `api_key=<FRED_API_KEY>`

### ECOS 한국은행 기준금리

- 제공처: 한국은행 ECOS Open API
- 통계표 코드: `722Y001`
- 항목 코드: `0101000`
- 항목명: 한국은행 기준금리
- 주기: 월(`M`)
- 단위: %
- 요청 형식: JSON

요청 경로는 다음 형식을 사용한다.

```text
https://ecos.bok.or.kr/api/StatisticSearch/<ECOS_API_KEY>/json/kr/1/1000/722Y001/M/YYYYMM/YYYYMM/0101000
```

### FRED 연준 목표금리

- 시리즈 ID: `DFEDTARU`(상단), `DFEDTARL`(하단)
- 두 시리즈가 모두 존재하는 월만 `(DFEDTARU + DFEDTARL) / 2`로 계산한다.
- 결과 컬럼은 `us_fed_target_rate_percent`이며 결측 월은 빈칸으로 둔다.

### 기간 계산

- 시작 월은 실행 시점의 달에서 정확히 5년 전 같은 달이다.
- 종료 월은 실행 시점의 달이다.
- 양 끝 월을 모두 포함하므로 최대 61개 월이 생성될 수 있다.
- 기관의 발표 시차 때문에 종료 월 데이터가 아직 없을 수 있다.
- 발표되지 않은 값을 추측하거나 이전 값으로 채우지 않는다.

## 5. 파일 구조와 책임

```text
ToSuhyeon/
├── .env
├── .gitignore
├── collect_data.py
├── .github/
│   └── workflows/
│       └── collect-weekly.yml
├── collector/
│   ├── __init__.py
│   ├── config.py
│   ├── dates.py
│   ├── fred.py
│   ├── ecos.py
│   ├── transform.py
│   └── storage.py
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   └── processed/
│       └── .gitkeep
├── tests/
│   ├── fixtures/
│   │   ├── fred_observations.json
│   │   └── ecos_base_rate.json
│   ├── test_config.py
│   ├── test_dates.py
│   ├── test_fred.py
│   ├── test_ecos.py
│   ├── test_transform.py
│   └── test_storage.py
└── README.md
```

- `collect_data.py`: 사용자가 실행하는 진입점이다. 각 단계를 순서대로
  호출하고 진행 상황과 최종 경로를 출력한다.
- `.github/workflows/collect-weekly.yml`: 월별 예약·수동 실행, 테스트, 데이터
  수집, 생성 데이터 커밋 순서를 정의한다.
- `collector/config.py`: `.env`를 읽고 두 필수 키가 존재하는지 검사한다.
- `collector/dates.py`: 실행일을 기준으로 5년 수집 범위를 계산한다.
- `collector/fred.py`: FRED 요청을 만들고 응답에서 월별 값을 추출한다.
- `collector/ecos.py`: ECOS 요청을 만들고 응답에서 월별 기준금리를
  추출한다.
- `collector/transform.py`: 두 월별 데이터 집합을 월의 합집합 기준으로
  결합한다.
- `collector/storage.py`: 원본 JSON과 최종 CSV를 안전하게 저장한다.
- `tests/fixtures/`: 실제 키나 네트워크가 필요 없는 작은 예시 응답이다.

각 모듈은 파일 이름에 적힌 한 가지 책임만 가진다. 네트워크 요청과 응답
파싱을 분리해 파싱 테스트가 실제 API를 호출하지 않게 한다.

## 6. 실행 흐름

1. `collect_data.py`가 프로젝트 루트의 `.env`를 찾는다.
2. 두 키의 존재와 비어 있지 않은 값을 확인한다.
3. 현재 날짜를 기준으로 시작 월과 종료 월을 계산한다.
4. FRED에 `WPU1017`, `DFEDTARU`, `DFEDTARL` 관측값을 요청한다.
5. 세 FRED 응답이 정상이라면 원본 JSON을 저장하고 월별 값을 파싱한다.
6. 두 연준 시리즈의 월별 중간값을 계산한다.
7. ECOS에 월별 한국은행 기준금리를 요청한다.
8. ECOS 응답이 정상이라면 원본 JSON을 저장하고 월별 값을 파싱한다.
9. 네 데이터의 모든 월을 모아 시간 오름차순으로 정렬한다.
10. 한쪽에만 있는 월은 다른 지표 칸을 비운다.
11. 완성된 행을 임시 CSV에 쓴 뒤 기존 최종 CSV와 원자적으로 교체한다.
12. 수집 건수와 생성된 파일 경로를 출력하고 종료한다.

사용자 출력 예시는 다음과 같다.

```text
[1/6] API 키를 확인했습니다.
[2/6] FRED 철강 PPI 60건을 수집했습니다.
[3/6] FRED 연준 목표금리 상단 60건을 수집했습니다.
[4/6] FRED 연준 목표금리 하단 60건을 수집했습니다.
[5/6] ECOS 기준금리 60건을 수집했습니다.
[6/6] 월별 CSV 60행을 저장했습니다.
완료: data/processed/monthly_indicators.csv
```

## 7. 저장 형식

### 원본 JSON

파일명은 수집 출처와 UTC 실행 시각을 포함한다.

```text
data/raw/fred_WPU1017_20260730T013000Z.json
data/raw/fred_DFEDTARU_20260730T013000Z.json
data/raw/fred_DFEDTARL_20260730T013000Z.json
data/raw/ecos_base_rate_20260730T013000Z.json
```

- API가 반환한 JSON 구조를 가공하지 않고 UTF-8로 저장한다.
- 정상 JSON 응답만 저장한다.
- 실행할 때마다 새 파일을 만들며 이전 원본을 덮어쓰지 않는다.
- API 키와 API 키가 포함된 요청 URL은 파일에 추가하지 않는다.

### 결합 CSV

경로는 `data/processed/monthly_indicators.csv`로 고정한다.

```csv
month,korea_base_rate_percent,us_steel_ppi_index,us_fed_target_rate_percent
2021-07,0.50,251.3,0.125
2021-08,0.75,257.8,0.125
```

- 인코딩은 Excel 호환성을 위해 `utf-8-sig`를 사용한다.
- `month`는 `YYYY-MM` 형식이다.
- 값은 API가 제공한 소수 표현을 유지한다.
- 결측값은 빈 문자열로 쓴다.
- 새 CSV가 완전히 작성된 경우에만 기존 CSV를 교체한다.

생성 데이터는 GitHub 자동화가 저장소에 축적해야 하므로 Git에서 제외하지
않는다. 로컬에서 수동 실행하면 `git status`에 새 원본과 변경된 CSV가
나타날 수 있으며, README에서 이것이 정상임을 설명한다. `.env`,
`__pycache__/`, `*.pyc`만 `.gitignore`로 제외한다.

## 8. 보안

- `.env`는 계속 Git에서 제외한다.
- GitHub에서는 저장소의 Actions secrets에 `FRED_API_KEY`와
  `ECOS_API_KEY`를 별도로 등록한다.
- 키 값을 코드, 테스트, fixture, README에 기록하지 않는다.
- 키 값이나 키가 포함된 URL을 출력하거나 예외 메시지에 포함하지 않는다.
- HTTP 오류를 사용자에게 보여줄 때 원본 예외 문자열 대신 기관명,
  상태 코드, 안전한 한국어 설명만 사용한다.
- 네트워크 모듈은 키를 저장 모듈이나 변환 모듈에 전달하지 않는다.
- 원본 응답에 현재 키 문자열이 포함된 경우 저장을 거부한다.
- GitHub 워크플로는 `contents: write`만 요청하고 다른 권한은 요청하지
  않는다.
- 예약 및 수동 실행에만 secrets를 사용하며 pull request 실행 조건은
  추가하지 않는다.

## 9. 오류 처리

모든 사용자 오류는 `수집 실패:`로 시작하는 쉬운 한국어 한 문장으로
보여주며 프로그램은 종료 코드 `1`로 끝난다. 성공 시 종료 코드는 `0`이다.

- `.env` 없음: 정확한 생성 위치를 안내한다.
- 필수 키 없음 또는 빈 값: 빠진 변수 이름만 보여준다.
- 타임아웃과 연결 실패: 실패한 기관명과 재시도 안내를 보여준다.
- HTTP 오류: 상태 코드만 보여주고 요청 URL은 숨긴다.
- FRED `error_code`: 안전한 오류 설명으로 바꿔 보여준다.
- ECOS `RESULT` 오류: 오류 코드는 보여주되 응답 전체는 출력하지 않는다.
- 응답 JSON 손상: 해당 기관 응답 형식이 올바르지 않다고 알린다.
- 예상 시리즈·항목 불일치: 잘못된 데이터를 저장하지 않고 중단한다.
- 유효한 월별 값 0건: 최종 CSV를 교체하지 않고 중단한다.
- 일부 월의 값 누락: 빈칸으로 유지하고 정상 완료한다.

FRED가 성공하고 ECOS가 실패한 경우 이미 받은 FRED 원본은 남길 수 있지만,
최종 CSV는 교체하지 않는다.

GitHub Actions에서 테스트나 수집이 실패하면 커밋 단계를 실행하지 않는다.
이전 데이터는 그대로 유지되고 해당 실행은 GitHub Actions 화면에서 실패로
표시된다. 같은 워크플로 실행이 겹치지 않도록 하나의 concurrency group을
사용한다.

## 10. 테스트

테스트는 Python 표준 `unittest`로 실행한다.

```bash
python3 -m unittest discover -s tests -v
```

테스트는 실제 `.env`, 실제 키, 실제 네트워크를 사용하지 않는다.
네트워크 함수에 가짜 응답을 주입하고 fixture JSON으로 다음 동작을
검증한다.

- `.env`의 주석과 빈 줄을 무시하고 필수 키를 읽는다.
- `.env`가 없거나 키가 비어 있으면 키 값을 노출하지 않고 실패한다.
- 실행일에서 5년 전 시작 월을 계산한다.
- FRED의 정상 값과 `.` 결측값을 구분한다.
- FRED 오류 응답을 정상 데이터로 처리하지 않는다.
- ECOS의 `722Y001 / 0101000 / M` 행만 읽는다.
- ECOS `RESULT` 오류를 정상 데이터로 처리하지 않는다.
- 두 데이터의 월 합집합을 시간순으로 결합한다.
- 한쪽에 없는 월은 빈칸으로 남긴다.
- CSV 헤더, 행 순서, `utf-8-sig` 인코딩이 정확하다.
- 저장 실패 시 기존 최종 CSV가 유지된다.
- 오류 문자열과 저장 파일에 테스트용 비밀 값이 남지 않는다.

자동 테스트가 모두 통과한 뒤 실제 API로 한 번 실행한다. 실제 실행에서는
다음을 확인한다.

- 원본 JSON 두 개가 생성된다.
- 최종 CSV가 생성된다.
- CSV에 최근 5년 범위의 월별 행이 있다.
- 키 값이 터미널 출력, 생성 파일, `git status`에 나타나지 않는다.

## 11. GitHub Actions 자동화

### 저장소 준비

1. 원본 `yealu/ToSuhyeon`을 `suhyeonhong-bit/ToSuhyeon`으로 fork한다.
2. 로컬 저장소의 `origin`을 수현님 fork로 변경한다.
3. 원본 주소는 `upstream` 원격으로 등록해 출처를 보존한다.
4. 로컬 커밋을 수현님 fork의 기본 브랜치 `main`으로 push한다.
5. 수현님 fork의 Actions secrets에 두 API 키를 사용자가 직접 입력한다.

키 값은 에이전트 대화창이나 명령 인자에 입력하지 않는다. GitHub 웹 화면의
secret 입력란에 사용자가 직접 붙여넣는다.

### 실행 조건

워크플로는 다음 두 조건으로 실행한다.

```yaml
on:
  schedule:
    - cron: "30 0 1 * *"
      timezone: "Asia/Seoul"
  workflow_dispatch:
```

- 예약 목표는 매월 1일 오전 9시 30분 한국 시간이다.
- GitHub 서버 부하에 따라 실제 시작은 몇 분 늦어질 수 있다.
- `workflow_dispatch`는 예약 시간을 기다리지 않고 검증할 수 있는 수동
  실행 버튼을 만든다.
- 예약 실행은 GitHub 기본 브랜치의 최신 커밋을 사용한다.

### 작업 순서와 권한

워크플로는 다음 순서로 동작한다.

1. `ubuntu-latest` 임시 실행 환경을 준비한다.
2. 수현님 fork의 기본 브랜치를 checkout한다.
3. Python 3.9를 준비한다.
4. `python3 -m unittest discover -s tests -v`를 실행한다.
5. Actions secrets를 환경 변수로 전달하고 `python3 collect_data.py`를
   실행한다.
6. `data/raw`와 `data/processed` 변경만 stage한다.
7. 변경이 있으면 GitHub Actions 봇 이름으로 커밋하고 `main`에 push한다.
8. 변경이 없으면 성공으로 끝내고 빈 커밋을 만들지 않는다.

워크플로는 다음 최소 권한만 사용한다.

```yaml
permissions:
  contents: write
```

GitHub가 실행마다 제공하는 저장소 범위의 `GITHUB_TOKEN`으로 push한다.
개인 액세스 토큰은 만들지 않는다. 자동화가 만든 push가 같은 워크플로를
다시 실행하게 하는 `push` 트리거도 추가하지 않는다.

### 자동 커밋

- 커밋 메시지: `data: collect monthly indicators YYYY-MM-DD`
- 커밋 대상: `data/raw/*.json`, `data/processed/monthly_indicators.csv`
- 커밋 제외: 코드, 문서, `.env`, 기타 사용자 파일
- 원본 JSON은 실행할 때마다 추가한다.
- 최종 CSV는 최신 5년 데이터로 교체한다.
- 공개 저장소이므로 커밋된 JSON과 CSV는 누구나 볼 수 있다.

### 첫 실행 검증과 운영상 예외

설정 직후 `Run workflow`로 한 번 실행해 다음을 확인한다.

- 테스트 단계 성공
- FRED와 ECOS 요청 성공
- secrets가 로그에 노출되지 않음
- 원본 JSON 두 개와 CSV 한 개 생성
- 데이터 파일만 포함한 자동 커밋 생성

ECOS가 GitHub 클라우드 실행 환경의 요청을 제한하면 워크플로는 데이터를
커밋하지 않고 실패한다. 실제 오류를 확인한 뒤 로컬 Mac 예약 실행으로
전환하거나 ECOS만 다른 허용 환경에서 실행하는 새 설계를 별도로 승인받는다.

공개 저장소의 예약 워크플로는 장기간 저장소 활동이 없으면 GitHub 정책에
따라 비활성화될 수 있다. 정상적인 주간 자동 커밋이 계속되면 저장소 활동도
이어진다. 실패가 장기간 지속되면 Actions 화면에서 워크플로 상태를
확인한다.

## 12. 문서화

README에 다음 내용을 초보자 관점으로 추가한다.

- 이 프로그램이 하는 일
- API 요청이 외부에 보내는 정보와 로컬에 만드는 파일
- `.env` 준비 상태를 확인하는 방법
- 프로그램 실행 명령
- 테스트 실행 명령
- JSON 원본과 CSV 결과를 여는 방법
- 발표 시차와 빈칸의 의미
- 키 오류, 인터넷 오류, API 오류에 대한 대응
- GitHub, fork, commit, Actions를 설명하는 초보자용 용어 안내
- 로컬 `.env`와 GitHub Actions secrets의 차이
- 수현님 fork 생성과 원격 저장소 연결 방법
- Actions secrets 등록 방법
- `Run workflow` 수동 검증 방법
- 예약 실행 시각과 지연 가능성
- 자동 커밋되는 파일과 공개 범위
- 실패한 자동 실행을 GitHub 화면에서 확인하는 방법
- 로컬 수동 실행은 자동으로 GitHub에 업로드되지 않는다는 설명

## 13. 완료 기준

- Python 3.9.6에서 외부 패키지 없이 실행된다.
- 모든 자동 테스트가 통과한다.
- 실제 ECOS와 FRED 요청이 성공한다.
- 최근 5년의 원본 JSON 두 개와 월별 CSV가 생성된다.
- API 키가 코드, 문서, 테스트, 출력, 생성 데이터, Git 추적 파일에 없다.
- 사용자가 실행 명령과 결과 파일의 의미를 README만 보고 이해할 수 있다.
- `suhyeonhong-bit/ToSuhyeon` 공개 fork의 기본 브랜치에 코드와
  워크플로가 있다.
- GitHub Actions secrets 두 개가 사용자에 의해 등록되어 있다.
- `Run workflow` 수동 실행에서 테스트, 수집, 자동 커밋이 성공한다.
- 예약 설정이 매월 1일 오전 9시 30분 `Asia/Seoul`을 사용한다.
- 자동 커밋에는 `data/raw`와 `data/processed` 파일만 포함된다.
