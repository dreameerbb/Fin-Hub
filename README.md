# Fin-Hub: 통합 금융 분석 MCP 서버

> **AI 기반 금융 분석 허브** - MCP(Model Context Protocol)를 통한 AI 에이전트용 종합 금융 도구

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Test Coverage](https://img.shields.io/badge/Tests-100%25-brightgreen)]()

## 🚀 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/fin-hub.git
cd fin-hub

# 2. API 키 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 3. Claude Desktop 설정에 추가
# 아래 설정 섹션 참조

# 4. Claude Desktop 재시작 - 사용 준비 완료!
```

## 📋 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [아키텍처](#아키텍처)
- [설치](#설치)
- [설정](#설정)
- [사용 가능한 도구](#사용-가능한-도구)
- [Docker 배포](#docker-배포)
- [테스트](#테스트)
- [해결된 이슈](#해결된-이슈)
- [개발](#개발)
- [문서](#문서)

## 🎯 개요

Fin-Hub는 AI 에이전트를 위한 종합 금융 분석 도구를 제공하는 **통합 MCP 서버**입니다. **Hub-Spoke 아키텍처**를 기반으로 시장 데이터, 리스크 관리, 포트폴리오 최적화를 하나의 통합 인터페이스로 결합합니다.

### 주요 기능

- **34개의 금융 도구** - 5개 허브 관리 도구 + 29개 금융 분석 도구
- AI 에이전트(Claude 등)를 위한 **MCP 프로토콜** 통합
- 자동 폴백 기능을 갖춘 **다중 소스 데이터** (7개 데이터 제공자)
- 500개 이상 주식에 대한 **5년 히스토리컬 데이터** (CSV 기반)
- 프로덕션 배포를 위한 **Docker 지원**
- 지연 로딩 및 캐싱을 통한 **최적화된 성능**

### 테스트 현황

| 모듈 | 도구 수 | 통과 | 상태 |
|------|---------|------|------|
| 허브 관리 | 5 | 5/5 | ✅ 100% |
| 마켓 Spoke | 13 | 13/13 | ✅ 100% |
| 리스크 Spoke | 8 | 8/8 | ✅ 100% |
| 포트폴리오 Spoke | 8 | 8/8 | ✅ 100% |
| **전체** | **34** | **34/34** | **✅ 100%** |

자세한 테스트 정보는 [TEST_RESULTS.md](TEST_RESULTS.md)를 참조하세요.

## 🏗️ 아키텍처

### Hub-Spoke 설계

```
┌─────────────────────────────────────────────────────┐
│              FIN-HUB 통합 서버                       │
│            (mcp_server_integrated.py)               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Market Spoke │  │  Risk Spoke  │  │Portfolio │ │
│  │   13개 도구   │  │   8개 도구    │  │ 8개 도구  │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
│  • 통합 API 액세스                                   │
│  • 지연 로딩                                        │
│  • sys.path 격리                                    │
│  • Pandas/Numpy 사전 로딩                           │
│                                                     │
└─────────────────────────────────────────────────────┘
         │
         │ MCP stdio transport
         ▼
    Claude Desktop / AI Agents
```

### 디렉토리 구조

```
fin-hub/
├── services/
│   ├── hub-server/
│   │   ├── mcp_server_integrated.py  # 메인 통합 서버 ⭐
│   │   └── Dockerfile
│   ├── market-spoke/
│   │   ├── app/
│   │   │   ├── tools/                # 13개 시장 분석 도구
│   │   │   ├── clients/              # API 통합
│   │   │   └── utils/
│   │   └── Dockerfile
│   ├── risk-spoke/
│   │   ├── app/
│   │   │   └── tools/                # 8개 리스크 관리 도구
│   │   └── Dockerfile
│   └── portfolio-spoke/
│       ├── app/
│       │   ├── tools/                # 8개 포트폴리오 도구
│       │   └── utils/
│       └── Dockerfile
├── data/
│   └── stock-data/                   # 500개 이상 주식 CSV 파일 (5년)
├── docker-compose.yml                # 프로덕션 배포
├── .env.example                      # API 키 템플릿
├── TEST_RESULTS.md                   # 종합 테스트 보고서
└── DOCKER_DEPLOYMENT.md              # Docker 가이드
```

## 📦 설치

### 사전 요구사항

- **Python 3.11+** (3.13 권장)
- **Claude Desktop** 또는 MCP 호환 AI 클라이언트
- 데이터 제공자의 **API 키** (아래 참조)

### 필요한 API 키

| 제공자 | 용도 | 무료 제한 | 키 발급 |
|--------|------|-----------|---------|
| Finnhub | 주식 시세 | 60 calls/분 | [finnhub.io](https://finnhub.io/register) |
| Alpha Vantage | 주식 데이터 | 25 calls/일 | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| CoinGecko | 암호화폐 가격 | 10-50 calls/분 | [coingecko.com](https://www.coingecko.com/en/api) |
| NewsAPI | 금융 뉴스 | 100 calls/일 | [newsapi.org](https://newsapi.org/register) |
| FRED | 경제 지표 | 무제한 | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |

선택사항: MarketStack, OpenSanctions

### 설치 단계

1. **저장소 클론**
```bash
git clone https://github.com/your-org/fin-hub.git
cd fin-hub
```

2. **의존성 설치**
```bash
pip install -r services/hub-server/requirements.txt
pip install -r services/market-spoke/requirements.txt
pip install -r services/risk-spoke/requirements.txt
pip install -r services/portfolio-spoke/requirements.txt
```

3. **API 키 설정**
```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

## ⚙️ 설정

### Claude Desktop 설정

1. Claude Desktop 설정 파일 열기:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. Fin-Hub 서버 추가:

```json
{
  "mcpServers": {
    "fin-hub": {
      "command": "python",
      "args": ["C:/project/Fin-Hub/services/hub-server/mcp_server_integrated.py"],
      "env": {
        "FINNHUB_API_KEY": "your_key_here",
        "ALPHA_VANTAGE_API_KEY": "your_key_here",
        "COINGECKO_API_KEY": "your_key_here",
        "NEWS_API_KEY": "your_key_here",
        "FRED_API_KEY": "your_key_here",
        "MARKETSTACK_API_KEY": "your_key_here",
        "OPENSANCTIONS_API_KEY": "your_key_here",
        "FIN_HUB_ROOT": "C:/project/Fin-Hub",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**주의사항**:
- `C:/project/Fin-Hub`를 실제 프로젝트 경로로 변경
- API 키를 실제 키로 변경
- Windows에서도 슬래시 `/` 사용

3. Claude Desktop 재시작

## 🛠️ 사용 가능한 도구

### 허브 관리 (5개 도구) ✅

| 도구 | 설명 | 목적 |
|------|------|------|
| `hub_status` | 허브 시스템 상태 | 모든 Spoke의 종합 상태 확인 |
| `hub_register_spoke` | 외부 Spoke 등록 | 새로운 Spoke 서비스 동적 추가 |
| `hub_unregister_spoke` | 외부 Spoke 해제 | Spoke 서비스 제거 |
| `hub_list_all_tools` | 모든 도구 나열 | 완전한 도구 인벤토리 조회 |
| `hub_search_tools` | 키워드로 도구 검색 | 모든 Spoke에서 도구 검색 |

**사용 예시:**
```javascript
// 허브 상태 확인
hub_status({})

// 주식 관련 도구 검색
hub_search_tools({query: "stock", category: "all"})

// 외부 Spoke 등록
hub_register_spoke({
  spoke_name: "custom-spoke",
  endpoint: "http://localhost:9999",
  tool_count: 10,
  description: "커스텀 금융 도구"
})
```

### 마켓 Spoke (13개 도구) ✅

모든 도구가 완벽하게 작동합니다:

| 도구 | 설명 | 속도 |
|------|------|------|
| `stock_quote` | 실시간 주식 시세 | 1.7s |
| `crypto_price` | 암호화폐 가격 | 0.3s |
| `financial_news` | 금융 뉴스 집계 | 0.5s |
| `economic_indicator` | FRED 경제 데이터 | 0.6s |
| `market_overview` | 종합 시장 뷰 | 2.5s |
| `api_status` | API 상태 체크 | 0.5s |
| `technical_analysis` | RSI, MACD, 볼린저 밴드 | 0.1s |
| `pattern_recognition` | 차트 패턴 (헤드앤숄더 등) | 2.6s |
| `anomaly_detection` | 가격/거래량 이상 탐지 | 0.2s |
| `stock_comparison` | 다중 주식 비교 | 0.2s |
| `sentiment_analysis` | 뉴스 감성 분석 | 1.1s |
| `alert_system` | 가격 알림 및 모니터링 | 0.2s |
| `unified_market_data` | 다중 소스 시장 데이터 | 0.6s |

**사용 예시:**
```javascript
// 주식 시세 조회
stock_quote({symbol: "AAPL"})

// 기술적 분석
technical_analysis({
  symbol: "AAPL",
  indicators: ["rsi", "macd", "bollinger"],
  period: 30
})

// 감성 분석
sentiment_analysis({symbol: "AAPL", days: 7})
```

### 리스크 Spoke (8개 도구) ✅

모든 도구가 작동합니다:

| 도구 | 설명 | 상태 |
|------|------|------|
| `risk_calculate_var` | VaR (역사적, 파라메트릭, 몬테카를로) | ✅ |
| `risk_calculate_metrics` | Sharpe, Sortino, 변동성, 베타 | ✅ |
| `risk_analyze_portfolio` | 포트폴리오 리스크 분석 | ✅ |
| `risk_stress_test` | 스트레스 테스트 시나리오 | ✅ |
| `risk_analyze_tail_risk` | 극단적 사건 분석 | ✅ |
| `risk_calculate_greeks` | 옵션 그릭스 (델타, 감마, 베가, 세타, 로) | ✅ |
| `risk_check_compliance` | 제재 및 규정 준수 검사 | ✅ |
| `risk_generate_dashboard` | 리스크 대시보드 | ✅ |

**사용 예시:**
```javascript
// VaR 계산
risk_calculate_var({
  symbol: "AAPL",
  method: "all",
  confidence_level: 0.95
})

// 스트레스 테스트
risk_stress_test({
  portfolio: [
    {symbol: "AAPL", weight: 0.6},
    {symbol: "MSFT", weight: 0.4}
  ]
})
```

### 포트폴리오 Spoke (8개 도구) ✅

모든 도구가 작동합니다:

| 도구 | 설명 | 상태 |
|------|------|------|
| `portfolio_optimize` | Sharpe 비율 최대화 | ✅ |
| `portfolio_rebalance` | 포트폴리오 리밸런싱 | ✅ |
| `portfolio_analyze_performance` | 성과 지표 | ✅ |
| `portfolio_backtest` | 전략 백테스팅 | ✅ |
| `portfolio_analyze_factors` | Fama-French 팩터 분석 | ✅ |
| `portfolio_allocate_assets` | 자산 배분 | ✅ |
| `portfolio_optimize_tax` | 세금 손실 수확 | ✅ |
| `portfolio_generate_dashboard` | 포트폴리오 대시보드 | ✅ |

**사용 예시:**
```javascript
// 포트폴리오 최적화
portfolio_optimize({
  tickers: ["AAPL", "MSFT", "GOOGL"],
  method: "max_sharpe"
})

// 전략 백테스팅
portfolio_backtest({
  strategy: "momentum",
  start_date: "2023-01-01",
  end_date: "2024-01-01"
})
```

## 🐳 Docker 배포

### Docker로 빠른 시작

```bash
# 1. 환경 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 2. 빌드 및 시작
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f

# 4. 중지
docker-compose down
```

### Docker 설정

`docker-compose.yml`에 포함된 내용:
- 데이터 지속성을 위한 볼륨 마운트
- 환경 변수 설정
- 리소스 제한 (2 CPU, 4GB RAM)
- 상태 체크
- 로깅 설정

종합적인 배포 가이드는 [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)를 참조하세요.

## 🧪 테스트

### 테스트 실행

```bash
# 간단한 직접 테스트 (권장)
python test_simple.py

# 전체 MCP 프로토콜 테스트
python test_all_tools.py
```

### 테스트 결과 요약

**전체: 100% (34/34 도구 작동 중)** ✅

- ✅ **허브 관리**: 100% (5/5)
- ✅ **마켓 Spoke**: 100% (13/13)
- ✅ **리스크 Spoke**: 100% (8/8)
- ✅ **포트폴리오 Spoke**: 100% (8/8)

모든 도구가 테스트되고 작동합니다! 자세한 테스트 정보는 [TEST_RESULTS.md](TEST_RESULTS.md)를 참조하세요.

## ✅ 해결된 이슈

모든 주요 이슈가 해결되었습니다:

### 1. ✅ 포트폴리오 도구 파라미터 불일치 - 해결됨
- **문제**: 5개 포트폴리오 도구의 MCP 스키마/함수 시그니처 불일치
- **해결**: 모든 스키마를 실제 함수 시그니처에 맞게 업데이트
- **상태**: 8개 포트폴리오 도구 모두 작동 중

### 2. ✅ sys.modules 캐시 충돌 - 해결됨
- **문제**: 여러 Spoke가 `app` 패키지를 사용하여 import 충돌 발생
- **해결**: 도구 로더에서 `sys.modules` 캐시 클리어 구현
- **상태**: 모든 Spoke가 올바르게 격리됨

### 3. ✅ risk_analyze_portfolio 빈 시퀀스 - 해결됨
- **문제**: 단일 자산 포트폴리오에서 `argmax(빈 시퀀스)` 오류 발생
- **해결**: 빈 배열 검증 추가
- **상태**: 1개 이상의 자산에서 작동

### 4. ✅ tax_optimizer 인덱스 오류 - 해결됨
- **문제**: 빈 DataFrame으로 인한 인덱스 범위 초과
- **해결**: 액세스 전 데이터 존재 확인 추가
- **상태**: 누락된 데이터를 우아하게 처리

### 5. ✅ 성능 최적화 - 해결됨
- **문제**: pandas/numpy import로 인해 첫 호출이 242초 소요
- **해결**: 서버 시작 시 무거운 라이브러리 사전 로드
- **상태**: 현재 0.1초에 로드

## ℹ️ 선택적 기능

### 누락된 데이터 파일
- 일부 벤치마킹 기능에는 SPY.csv가 필요할 수 있음
- **해결 방법**: SPY 데이터 다운로드 또는 대체 벤치마크 사용
- **영향**: 중요하지 않음, 대부분의 기능은 없이도 작동

## 💻 개발

### 아키텍처 결정사항

1. **통합 허브 서버**: 4개의 별도 서버 대신 단일 MCP 서버
   - 더 간단한 배포
   - 더 나은 리소스 관리
   - 더 쉬운 유지보수

2. **stdio 전송만 사용**: HTTP/SSE 모드는 실험적이었으며 제거됨
   - stdio가 MCP 표준
   - 더 간단한 구현
   - 더 나은 호환성

3. **CSV 기반 데이터**: 500개 이상 주식에 대한 5년 히스토리컬 데이터
   - 실시간 API 속도 제한 없음
   - 빠른 로컬 액세스
   - 백테스팅에 적합

4. **지연 로딩**: 첫 사용 시 도구 로드
   - 더 빠른 시작
   - 낮은 메모리 사용량
   - 더 나은 성능

### 성능 최적화

1. **무거운 라이브러리 사전 로딩**
   - 시작 시 pandas 및 numpy 로드
   - 첫 도구 호출을 242초에서 0.1초로 단축

2. **도구 인스턴스 캐싱**
   - 도구를 한 번 생성하고 재사용
   - 초기화 오버헤드 절약

3. **sys.path 격리**
   - 각 Spoke에 대해 깨끗한 sys.path
   - import 충돌 방지

4. **sys.modules 캐시 클리어**
   - Spoke 로드 전 `app.*` 모듈 클리어
   - 올바른 import 보장

### 새 도구 추가

새로운 금융 도구 추가 가이드는 [DEVELOPMENT.md](DEVELOPMENT.md)를 참조하세요.

## 📚 문서

### 주요 문서
- [TEST_RESULTS.md](TEST_RESULTS.md) - 종합 테스트 보고서 및 알려진 이슈
- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - Docker 배포 가이드
- [.env.example](.env.example) - API 키 설정 템플릿

### API 문서
- 마켓 Spoke: `services/market-spoke/app/tools/` 참조
- 리스크 Spoke: `services/risk-spoke/app/tools/` 참조
- 포트폴리오 Spoke: `services/portfolio-spoke/app/tools/` 참조

### 데이터 소스
- **Finnhub**: 실시간 주식 시세
- **Alpha Vantage**: 주식 시장 데이터
- **CoinGecko**: 암호화폐 가격
- **NewsAPI**: 금융 뉴스
- **FRED**: 경제 지표
- **MarketStack**: 주식 데이터 (백업)
- **OpenSanctions**: 규정 준수 데이터

## 🔐 보안

### API 키 관리

**절대 API 키를 git에 커밋하지 마세요!**

- `.env` 파일은 `.gitignore`에 포함됨
- 환경 변수만 사용
- 정기적으로 키 교체
- 개발에는 무료 계정 사용

### gitignore 범위
- `.env*` - 모든 환경 파일
- `*_API_KEY*`, `*_SECRET*` - API 키 및 비밀
- `*.pem`, `*.key` - 인증서 및 키
- `claude_desktop_config.json` - 개인 설정

## 🤝 기여

기여를 환영합니다! 잠재적 개선사항:

1. 더 많은 금융 지표 추가 (모멘텀, 변동성 등)
2. 엣지 케이스를 포함한 테스트 커버리지 확장
3. 중복성을 위한 더 많은 데이터 제공자 추가
4. 캐싱 전략 개선
5. 실시간 WebSocket 데이터 피드 추가
