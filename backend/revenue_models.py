"""
revenue_models.py — Agent World

Hybrid revenue tracking: Lightweight internal aggregator for agent visibility
+ external tool integration (Stripe, Meta Ads Manager) for compliance.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import json


class RevenueTransaction(Base):
    """Individual sale transaction from any channel"""
    __tablename__ = "revenue_transactions"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    tenant_id = Column(String(100), nullable=False, index=True)
    
    # Transaction details
    channel = Column(String(50))  # etsy, amazon_kdp, shopify, gumroad, stripe
    order_id = Column(String(255), index=True)
    product_id = Column(String(255))
    product_name = Column(String(500))
    
    # Financials
    gross_revenue = Column(Float, default=0.0)  # Before fees
    platform_fee = Column(Float, default=0.0)     # Etsy listing fee, etc
    payment_fee = Column(Float, default=0.0)    # Stripe/PayPal fee
    net_revenue = Column(Float, default=0.0)    # After all fees
    currency = Column(String(3), default="USD")
    
    # Attribution
    campaign_id = Column(String(255))  # Link to ad campaign that drove this sale
    attributed_to_agent = Column(String(100))  # Which agent created the product
    
    # Metadata
    transaction_time = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(Text)  # JSON blob from original API response
    synced_from = Column(String(50))  # stripe, etsy_api, manual_import
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_revenue_business_time', 'business_id', 'transaction_time'),
        Index('idx_revenue_channel_time', 'channel', 'transaction_time'),
        Index('idx_revenue_campaign', 'campaign_id'),
    )


class AdSpendTransaction(Base):
    """Ad spend from Meta, Google, Amazon, TikTok ads"""
    __tablename__ = "ad_spend_transactions"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    tenant_id = Column(String(100), nullable=False, index=True)
    
    # Platform details
    platform = Column(String(50))  # meta, google, amazon_ads, tiktok
    campaign_id = Column(String(255), index=True)
    campaign_name = Column(String(500))
    ad_set_id = Column(String(255))
    ad_id = Column(String(255))
    
    # Financials
    spend = Column(Float, default=0.0)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)  # Platform-reported
    currency = Column(String(3), default="USD")
    
    # Attribution (link to our campaigns)
    internal_campaign_id = Column(String(255))  # Our campaign tracking ID
    
    # Time (hourly or daily granularity from APIs)
    transaction_time = Column(DateTime, default=datetime.utcnow)
    
    raw_data = Column(Text)
    synced_from = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_adspend_business_time', 'business_id', 'transaction_time'),
        Index('idx_adspend_platform_time', 'platform', 'transaction_time'),
        Index('idx_adspend_internal_campaign', 'internal_campaign_id'),
    )


class CampaignPerformance(Base):
    """Aggregated campaign metrics — ROAS, CPA, etc."""
    __tablename__ = "campaign_performance"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    tenant_id = Column(String(100), nullable=False, index=True)
    
    # Campaign identification
    campaign_id = Column(String(255), index=True)  # Internal ID
    campaign_name = Column(String(500))
    platform = Column(String(50))  # meta, google, etc
    product_id = Column(String(255))  # What we're selling
    
    # Time window (daily or hourly rollups)
    date = Column(DateTime, nullable=False)
    granularity = Column(String(20), default="daily")  # hourly, daily, weekly
    
    # Aggregated metrics
    ad_spend = Column(Float, default=0.0)
    revenue_attributed = Column(Float, default=0.0)  # From RevenueTransaction.campaign_id
    orders_attributed = Column(Integer, default=0)
    
    # Calculated metrics (denormalized for fast queries)
    roas = Column(Float, default=0.0)  # Return on Ad Spend = revenue / spend
    cpa = Column(Float, default=0.0)   # Cost Per Acquisition = spend / orders
    aov = Column(Float, default=0.0)   # Average Order Value = revenue / orders
    
    # Platform metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)   # Click-through rate
    cpc = Column(Float, default=0.0)   # Cost per click
    
    # Agent decisions
    agent_action = Column(String(50))  # scaled, paused, maintained
    agent_reasoning = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_perf_business_date', 'business_id', 'date'),
        Index('idx_perf_campaign_date', 'campaign_id', 'date'),
        Index('idx_perf_roas', 'roas'),  # For "find underperforming campaigns"
    )


class RevenueSyncLog(Base):
    """Track last sync times for each external integration"""
    __tablename__ = "revenue_sync_logs"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    tenant_id = Column(String(100), nullable=False)
    
    integration = Column(String(50))  # stripe, etsy, meta_ads, google_ads
    last_sync_at = Column(DateTime)
    last_transaction_time = Column(DateTime)  # Up to what time we synced
    transactions_synced = Column(Integer, default=0)
    status = Column(String(50))  # success, error, partial
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sync_business_integration', 'business_id', 'integration'),
    )


class RevenueGoal(Base):
    """Revenue targets and tracking"""
    __tablename__ = "revenue_goals"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    tenant_id = Column(String(100), nullable=False)
    
    goal_type = Column(String(50))  # daily, weekly, monthly, custom
    target_amount = Column(Float)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    # Progress (updated by background job)
    current_amount = Column(Float, default=0.0)
    percent_complete = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
