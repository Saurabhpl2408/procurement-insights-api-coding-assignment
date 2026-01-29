from pydantic import BaseModel, Field, validator
from typing import List, Literal
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SupplierInput(BaseModel):
    supplier_name: str = Field(..., min_length=1, description="Name of the supplier")
    annual_spend_usd: float = Field(..., gt=0, description="Annual spend in USD")
    on_time_delivery_pct: float = Field(..., ge=0, le=100, description="On-time delivery percentage")
    contract_expiry_months: int = Field(..., ge=0, description="Months until contract expiry")
    single_source_dependency: bool = Field(..., description="Whether this is a single source supplier")
    region: str = Field(..., min_length=1, description="Supplier region")

    @validator('supplier_name', 'region')
    def validate_non_empty_string(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty or whitespace only')
        return v.strip()


class InsightsRequest(BaseModel):
    category: str = Field(..., min_length=1, description="Procurement category name")
    suppliers: List[SupplierInput] = Field(..., min_items=1, description="List of suppliers")

    @validator('category')
    def validate_category(cls, v):
        if not v or not v.strip():
            raise ValueError('Category cannot be empty or whitespace only')
        return v.strip()


class InsightsResponse(BaseModel):
    category: str = Field(..., description="Procurement category")
    overall_risk_level: RiskLevel = Field(..., description="Overall risk assessment")
    key_risks: List[str] = Field(..., min_items=1, description="Identified key risks")
    negotiation_levers: List[str] = Field(..., min_items=1, description="Available negotiation levers")
    recommended_actions_next_90_days: List[str] = Field(..., min_items=1, description="Recommended actions for next 90 days")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score between 0 and 1")

    @validator('key_risks', 'negotiation_levers', 'recommended_actions_next_90_days')
    def validate_non_empty_lists(cls, v):
        if not v:
            raise ValueError('List cannot be empty')
        for item in v:
            if not item or not item.strip():
                raise ValueError('List items cannot be empty or whitespace only')
        return [item.strip() for item in v]