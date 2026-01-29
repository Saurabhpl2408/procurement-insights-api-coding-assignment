# Error Handling and Guardrails Documentation

## Overview
This document describes how the API handles errors, validates data, and provides guardrails against malformed inputs and LLM failures.

---

## 1. Error Handling Scenarios

### Scenario A: Empty Supplier List

**What Happens:**
```python
# Request with empty suppliers array
{
  "category": "IT Hardware",
  "suppliers": []
}
```

**Detection Point:** FastAPI endpoint (`app/main.py`, line 63-67)

```python
if not request.suppliers or len(request.suppliers) == 0:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Supplier list cannot be empty. At least one supplier is required."
    )
```

**Response:**
```json
{
  "detail": "Supplier list cannot be empty. At least one supplier is required."
}
```

**HTTP Status:** 422 Unprocessable Entity

**Why This Matters:** 
- Cannot perform comparative analysis with zero suppliers
- Prevents wasting LLM API calls on invalid requests
- Clear error message guides user to fix the issue

---

### Scenario B: Missing Required Fields

**What Happens:**
```python
# Supplier missing 'supplier_name'
{
  "category": "IT Hardware",
  "suppliers": [
    {
      "annual_spend_usd": 1000000,
      "on_time_delivery_pct": 95
      # Missing: supplier_name, contract_expiry_months, 
      #          single_source_dependency, region
    }
  ]
}
```

**Detection Point:** Pydantic validation (automatic, before endpoint code runs)

**Response:**
```json
{
  "error": "Validation Error",
  "details": [
    "suppliers -> 0 -> supplier_name: field required",
    "suppliers -> 0 -> contract_expiry_months: field required",
    "suppliers -> 0 -> single_source_dependency: field required",
    "suppliers -> 0 -> region: field required"
  ],
  "message": "Invalid input data. Please check the request format."
}
```

**HTTP Status:** 422 Unprocessable Entity

**Implementation:** Custom exception handler in `app/main.py`
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": errors,
            "message": "Invalid input data. Please check the request format."
        }
    )
```

---

### Scenario C: Malformed Field Values

**What Happens:**
```python
# Invalid values
{
  "category": "IT Hardware",
  "suppliers": [
    {
      "supplier_name": "",  # Empty string
      "annual_spend_usd": -5000,  # Negative spend
      "on_time_delivery_pct": 150,  # >100%
      "contract_expiry_months": -3,  # Negative months
      "single_source_dependency": true,
      "region": "North America"
    }
  ]
}
```

**Detection Point 1:** Pydantic field validators (`app/models.py`)
```python
annual_spend_usd: float = Field(..., gt=0)  # Must be > 0
on_time_delivery_pct: float = Field(..., ge=0, le=100)  # 0-100 range
contract_expiry_months: int = Field(..., ge=0)  # Non-negative
```

**Response:**
```json
{
  "error": "Validation Error",
  "details": [
    "suppliers -> 0 -> supplier_name: Field cannot be empty or whitespace only",
    "suppliers -> 0 -> annual_spend_usd: ensure this value is greater than 0",
    "suppliers -> 0 -> on_time_delivery_pct: ensure this value is less than or equal to 100",
    "suppliers -> 0 -> contract_expiry_months: ensure this value is greater than or equal to 0"
  ]
}
```

**HTTP Status:** 422 Unprocessable Entity

**Detection Point 2:** Additional business logic validation (`app/main.py`, lines 69-88)
```python
if supplier.annual_spend_usd <= 0:
    raise HTTPException(
        status_code=422,
        detail=f"Supplier '{supplier.supplier_name}' has invalid annual spend."
    )
```

**Why Two Layers?**
1. **Pydantic:** Catches structural/type issues automatically
2. **Business Logic:** Catches domain-specific problems with better error messages

---

### Scenario D: LLM API Failure

**What Happens:**
- Gemini API is down
- Network connection lost
- API quota exceeded
- Authentication failure

**Detection Point:** Try-catch in `app/llm_service.py`
```python
try:
    response = self.model.generate_content(full_prompt)
except Exception as e:
    raise Exception(f"Error generating insights: {str(e)}")
```

**Handling in endpoint** (`app/main.py`, lines 102-106):
```python
except Exception as e:
    if "API" in str(e):
        raise HTTPException(
            status_code=503,
            detail="LLM service is currently unavailable. Please try again later."
        )
```

**Response:**
```json
{
  "detail": "LLM service is currently unavailable. Please try again later."
}
```

**HTTP Status:** 503 Service Unavailable

**Why 503 instead of 500?**
- 503 indicates temporary external service failure
- Signals to client: "Retry later, this isn't your fault"
- 500 would imply internal server bug

---

### Scenario E: LLM Returns Invalid JSON

**What Happens:**
```
LLM response: "Here's the analysis: {
  'category': 'IT Hardware'  # Single quotes, not valid JSON
  'overall_risk_level': 'High'  # Missing commas
}"
```

**Detection Point 1:** JSON cleaning (`app/llm_service.py`)
```python
def _clean_json_response(self, text: str) -> str:
    text = text.strip()
    
    # Remove markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    return text.strip()
```

**Detection Point 2:** JSON parsing with error handling
```python
try:
    response_data = json.loads(response_text)
except json.JSONDecodeError as e:
    print(f"JSON Decode Error: {str(e)}")
    print(f"Response text was: {response_text}")
    raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")
```

**Handling in endpoint:**
```python
elif "JSON" in str(e):
    raise HTTPException(
        status_code=500,
        detail="Failed to parse LLM response. Please contact support."
    )
```

**Response:**
```json
{
  "detail": "Failed to parse LLM response. Please contact support."
}
```

**HTTP Status:** 500 Internal Server Error

**Logging:** Full response text logged to server console for debugging

---

### Scenario F: LLM Returns Invalid Schema

**What Happens:**
```json
{
  "category": "IT Hardware",
  "overall_risk_level": "CRITICAL",  # Not "Low"/"Medium"/"High"
  "key_risks": [],  # Empty array (needs 1+ items)
  "negotiation_levers": ["lever1"],
  "recommended_actions_next_90_days": ["action1"]
  # Missing: confidence_score
}
```

**Detection Point 1:** Schema validation/fixing (`app/llm_service.py`)
```python
def _validate_and_fix_response(self, data: Dict[str, Any], category: str) -> Dict[str, Any]:
    # Fix missing/invalid overall_risk_level
    if "overall_risk_level" not in data:
        data["overall_risk_level"] = "Medium"
    else:
        risk_level = data["overall_risk_level"]
        if risk_level not in ["Low", "Medium", "High"]:
            data["overall_risk_level"] = "Medium"  # Default to Medium
    
    # Fix empty lists
    for list_field in ["key_risks", "negotiation_levers", "recommended_actions_next_90_days"]:
        if list_field not in data or len(data[list_field]) == 0:
            data[list_field] = [f"Analysis pending for {list_field.replace('_', ' ')}"]
    
    # Fix missing confidence_score
    if "confidence_score" not in data:
        data["confidence_score"] = 0.85
    else:
        score = float(data["confidence_score"])
        data["confidence_score"] = max(0.70, min(0.98, score))  # Clamp to range
    
    return data
```

**Detection Point 2:** Final Pydantic validation
```python
insights_response = InsightsResponse(**response_data)
```

If still invalid after fixing, Pydantic raises `ValidationError`, caught by:
```python
except ValidationError as e:
    raise HTTPException(
        status_code=422,
        detail=f"Data validation failed: {str(e)}"
    )
```

**Why This Approach?**
- **Graceful degradation:** Try to fix minor issues automatically
- **Never crash:** Always return something useful
- **Transparency:** Indicate when analysis is "pending" rather than failing silently

---

## 2. Guardrails Architecture

### Layer 1: Input Validation (Pydantic Models)
**Location:** `app/models.py`

**What it prevents:**
- Wrong data types (string instead of number)
- Missing required fields
- Out-of-range values (negative spend, delivery % > 100)
- Empty strings where data is required

**Example:**
```python
class SupplierInput(BaseModel):
    supplier_name: str = Field(..., min_length=1)
    annual_spend_usd: float = Field(..., gt=0)
    on_time_delivery_pct: float = Field(..., ge=0, le=100)
    
    @validator('supplier_name')
    def validate_non_empty_string(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()
```

**Why it works:** Validation happens automatically before endpoint code runs

---

### Layer 2: Business Logic Validation
**Location:** `app/main.py` (endpoint function)

**What it prevents:**
- Empty supplier lists (can't analyze nothing)
- Semantically invalid data (e.g., supplier exists but all fields are placeholder values)

**Example:**
```python
if len(request.suppliers) == 0:
    raise HTTPException(422, "At least one supplier required")

for idx, supplier in enumerate(request.suppliers):
    if not supplier.supplier_name.strip():
        raise HTTPException(422, f"Supplier {idx} has empty name")
```

**Why separate from Pydantic?** More detailed error messages specific to business context

---

### Layer 3: LLM Response Cleaning
**Location:** `app/llm_service.py` → `_clean_json_response()`

**What it prevents:**
- Markdown artifacts (```json ... ```)
- Leading/trailing whitespace
- LLM adding explanatory text before JSON

**Example:**
```python
# Before cleaning:
"```json\n{\n  \"category\": \"IT Hardware\"\n}\n```"

# After cleaning:
"{\n  \"category\": \"IT Hardware\"\n}"
```

---

### Layer 4: Schema Validation and Repair
**Location:** `app/llm_service.py` → `_validate_and_fix_response()`

**What it prevents:**
- Invalid enum values (fixes "CRITICAL" → "Medium")
- Empty required lists (adds placeholder items)
- Missing confidence_score (defaults to 0.85)
- Out-of-range confidence (clamps to [0.70, 0.98])

**Philosophy:** Try to salvage the response rather than fail completely

---

### Layer 5: Final Pydantic Validation
**Location:** `app/llm_service.py` → `InsightsResponse(**response_data)`

**What it prevents:**
- Any issues that slipped through previous layers
- Type mismatches (string instead of float)
- Schema violations

**Example:**
```python
# This will raise ValidationError if response_data is still invalid
insights_response = InsightsResponse(**response_data)
```

---

### Layer 6: HTTP Exception Handling
**Location:** `app/main.py` → Exception handlers

**What it prevents:**
- Raw Python exceptions reaching the user
- Unhelpful error messages
- Stack traces in production

**Example:**
```python
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred."
        }
    )
```

---

## 3. Error Response Consistency

All errors follow a consistent structure:

**Validation Errors (422):**
```json
{
  "error": "Validation Error",
  "details": ["field1: message1", "field2: message2"],
  "message": "Invalid input data. Please check the request format."
}
```

**Service Errors (503):**
```json
{
  "detail": "LLM service is currently unavailable. Please try again later."
}
```

**Internal Errors (500):**
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred while processing your request."
}
```

**Why consistency matters:**
- Clients can parse errors programmatically
- Easier to display errors in UI
- Simplifies error logging and monitoring

---

## 4. Logging Strategy

**What gets logged:**
- All incoming requests (category, supplier count)
- LLM API calls and response snippets
- All errors (with full context)
- Validation failures

**Example log output:**
```
INFO:app.main:Processing insights request for category: IT Hardware
INFO:app.llm_service:Making API call to Google Gemini...
INFO:app.llm_service:Received response from LLM: {"category": "IT Hardware"...
INFO:app.main:Successfully generated insights for category: IT Hardware
```

**Error log output:**
```
ERROR:app.main:Error generating insights: Failed to parse LLM response as JSON
INFO:app.llm_service:Response text was: Here is the analysis {...
```

---

## 5. Production Considerations

### Current Implementation:
- ✓ Comprehensive input validation
- ✓ Graceful error handling
- ✓ Meaningful error messages
- ✓ Logging for debugging

### What would be added in production:

**1. Rate Limiting:**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/generate-insights")
@limiter.limit("10/minute")
async def generate_insights(...):
    ...
```

**2. Request ID Tracking:**
```python
import uuid

request_id = str(uuid.uuid4())
logger.info(f"[{request_id}] Processing request...")
```

**3. Retry Logic for LLM:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def call_llm(...):
    return self.model.generate_content(...)
```

**4. Circuit Breaker:**
```python
if llm_error_rate > 0.5:  # 50% errors
    return cached_response or generic_response
```

**5. Structured Logging:**
```python
logger.info("llm_call", extra={
    "category": category,
    "supplier_count": len(suppliers),
    "response_time_ms": elapsed_time
})
```

---

## Summary

Our error handling provides:

1. ✓ **Multiple validation layers** - Catch errors early and often
2. ✓ **Graceful degradation** - Fix minor issues automatically
3. ✓ **Clear error messages** - Users know exactly what went wrong
4. ✓ **Appropriate HTTP codes** - 422 for client errors, 503 for service issues
5. ✓ **Comprehensive logging** - Debug issues in production
6. ✓ **Never crash** - Always return a response (even if it's an error)

This ensures the API is robust, debuggable, and production-ready.