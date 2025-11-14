# Fin-Hub Docker Deployment Guide

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- API keys from financial data providers (see below)

### Step 1: Clone & Configure

```bash
# Clone repository
git clone https://github.com/your-org/fin-hub.git
cd fin-hub

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

### Step 2: Prepare Data (Optional)

```bash
# Create data directory
mkdir -p data/stock-data

# Option A: Use your own CSV data
# Place your stock CSV files in data/stock-data/
# Format: SYMBOL.csv (e.g., AAPL.csv, MSFT.csv)

# Option B: Let Fin-Hub download sample data automatically
# (First run will download basic S&P 500 data)
```

### Step 3: Launch

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📋 Required API Keys

### Free Tier Available

| Provider | Purpose | Get Key | Free Tier |
|----------|---------|---------|-----------|
| **Alpha Vantage** | Stock quotes | [alphavantage.co](https://www.alphavantage.co/support/#api-key) | 25 calls/day |
| **Finnhub** | Real-time stock data | [finnhub.io](https://finnhub.io/register) | 60 calls/min |
| **NewsAPI** | Financial news | [newsapi.org](https://newsapi.org/register) | 100 calls/day |
| **CoinGecko** | Crypto prices | [coingecko.com](https://www.coingecko.com/en/api) | 10-50 calls/min |
| **FRED** | Economic indicators | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) | Free, unlimited |

### Optional

| Provider | Purpose | Get Key | Notes |
|----------|---------|---------|-------|
| **MarketStack** | Stock data backup | [marketstack.com](https://marketstack.com/signup/free) | Fallback only |
| **OpenSanctions** | Compliance checks | [opensanctions.org](https://www.opensanctions.org/api/) | Enterprise feature |

## 📦 Configuration Options

### Environment Variables

```bash
# Required
FINNHUB_API_KEY=xxx
ALPHA_VANTAGE_API_KEY=xxx
NEWS_API_KEY=xxx
COINGECKO_API_KEY=xxx
FRED_API_KEY=xxx

# Optional
MARKETSTACK_API_KEY=xxx
OPENSANCTIONS_API_KEY=xxx
ENVIRONMENT=production  # or development
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
FIN_HUB_ROOT=/app  # Override project root
```

### Volume Mounts

```yaml
volumes:
  # Stock data (CSV files)
  - ./data/stock-data:/app/data/stock-data

  # Crypto cache (auto-generated)
  - ./data/crypto-cache:/app/data/crypto-cache

  # Logs
  - ./logs:/app/logs
```

## 🔧 Advanced Usage

### Custom Data Directory

```yaml
# docker-compose.yml
services:
  fin-hub:
    volumes:
      - /path/to/your/data:/app/data
    environment:
      - FIN_HUB_ROOT=/app
```

### Multiple Instances

```bash
# Run multiple instances with different ports
docker-compose up --scale fin-hub=3

# Or use different compose files
docker-compose -f docker-compose.prod.yml up
```

### Production Deployment

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  fin-hub:
    image: your-registry.com/fin-hub:latest
    restart: always
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=WARNING
    env_file:
      - .env.production
    volumes:
      - stock-data:/app/data/stock-data
      - logs:/app/logs
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  stock-data:
    driver: local
  logs:
    driver: local
```

## 📊 Data Management

### CSV Data Format

Stock data CSVs should have these columns:
```csv
Date,Open,High,Low,Close,Volume
2025-01-01,150.00,152.00,149.00,151.00,1000000
```

### Automatic Data Download

If no data found, Fin-Hub will automatically download:
- S&P 500 top 100 stocks
- 5 years of historical data
- Daily updates

To disable:
```yaml
environment:
  - AUTO_DOWNLOAD_DATA=false
```

## 🔐 Security Best Practices

### 1. Never Commit Secrets
```bash
# .gitignore (already configured)
.env
.env.local
.env.production
*.key
credentials.json
```

### 2. Use Docker Secrets (Swarm/Kubernetes)
```bash
# Create secret
echo "your_api_key" | docker secret create finnhub_key -

# Use in compose
services:
  fin-hub:
    secrets:
      - finnhub_key
```

### 3. Rotate Keys Regularly
```bash
# Update .env
# Restart container
docker-compose restart
```

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs fin-hub

# Common issues:
# 1. Missing API keys -> Check .env file
# 2. Port conflict -> Change port in docker-compose.yml
# 3. Permission denied -> Check volume permissions
```

### API calls failing
```bash
# Test API keys
docker-compose exec fin-hub python -c "
from app.clients.unified_api_manager import UnifiedAPIManager
import asyncio
async def test():
    async with UnifiedAPIManager() as mgr:
        result = await mgr.get_stock_quote('AAPL')
        print(result)
asyncio.run(test())
"
```

### Data not loading
```bash
# Check data directory
docker-compose exec fin-hub ls -la /app/data/stock-data

# Manually trigger download
docker-compose exec fin-hub python -c "
from services.market_spoke.download_data import download_sp500_data
download_sp500_data()
"
```

## 📈 Performance Tuning

### Memory Optimization
```yaml
services:
  fin-hub:
    deploy:
      resources:
        limits:
          memory: 2G  # Adjust based on data size
```

### Caching
```yaml
environment:
  - CACHE_TTL=300  # 5 minutes
  - ENABLE_REDIS_CACHE=true  # If Redis available
```

## 🔄 Updates

```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d

# Clean up old images
docker image prune
```

## 📞 Support

- Issues: https://github.com/your-org/fin-hub/issues
- Docs: https://docs.fin-hub.io
- Discord: https://discord.gg/fin-hub

## 📄 License

MIT License - see LICENSE file for details
