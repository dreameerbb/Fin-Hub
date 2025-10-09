"""
Sentiment Analysis Tool - Enhanced sentiment analysis combining news and market data
Provides comprehensive sentiment scoring with multiple data sources
"""

import sys
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re


class SentimentAnalysisTool:
    """Enhanced sentiment analysis combining news sentiment with market momentum"""

    def __init__(self):
        # Lazy import: news tool imported on-demand
        self.news_tool = None

    async def get_tool_info(self) -> Dict:
        """Get tool information for MCP protocol"""
        return {
            "name": "sentiment_analysis",
            "description": "Enhanced sentiment analysis combining news sentiment with market data scoring (1-5 scale)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search query (default: company name from symbol)"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze (default: 7)",
                        "default": 7
                    }
                },
                "required": ["symbol"]
            }
        }

    def _analyze_text_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text using keyword-based approach"""
        text_lower = text.lower()

        # Positive keywords
        positive_keywords = [
            'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'climb', 'advance',
            'outperform', 'beat', 'exceed', 'strong', 'growth', 'profit', 'bullish',
            'upgrade', 'positive', 'buy', 'success', 'innovation', 'breakthrough',
            'record', 'high', 'boom', 'upbeat', 'optimistic', 'excellent'
        ]

        # Negative keywords
        negative_keywords = [
            'plunge', 'crash', 'fall', 'drop', 'decline', 'slump', 'tumble', 'slide',
            'underperform', 'miss', 'disappoint', 'weak', 'loss', 'bearish',
            'downgrade', 'negative', 'sell', 'failure', 'concern', 'worry',
            'low', 'bust', 'pessimistic', 'poor', 'risk', 'warning'
        ]

        # Neutral keywords
        neutral_keywords = [
            'stable', 'unchanged', 'flat', 'mixed', 'neutral', 'hold',
            'maintain', 'steady', 'moderate'
        ]

        # Count keyword occurrences
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        neutral_count = sum(1 for word in neutral_keywords if word in text_lower)

        total_count = positive_count + negative_count + neutral_count

        if total_count == 0:
            return {"score": 3, "label": "NEUTRAL", "confidence": "LOW"}

        # Calculate sentiment score (1-5 scale)
        if positive_count > negative_count:
            if positive_count > negative_count * 2:
                score = 5  # Very Positive
                label = "VERY_POSITIVE"
            else:
                score = 4  # Positive
                label = "POSITIVE"
        elif negative_count > positive_count:
            if negative_count > positive_count * 2:
                score = 1  # Very Negative
                label = "VERY_NEGATIVE"
            else:
                score = 2  # Negative
                label = "NEGATIVE"
        else:
            score = 3  # Neutral
            label = "NEUTRAL"

        confidence = "HIGH" if total_count > 5 else "MEDIUM" if total_count > 2 else "LOW"

        return {
            "score": score,
            "label": label,
            "confidence": confidence,
            "positive_signals": positive_count,
            "negative_signals": negative_count,
            "neutral_signals": neutral_count
        }

    def _aggregate_news_sentiment(self, news_articles: List[Dict]) -> Dict:
        """Aggregate sentiment from multiple news articles"""
        if not news_articles:
            return {
                "overall_score": 3,
                "overall_label": "NEUTRAL",
                "confidence": "LOW",
                "article_count": 0
            }

        sentiment_scores = []
        sentiment_details = []

        for article in news_articles:
            title = article.get('title', '')
            description = article.get('description', '')
            combined_text = f"{title} {description}"

            sentiment = self._analyze_text_sentiment(combined_text)
            sentiment_scores.append(sentiment['score'])

            sentiment_details.append({
                "title": title[:100],  # First 100 chars
                "score": sentiment['score'],
                "label": sentiment['label'],
                "published": article.get('published_at', 'Unknown')
            })

        # Calculate average score
        avg_score = sum(sentiment_scores) / len(sentiment_scores)

        # Determine overall label
        if avg_score >= 4.5:
            overall_label = "VERY_POSITIVE"
        elif avg_score >= 3.5:
            overall_label = "POSITIVE"
        elif avg_score >= 2.5:
            overall_label = "NEUTRAL"
        elif avg_score >= 1.5:
            overall_label = "NEGATIVE"
        else:
            overall_label = "VERY_NEGATIVE"

        # Calculate distribution
        score_distribution = {
            "very_positive": sum(1 for s in sentiment_scores if s == 5),
            "positive": sum(1 for s in sentiment_scores if s == 4),
            "neutral": sum(1 for s in sentiment_scores if s == 3),
            "negative": sum(1 for s in sentiment_scores if s == 2),
            "very_negative": sum(1 for s in sentiment_scores if s == 1)
        }

        confidence = "HIGH" if len(news_articles) >= 10 else "MEDIUM" if len(news_articles) >= 5 else "LOW"

        return {
            "overall_score": round(avg_score, 2),
            "overall_label": overall_label,
            "confidence": confidence,
            "article_count": len(news_articles),
            "score_distribution": score_distribution,
            "article_sentiments": sentiment_details[:10]  # Top 10
        }

    def _calculate_market_momentum_score(self, symbol: str) -> Dict:
        """Calculate market momentum score (placeholder - would use real price data)"""
        # This would integrate with technical analysis tool to get real momentum
        # For now, return a neutral score
        return {
            "momentum_score": 3,
            "momentum_label": "NEUTRAL",
            "trend": "SIDEWAYS",
            "note": "Market momentum calculation requires technical analysis integration"
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced sentiment analysis"""
        # Lazy import of news tool
        if self.news_tool is None:
            from .unified_market_data import FinancialNewsTool
            self.news_tool = FinancialNewsTool()

        symbol = arguments.get("symbol", "").upper()
        query = arguments.get("query", symbol)
        days = arguments.get("days", 7)

        if not symbol:
            return {"error": "Symbol is required"}

        try:
            # Fetch news articles
            news_result = await self.news_tool.execute({
                "query": query,
                "limit": 20  # Get more articles for better sentiment analysis
            })

            if "error" in news_result:
                return {
                    "error": "Failed to fetch news data",
                    "details": news_result["error"]
                }

            # Analyze news sentiment
            news_articles = news_result.get("articles", [])
            news_sentiment = self._aggregate_news_sentiment(news_articles)

            # Calculate market momentum (placeholder)
            market_momentum = self._calculate_market_momentum_score(symbol)

            # Calculate combined sentiment score
            # Weight: 70% news sentiment, 30% market momentum
            combined_score = (news_sentiment['overall_score'] * 0.7 +
                            market_momentum['momentum_score'] * 0.3)

            # Determine combined label
            if combined_score >= 4.5:
                combined_label = "VERY_POSITIVE"
                recommendation = "STRONG_BUY"
            elif combined_score >= 3.5:
                combined_label = "POSITIVE"
                recommendation = "BUY"
            elif combined_score >= 2.5:
                combined_label = "NEUTRAL"
                recommendation = "HOLD"
            elif combined_score >= 1.5:
                combined_label = "NEGATIVE"
                recommendation = "SELL"
            else:
                combined_label = "VERY_NEGATIVE"
                recommendation = "STRONG_SELL"

            return {
                "symbol": symbol,
                "analysis_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "period_days": days,
                "combined_sentiment": {
                    "score": round(combined_score, 2),
                    "label": combined_label,
                    "recommendation": recommendation,
                    "confidence": news_sentiment['confidence']
                },
                "news_sentiment": news_sentiment,
                "market_momentum": market_momentum,
                "summary": self._generate_summary(
                    symbol,
                    combined_score,
                    combined_label,
                    news_sentiment,
                    market_momentum
                ),
                "data_sources": [
                    "Financial News (NewsAPI)",
                    "Market Momentum (Technical Analysis)"
                ]
            }

        except Exception as e:
            return {
                "error": f"Sentiment analysis failed: {str(e)}",
                "symbol": symbol
            }

    def _generate_summary(self, symbol: str, score: float, label: str,
                         news_sentiment: Dict, market_momentum: Dict) -> str:
        """Generate human-readable summary"""
        summary_parts = []

        summary_parts.append(f"{symbol} Overall Sentiment: {label} ({score:.1f}/5)")
        summary_parts.append(f"News: {news_sentiment['overall_label']} ({news_sentiment['article_count']} articles)")
        summary_parts.append(f"Market Momentum: {market_momentum['momentum_label']}")

        # Add recommendation
        if score >= 4:
            summary_parts.append("Strong positive outlook")
        elif score >= 3.5:
            summary_parts.append("Positive outlook")
        elif score >= 2.5:
            summary_parts.append("Neutral outlook")
        elif score >= 2:
            summary_parts.append("Negative outlook")
        else:
            summary_parts.append("Strong negative outlook")

        return " | ".join(summary_parts)


# Export for MCP server
__all__ = ['SentimentAnalysisTool']
