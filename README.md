# Fin-Hub: AI 금융 도구 통합 허브

## 프로젝트 개요
Fin-Hub는 AI 에이전트가 활용할 수 있는 금융 분석 도구들을 통합하는 중앙 허브 플랫폼입니다. Hub-and-Spoke 아키텍처를 통해 분산된 금융 AI 도구들을 MCP(Model Context Protocol) 표준으로 통합하여 제공합니다.

## 주요 기능

### 🎯 MCP (Model Context Protocol) 지원
- Claude Desktop 및 다른 AI 클라이언트와 직접 연동
- 4개의 독립적인 MCP 서버 (Hub, Market, Risk, Portfolio)
- **총 38개 API** 제공 (Hub 9개 + Market 13개 + Risk 8개 + Portfolio 8개)
- **초고속 초기화** (평균 2초, Lazy Loading 최적화 적용)
- 실시간 시장 데이터, 리스크 분석, 포트폴리오 최적화 도구 제공

### 🏢 Hub 서버 (9개 API)
- **hub_status** - 전체 시스템 상태 확인
- **hub_list_spokes** - Spoke 서비스 목록 및 상태
- **hub_get_spoke_tools** - 모든 도구 목록 조회
- **hub_health_check** - 시스템 헬스체크
- **hub_unified_dashboard** - 통합 대시보드
- **hub_search_tools** - 키워드 기반 도구 검색
- **hub_quick_actions** - 자주 쓰는 작업 템플릿
- **hub_integration_guide** - 워크플로우 가이드
- **hub_call_spoke_tool** - Spoke 도구 프록시 호출

### 📊 시장 데이터 분석 (Market Spoke - 13개 API)
- **기본 데이터**: 실시간 주식/암호화폐 시세, 금융 뉴스, 경제 지표
- **기술적 분석**: RSI, MACD, Bollinger Bands, 이동평균
- **패턴 인식**: 차트 패턴, 지지/저항선, 추세 분석
- **고급 분석**: 이상 징후 탐지, 종목 비교, 감성 분석
- **알림 시스템**: 가격 변동, 돌파 알림
- 다중 API fallback 지원 (7개 데이터 소스)

### 🛡️ 리스크 관리 (Risk Spoke - 8개 API)
- **VaR 계산**: Historical, Parametric, Monte Carlo 방식
- **리스크 지표**: Sharpe, Sortino, 최대손실, 변동성, Calmar
- **포트폴리오 리스크**: 상관관계, 집중도, 분산 분석
- **시나리오 분석**: 스트레스 테스트, 꼬리 리스크, 블랙스완
- **파생상품**: 옵션 Greeks (Delta, Gamma, Vega, Theta, Rho)
- **규제 준수**: 제재 확인, KYC/AML, 포지션 한도
- **리스크 대시보드**: 종합 리스크 현황

### 💼 포트폴리오 관리 (Portfolio Spoke - 8개 API)
- **최적화**: 평균-분산, HRP, Risk Parity, Black-Litterman
- **자산 배분**: 전략적/전술적 자산군별 배분
- **리밸런싱**: 임계값 기반, 정기, 세금 고려 전략
- **성과 분석**: 수익률, Sharpe, Sortino, 알파/베타, 기여도 분석
- **백테스트**: 모멘텀, 평균회귀 등 전략 시뮬레이션
- **팩터 분석**: Fama-French 5-factor 모델
- **세금 최적화**: 손실 수확, Wash Sale 탐지, 세금 최소화
- **포트폴리오 대시보드**: 종합 현황 및 건강도 점수

## 아키텍처 개요
```
fin-hub/
├── infrastructure/          # 인프라 설정 (Consul, NGINX, Monitoring)
├── services/               # 핵심 서비스들
│   ├── hub-server/         # 중앙 허브 서비스 (9개 API)
│   ├── market-spoke/       # 시장 분석 도구 (13개 API)
│   ├── risk-spoke/         # 리스크 관리 도구 (8개 API)
│   └── portfolio-spoke/    # 포트폴리오 관리 도구 (8개 API)
├── data/                   # 주식 데이터 (503개 종목)
├── docs/                   # 프로젝트 문서
├── tests/                  # 통합 테스트
└── .env.example            # 환경 변수 예시
```

## 빠른 시작

### 1. MCP 서버 설정 (Claude Desktop 연동)

#### 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 필요한 API 키를 설정하세요:

```bash
# Market Data APIs
ALPHA_VANTAGE_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
COINGECKO_API_KEY=your_key_here
FRED_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
MARKETSTACK_API_KEY=your_key_here
OPENSANCTIONS_API_KEY=your_key_here
```

**주의:** `.env` 파일은 gitignore에 포함되어 있으므로 git에 커밋되지 않습니다.

#### Claude Desktop 설정

1. Claude Desktop 설정 파일 열기:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. 다음 설정을 `mcpServers` 섹션에 추가:

```json
{
  "mcpServers": {
    "fin-hub": {
      "type": "stdio",
      "command": "python",
      "args": ["C:/project/Fin-Hub/services/hub-server/mcp_server.py"],
      "env": {
        "ENVIRONMENT": "development",
        "HUB_HOST": "localhost",
        "HUB_PORT": "8000",
        "LOG_LEVEL": "INFO"
      }
    },
    "fin-hub-market": {
      "type": "stdio",
      "command": "python",
      "args": ["C:/project/Fin-Hub/services/market-spoke/mcp_server.py"],
      "env": {
        "ENVIRONMENT": "development",
        "SERVICE_NAME": "market-spoke",
        "SERVICE_PORT": "8001",
        "ALPHA_VANTAGE_API_KEY": "your_key",
        "NEWS_API_KEY": "your_key",
        "COINGECKO_API_KEY": "your_key",
        "FRED_API_KEY": "your_key",
        "FINNHUB_API_KEY": "your_key",
        "MARKETSTACK_API_KEY": "your_key",
        "OPENSANCTIONS_API_KEY": "your_key",
        "LOG_LEVEL": "INFO"
      }
    },
    "fin-hub-risk": {
      "type": "stdio",
      "command": "python",
      "args": ["C:/project/Fin-Hub/services/risk-spoke/mcp_server.py"],
      "env": {
        "ENVIRONMENT": "development",
        "SERVICE_NAME": "risk-spoke",
        "SERVICE_PORT": "8002",
        "LOG_LEVEL": "INFO"
      }
    },
    "fin-hub-portfolio": {
      "type": "stdio",
      "command": "python",
      "args": ["C:/project/Fin-Hub/services/portfolio-spoke/mcp_server.py"],
      "env": {
        "ENVIRONMENT": "development",
        "SERVICE_NAME": "portfolio-spoke",
        "SERVICE_PORT": "8003",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**주의:** 경로를 실제 프로젝트 경로로 변경하세요.

3. Claude Desktop 재시작

4. Claude Desktop에서 `/mcp` 명령어로 서버 확인

### 2. MCP 서버 사용 예시

#### Hub 서버를 통한 통합 관리
```
# 전체 시스템 상태 확인
hub_status

# 모든 도구 검색
hub_search_tools(keyword: "stock")

# 통합 대시보드
hub_unified_dashboard
```

#### Market Spoke - 시장 데이터
```
# 주식 시세 조회
stock_quote(symbol: "AAPL")

# 암호화폐 가격
crypto_price(symbol: "bitcoin")

# 기술적 분석
technical_analysis(symbol: "AAPL", indicators: ["rsi", "macd"])

# 패턴 인식
pattern_recognition(symbol: "AAPL", patterns: ["trend", "support_resistance"])

# 감성 분석
sentiment_analysis(symbol: "AAPL")
```

#### Risk Spoke - 리스크 관리
```
# VaR 계산
risk_calculate_var(symbol: "AAPL", method: "all", confidence_level: 0.95)

# 리스크 지표
risk_calculate_metrics(symbol: "AAPL")

# 포트폴리오 리스크
risk_analyze_portfolio(portfolio: [
  {"symbol": "AAPL", "weight": 0.6},
  {"symbol": "MSFT", "weight": 0.4}
])

# 스트레스 테스트
risk_stress_test(symbol: "AAPL", scenarios: ["2008_financial_crisis"])

# 옵션 Greeks
risk_calculate_greeks(symbol: "AAPL", option_type: "call", strike: 150)
```

#### Portfolio Spoke - 포트폴리오 관리
```
# 포트폴리오 최적화
portfolio_optimize(tickers: ["AAPL", "MSFT", "GOOGL"], method: "max_sharpe")

# 리밸런싱
portfolio_rebalance(
  current_positions: {"AAPL": {"shares": 100, "value": 15000, "price": 150}},
  target_weights: {"AAPL": 0.5, "MSFT": 0.5},
  total_value: 15000
)

# 백테스트
portfolio_backtest(
  strategy: "momentum",
  custom_tickers: ["AAPL", "MSFT"],
  start_date: "2023-01-01"
)

# 세금 최적화
portfolio_optimize_taxes(
  positions: {"AAPL": {"shares": 100, "cost_basis": 150, "current_price": 180}},
  transactions: []
)
```

자세한 사용법은 [MCP 서버 가이드](docs/MCP_SERVERS_GUIDE.md)를 참고하세요.

## 성능 및 최적화

### ⚡ 초기화 속도
- **Hub 서버**: 0.54초
- **Market Spoke**: ~2-3초 (이전 9초에서 개선)
- **Risk Spoke**: ~2-3초 (이전 7초에서 개선)
- **Portfolio Spoke**: ~2-3초 (이전 12초에서 개선)
- **평균**: 약 2초 (78% 성능 향상)

### 🔧 적용된 최적화
1. **Lazy Loading**: InitializationOptions 지연 로딩 (6초 절약)
2. **조건부 Import**: 필요한 경우에만 dotenv 로딩
3. **도구 인스턴스 캐싱**: 첫 호출 시에만 생성, 이후 재사용
4. **JSON 직렬화 최적화**: Numpy/Pandas 타입 자동 변환

### ✅ 테스트 완료
- **전체 38개 API 정상 작동 확인**
- Market Spoke: 13/13 통과
- Risk Spoke: 8/8 통과
- Portfolio Spoke: 8/8 통과
- Hub Server: 9/9 통과
- JSON 직렬화 문제 해결 완료
- Claude Desktop 연동 검증 완료

## 서비스 구성

### Hub Server (9개 API)
- **시스템 관리**: 상태 확인, Spoke 관리, 헬스체크
- **도구 검색**: 키워드 기반 도구 찾기, 통합 대시보드
- **워크플로우**: Quick Actions, 통합 가이드
- **프록시**: Spoke 도구 직접 호출 라우팅

### Market Spoke (13개 API)
- **기본 데이터**: 주식/암호화폐 시세, 뉴스, 경제 지표, 시장 현황
- **기술적 분석**: RSI, MACD, Bollinger Bands, 이동평균
- **고급 분석**: 패턴 인식, 이상 탐지, 종목 비교, 감성 분석, 알림
- **데이터 소스**: 7개 API (Alpha Vantage, Finnhub, CoinGecko 등)

### Risk Spoke (8개 API)
- **기본 리스크**: VaR (3가지 방법), 리스크 지표 (Sharpe, Sortino 등)
- **포트폴리오**: 포트폴리오 리스크 분석, 상관관계, 집중도
- **시나리오**: 스트레스 테스트, 꼬리 리스크, 블랙스완 분석
- **파생상품**: 옵션 Greeks (Black-Scholes 모델)
- **규제**: 제재 확인, 컴플라이언스 체크

### Portfolio Spoke (8개 API)
- **최적화**: 4가지 방법 (평균-분산, HRP, Risk Parity, Black-Litterman)
- **배분/리밸런싱**: 자산 배분, 3가지 리밸런싱 전략
- **분석**: 성과 분석, 백테스트, 팩터 분석 (Fama-French)
- **세금**: 손실 수확, Wash Sale 탐지, 세금 최소화
- **대시보드**: 포트폴리오 건강도 및 종합 현황

## 개발 환경 설정

### 필수 요구사항
- Docker & Docker Compose
- Python 3.11+
- Node.js (문서 생성용)

### 로컬 개발 환경
```bash
# 개발 환경 초기화
make setup-dev

# 서비스별 개발 서버 시작
make dev-hub        # Hub Server
make dev-market     # Market Spoke
make dev-risk       # Risk Spoke
make dev-pfolio     # Portfolio Spoke
```

## 문서

### MCP 서버 관련
- **[MCP 서버 사용 가이드](docs/MCP_SERVERS_GUIDE.md)** - 각 MCP 서버의 도구 사용법 및 예시
- **[데이터 및 API 레퍼런스](docs/DATA_AND_API_REFERENCE.md)** - API 데이터 소스 및 검증 정보
- **[Market Spoke 테스트 리포트](docs/MARKET_SPOKE_TEST_REPORT.md)** - Market Spoke 통합 테스트 결과

### 프로젝트 관리
- [설치 가이드](documentation/setup/INSTALLATION.md)
- [API 문서](documentation/api/README.md)
- [아키텍처 가이드](documentation/architecture/README.md)
- [배포 가이드](documentation/deployment/README.md)

## 보안 및 주의사항

### API 키 관리
- **절대로 API 키를 git에 커밋하지 마세요**
- `.env` 파일과 `claude_desktop_config.json`은 `.gitignore`에 포함되어 있습니다
- API 키는 환경 변수로만 관리하세요
- 공개 저장소에 업로드하기 전에 모든 민감한 정보를 제거했는지 확인하세요

### gitignore 포함 항목
- `.env*` - 모든 환경 변수 파일
- `claude_desktop_config.json` - Claude Desktop 설정 (API 키 포함)
- `*_API_KEY*`, `*_SECRET*`, `*credentials*` - API 키 및 비밀 정보
- `*.pem`, `*.key` - 인증서 및 키 파일

## 데이터 소스

### Market Data Providers
- **Alpha Vantage** - 주식 시세 데이터
- **CoinGecko** - 암호화폐 가격 데이터
- **News API** - 금융 뉴스
- **FRED (Federal Reserve Economic Data)** - 경제 지표
- **Finnhub** - 실시간 주식 데이터
- **Marketstack** - 주식 시장 데이터
- **OpenSanctions** - 제재 대상 확인
