# ReviewFlow (GitHub PR 기반 LangGraph 다중 LLM 자동 코드 리뷰 및 토큰 최적화 파이프라인)

AWS Lambda/API Gateway 및 FastAPI 기반의 **GitHub Webhook 실시간 비동기 처리**, **LangGraph 기반 멀티 에이전트 상태 머신(State Machine)**, **Redis Commit SHA 캐싱을 통한 중복 실행 방지**, **PostgreSQL 기반 리뷰 이력 및 토큰/비용 추적**을 결합한 서버리스 AI 코드 리뷰 파이프라인입니다.

## 1. 프로젝트 개요

### 1-1. 기획 배경

#### 수동 코드 리뷰의 반복성 및 병목 현상

팀 내에서 Pull Request(PR)가 생성될 때마다 코드 컨벤션, 가독성, 보안 취약점, 성능 문제 등을 리뷰어가 직접 확인하는 과정에서 반복적인 공수가 발생했습니다.

#### 전체 코드 변경점 AI 분석에 따른 비용 및 타임아웃 문제

기존의 동기식 AI 코드 리뷰 구조에서는 다음과 같은 문제가 발생할 수 있었습니다.

* **Webhook Timeout**

  * GitHub Webhook 수신 시 대규모 Diff를 LLM에 동기적으로 전달
  * LLM 분석 시간이 길어질 경우 Webhook 응답이 지연
  * GitHub Webhook 응답 제한 시간 내 처리하지 못하는 문제 발생

* **불필요한 LLM 호출**

  * 동일한 Commit에 대해 Webhook 이벤트가 반복적으로 발생
  * 변경 사항이 없는 경우에도 LLM이 재호출
  * 불필요한 Prompt / Completion Token 소비 및 API 비용 증가

#### 해결 방향

1. **서버리스 비동기 Webhook 파이프라인**

   * FastAPI 기반 Webhook 수신
   * HMAC SHA256 서명 검증
   * Webhook 요청 수신 후 즉시 `200 OK` 반환
   * 실제 AI 리뷰 작업은 백그라운드 이벤트로 분리

2. **LangGraph 기반 멀티 LLM 오케스트레이션**

   단일 LLM에 모든 리뷰 작업을 요청하는 대신 리뷰 목적에 따라 모델을 분리했습니다.

   | 리뷰 영역       | LLM          |
   | ----------- | ------------ |
   | 분류 / 코드 스타일 | Gemini Flash |
   | 보안 취약점      | Claude 3.5   |
   | 성능 최적화      | GPT-4o       |

   LangGraph를 통해 각 리뷰 Agent의 실행 흐름과 상태를 관리하고 최종 결과를 통합합니다.

3. **Redis + PostgreSQL 기반 비용 및 이력 관리**

   * Redis에 Commit SHA를 저장하여 중복 리뷰 실행 방지
   * LLM 호출별 Token 사용량 측정
   * 리뷰 결과 및 비용 정보를 PostgreSQL에 영속화
   * 리뷰 이력 및 API 사용량 추적

---

### 1-2. 프로젝트 목표

#### 실시간 PR 이벤트 연동

* GitHub Pull Request Webhook 이벤트 실시간 수신
* HMAC SHA256 서명 검증
* Webhook 수신과 AI 분석 작업 분리

#### LangGraph 기반 State Machine 구축

* 리뷰 단계를 Graph 구조로 정의
* Agent별 독립적인 리뷰 수행
* `ReviewState`를 통한 Agent 간 상태 공유
* 리뷰 결과 통합

#### 비용 최적화

* Commit SHA 기반 Redis 캐싱
* 이미 분석된 Commit에 대한 LLM 호출 차단
* Prompt / Completion Token 사용량 측정
* PostgreSQL 기반 비용 및 리뷰 이력 저장

#### 서버리스 및 CI/CD

* AWS Lambda 기반 서버리스 실행
* API Gateway를 통한 Webhook 수신
* GitHub Actions 기반 CI/CD
* Pytest 기반 단위 / 통합 테스트

---

### 1-3. 기술 스택

| 분류                   | 기술                               |
| -------------------- | -------------------------------- |
| **Language**         | Python 3.11                      |
| **Framework**        | FastAPI                          |
| **AI Orchestration** | LangChain, **LangGraph**         |
| **LLM**              | Gemini Flash, Claude 3.5, GPT-4o |
| **Database**         | PostgreSQL                       |
| **Cache**            | Redis                            |
| **Serverless**       | AWS Lambda, AWS API Gateway      |
| **Adapter**          | Mangum                           |
| **Container**        | Docker                           |
| **Integration**      | GitHub REST API                  |
| **Testing**          | Pytest                           |
| **CI/CD**            | GitHub Actions                   |

---

### 1-4. 시스템 아키텍처

```text
[ GitHub PR (opened / synchronize) ]
                │
                ▼
[ GitHub Webhook ]
                │
                ▼
[ 1. FastAPI Webhook Controller ]
    ├── HMAC SHA256 서명 검증
    ├── Webhook DTO 변환
    └── Background Event Dispatch
                │
                ▼
[ 2. ReviewService ]
    ├── Redis → Commit SHA 중복 확인
    │       └── 이미 분석됨 → [Skip]
    │
    └── LangGraph State Machine 실행
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
   [Gemini] [Claude]  [GPT-4o]
       │        │        │
     분류/     보안      성능
     스타일    리뷰      리뷰
       └────────┼────────┘
                │
                ▼
[ 3. Review Result ]
    ├── Summary
    ├── Style Review
    ├── Security Review
    ├── Performance Review
    └── Token Metrics
                │
        ┌───────┴────────┐
        ▼                ▼
[ GitHub REST API ]   [ PostgreSQL ]
        │                │
    PR Comment        리뷰 이력
    자동 등록         Token / Cost 저장
```

#### CI/CD 배포 파이프라인

```text
GitHub Push (main)
 └─► GitHub Actions (deploy.yml)
      ├─► Checkout Code & Set up Python (.venv)
      ├─► Install Dependencies (requirements.txt)
      ├─► pytest (Unit & Integration Test 자동 실행)
      ├─► Docker Image Build (Dockerfile 컨테이너 패키징)
      └─► AWS Lambda / Cloud Server 자동 배포 완료
```

---

## 2. 도메인 및 구조 설계

### 2-1. 프로젝트 구조

```text
ReviewFlow/
├── .github/workflows/
│    └── deploy.yml                    # AWS Lambda 자동 배포
├── src/
│   ├── application/                   # 리뷰 오케스트레이션 및 비즈니스 로직
│   │   └── ReviewService
│   ├── domain/                        # 리뷰 데이터 모델 및 인터페이스
│   ├── infrastructure/                # 외부 시스템 연동
│   │   ├── Gemini LLM
│   │   ├── Redis
│   │   └── GitHub API
│   └── presentation/                  # FastAPI Webhook Controller
|   ├── tests/                         # 단위 테스트 & 통합 테스트
├── main.py                            # Lambda Entry Point / Mangum Handler
├── requirements.txt                   # Python Dependencies
```

---

## 3. 핵심 기능

### 3-1. 핵심 기능 요약

* **LangGraph 기반 멀티 에이전트 오케스트레이션**

  * 코드의 성격과 리뷰 목적에 따라 Gemini, Claude, GPT를 단계별로 호출하고 상태를 공유하는 State Machine 구현

* **Redis 기반 Commit SHA 캐싱**

  * 이미 분석된 커밋 해시에 대한 중복 LLM 호출을 차단하여 응답 속도 최적화 및 비용 절감

* **정밀한 토큰 및 비용 측정**

  * LLM 호출마다 소모되는 Prompt/Completion Token을 집계하여 PostgreSQL에 영속화하고 비용 모니터링 기반 마련

* **서버리스 비동기 Webhook 아키텍처**

  * GitHub Webhook의 10초 타임아웃 제약을 극복하기 위한 백그라운드 이벤트 디스패치 적용

---

### 3-2. 핵심 비즈니스 로직

| 구분                     | 비즈니스 규칙             | 처리 방식                               |
| ---------------------- | ------------------- | ----------------------------------- |
| **Webhook 수신**         | GitHub 요청의 안전한 수신   | HMAC SHA256 서명 검증                   |
| **Webhook 응답**         | GitHub Timeout 방지   | 즉시 `200 OK` 반환 후 Background Task 실행 |
| **중복 실행 방지**           | 동일 Commit의 중복 리뷰 방지 | Redis `commit_sha` 조회               |
| **리뷰 오케스트레이션**         | 리뷰 영역별 Agent 실행     | LangGraph State Machine             |
| **Style Review**       | 코드 스타일 및 가독성 분석     | Gemini Flash                        |
| **Security Review**    | 보안 취약점 분석           | Claude 3.5                          |
| **Performance Review** | 성능 개선점 분석           | GPT-4o                              |
| **결과 통합**              | 각 Agent 리뷰 결과 통합    | `ReviewState` 기반 결과 합성              |
| **비용 추적**              | Token 사용량 기록        | LLM 응답 Metadata 파싱                  |
| **이력 관리**              | 리뷰 결과 영속화           | PostgreSQL                          |
| **PR 피드백**             | 분석 결과 자동 전달         | GitHub REST API                     |

---

### 3-8. 담당 영역 및 역할

#### 개인 프로젝트 (100% 기여)

* **서버리스 비동기 아키텍처 및 비용 최적화 설계**

  * GitHub Webhook의 10초 타임아웃 제약을 극복하기 위한 백그라운드 이벤트 비동기 디스패치 파이프라인 설계
  * Redis Commit SHA 캐싱을 도입하여 중복 분석을 차단하고 LLM API 토큰 및 비용 절감 구조 구축

* **LangGraph 기반 멀티 에이전트 오케스트레이션 구축**

  * 코드 리뷰의 전문성을 높이기 위해 LangGraph 상태 기계(State Machine) 도입
  * Gemini, Claude, GPT 모델을 도메인별(스타일, 보안, 성능)로 분산 배치하여 멀티 에이전트 리뷰 파이프라인 구현

* **CI/CD 및 배포 자동화**

  * GitHub Actions 기반 `pytest` 단위/통합 테스트 자동 검증 파이프라인 구축
  * AWS Lambda 및 컨테이너 기반 배포 자동화 환경 구축

---

## 4. 엔지니어링 문제 해결 및 트러블슈팅

### 4-1. 성능 개선 및 구조 최적화 비교

| **개선 항목**          | **개선 전**                            | **개선 후**                                           | **정성적 / 정량적 효과**                |
| ------------------ | ----------------------------------- | -------------------------------------------------- | ------------------------------- |
| **웹훅 응답 속도 및 안정성** | 동기식 LLM 호출로 10초 초과 시 GitHub 타임아웃 발생 | 백그라운드 비동기 디스패치 및 즉시 `200 OK` 반환                    | GitHub 웹훅 전송 실패(Timeout)율 0% 달성 |
| **LLM API 비용 관리**  | 푸시/동기화 이벤트마다 전체 코드 재분석으로 비용 낭비      | **Redis Commit SHA 캐싱** 도입으로 중복 분석 원천 차단           | 불필요한 LLM API 호출 비용 대폭 절감        |
| **리뷰 확장성 및 전문성**   | 단일 LLM 프롬프트로 모든 관점 리뷰 수행            | **LangGraph 멀티 에이전트** 기반 분산 리뷰 (Gemini/Claude/GPT) | 영역별(보안, 성능, 스타일) 리뷰 분리          |

### 4-2. 기술 트러블슈팅

#### 1) GitHub Webhook 타임아웃 (`Client.Timeout exceeded`) 문제 해결

**현상**

PR 생성 시 웹훅 서버가 무거운 AI 분석 작업을 동기로 대기하면서 10초 이내에 응답하지 못해 GitHub이 연결을 끊고 전송 실패 처리

**원인**

Webhook Controller와 비즈니스 로직 간 작업 분리가 이루어지지 않아 HTTP 응답 지연 발생

**해결**

FastAPI 백그라운드 이벤트 디스패치 패턴을 도입하여 요청 수신 및 HMAC 검증 후 즉시 `200 OK`를 반환하고, 실제 리뷰 파이프라인은 백그라운드 태스크로 분리

**결과**

GitHub Webhook 타임아웃 문제를 해결하고 안정적인 이벤트 수신 파이프라인 구축

#### 2) 반복되는 Push 이벤트로 인한 LLM 토큰 낭비 및 비용 증가 해결

**현상**

개발자가 사소한 수정으로 연속 커밋을 Push할 때마다 동일한 Diff에 대해 LLM이 재호출되어 API 비용 증가

**원인**

커밋 변경 이력을 식별하지 못하고 모든 Webhook `synchronize` 이벤트에 대해 리뷰 수행

**해결**

Redis에 `commit_sha`를 키로 사용하는 캐싱 레이어(`redis_client.py`) 구축

  * 수신된 PR의 최신 Commit SHA가 Redis에 존재하면 리뷰 프로세스 즉시 스킵
  * 존재하지 않는 경우에만 LLM 리뷰 실행 후 Commit SHA 저장

**결과**

중복 LLM API 호출을 방지하여 토큰 비용을 최적화하고 불필요한 리뷰 처리 감소

#### 3) 단일 LLM 프롬프트의 한계 극복

**현상**

하나의 LLM 모델에 코드 스타일, 보안 취약점, 성능 최적화를 동시에 요청하면서 리뷰 관점이 복잡해지고 결과 품질에 한계 발생

**원인**

단일 프롬프트에 여러 리뷰 목적을 결합한 구조

**해결**

**LangGraph**를 도입하여 State Machine 기반의 멀티 에이전트 리뷰 파이프라인 구축

  * **Gemini Flash** → 분류 / 스타일 리뷰
  * **Claude 3.5** → 보안 리뷰
  * **GPT-4o** → 성능 리뷰
  * 각 노드에서 `ReviewState`를 공유하도록 구성

**결과**

리뷰 관점을 도메인별로 분리하여 각 모델의 역할에 맞는 코드 리뷰 파이프라인 구축

### 4-3. 프로젝트 회고 및 성장 포인트

* **비용 관점의 백엔드 및 캐싱 설계**

  * 무조건적인 LLM 호출에 의존하지 않고, **Redis Commit SHA 캐시 레이어**와 **PostgreSQL 기반 토큰/비용 추적 로직**을 구축하여 API 비용을 수치적으로 관리하고 불필요한 토큰 낭비를 차단했습니다.
  * 중복 분석을 방지하고 작업 성격에 따라 모델을 분산 배치하여 **비용과 리뷰 품질을 함께 고려한 효율적인 파이프라인**을 구축했습니다.

* **LangGraph 기반 멀티 에이전트 아키텍처 경험**

  * 단일 프롬프트의 한계를 극복하기 위해 **LangGraph 상태 기계(State Machine)**를 도입하고, 리뷰 목적(스타일, 보안, 성능)에 따라 특화된 LLM(Gemini, Claude, GPT)을 유기적으로 연결했습니다.
  * 각 에이전트 간 상태 공유와 분기 흐름을 제어하며 **복잡한 AI 오케스트레이션 시스템을 설계하고 구현하는 역량**을 확장했습니다.

* **서버리스 환경의 비동기 이벤트 제어 및 Webhook 안정성 확보**

  * GitHub Webhook의 10초 타임아웃 제약을 극복하기 위해 **백그라운드 이벤트 비동기 디스패치 구조**를 도입하고, AWS Lambda 환경에서 발생할 수 있는 이벤트 루프 이슈에 대응했습니다.
  * 개발자의 별도 개입을 최소화하면서 안정적으로 동작하는 **AI 기반 코드 리뷰 자동화 시스템의 구조와 운영 방식을 설계하고 적용했습니다.**

---

## 5. 테스트 전략

* **단위 테스트 (Unit Tests)**

  * `pytest` 기반으로 핵심 파서 및 독립 도메인 로직 검증
  * `test_diff_parser.py`: Git Diff 정규식 파서가 변경된 코드 영역 및 Markdown 스니펫을 정확하게 추출하는지 검증

* **통합 테스트 (Integration Tests)**

  * `test_webhook.py`: GitHub Webhook Payload 수신, HMAC SHA256 서명 검증, DTO 매핑 및 백그라운드 이벤트 디스패치 흐름 통합 검증

* **CI 연동 검증**

  * GitHub Actions (`deploy.yml`) 실행 시 `pytest` 자동 수행
  * 단위 및 통합 테스트 전체 통과 시에만 컨테이너 빌드 및 AWS Lambda 배포 진행
 
---

## 6. 실행 방법 (Local Run)

```bash
# 1. Repository Clone
git clone https://github.com/Your-Username/ReviewFlow.git
cd ReviewFlow

# 2. Virtual Environment & Dependencies Setup
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Environment Variables Setup
cp .env.example .env
# .env 파일 내 GEMINI_API_KEY, CLAUDE_API_KEY, OPENAI_API_KEY, GITHUB_TOKEN, REDIS_URL, DATABASE_URL 설정

# 4. Local Server Run
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Run Unit & Integration Tests
pytest
```
