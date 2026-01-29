# Procurement Insights API

A FastAPI-based service that uses AI to generate structured procurement insights from supplier data. Built for a mid-size manufacturing company to support supplier negotiations, risk mitigation, and contract renewal decisions.

---

## Quick Start

### Prerequisites
- Python 3.9+
- Google Gemini API key (get one at https://aistudio.google.com/apikey)

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd procurement-insights-api
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

5. Run the API
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

---

## Usage

### Interactive Documentation
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

### Example Request

**Endpoint:** `POST /generate-insights`

**Request Body:**
```json
{
  "category": "IT Hardware",
  "suppliers": [
    {
      "supplier_name": "TechSource Inc.",
      "annual_spend_usd": 4200000,
      "on_time_delivery_pct": 92,
      "contract_expiry_months": 6,
      "single_source_dependency": true,
      "region": "North America"
    },
    {
      "supplier_name": "GlobalComp Solutions",
      "annual_spend_usd": 3100000,
      "on_time_delivery_pct": 85,
      "contract_expiry_months": 3,
      "single_source_dependency": false,
      "region": "Asia"
    },
    {
      "supplier_name": "NextGen Systems",
      "annual_spend_usd": 1800000,
      "on_time_delivery_pct": 97,
      "contract_expiry_months": 12,
      "single_source_dependency": false,
      "region": "Europe"
    }
  ]
}
```

**Using curl:**
```bash
curl -X POST "http://localhost:8000/generate-insights" \
  -H "Content-Type: application/json" \
  -d @examples/example_request.json
```

**Using Python:**
```bash
python test/test_api.py
```

### Example Response

```json
{
  "category": "IT Hardware",
  "overall_risk_level": "High",
  "key_risks": [
    "High concentration risk with TechSource Inc. as a single source for 46% of spend.",
    "Imminent contract expiration for GlobalComp Solutions (3 months) and TechSource Inc. (6 months).",
    "Subpar delivery performance from GlobalComp Solutions (85% OTD) impacting operational reliability.",
    "Limited geographic diversification for critical spend."
  ],
  "negotiation_levers": [
    "Competitive sourcing for GlobalComp Solutions due to poor OTD and expiring contract.",
    "Volume consolidation potential with high-performing NextGen Systems.",
    "Urgency of contract expirations to demand improved terms or explore alternatives.",
    "Mitigate single-source risk for TechSource Inc. by identifying alternative suppliers."
  ],
  "recommended_actions_next_90_days": [
    "Launch RFP for GlobalComp Solutions contract renegotiation (Due in 30 days).",
    "Initiate dual-sourcing project for TechSource Inc. (Due in 60 days).",
    "Develop performance improvement plan with GlobalComp Solutions (Due in 45 days).",
    "Conduct strategic review of IT Hardware sourcing for geographic diversification (Due in 90 days)."
  ],
  "confidence_score": 0.85
}
```

---

## Assumptions Made

### Data Assumptions
- **Currency is USD:** All spend amounts are assumed to be in US dollars
- **On-time delivery percentage:** Assumes this is calculated consistently across suppliers
- **Single-source dependency:** Assumes this flag accurately reflects whether alternative suppliers exist

### Business Assumptions
- **Risk thresholds:** 
  - Delivery performance < 90% is considered problematic
  - Contracts expiring within 3 months require urgent attention
  - Single-source dependencies are always high risk
- **Time horizon:** Recommendations focus on the next 90 days (short-term tactical actions)

### Technical Assumptions
- **Small datasets:** Optimized for 3-10 suppliers per category
- **Synchronous processing:** Assumes response time under 5 seconds is acceptable
- **Internet connectivity:** Requires stable connection to Google's Gemini API

---

## Production Improvements

If this were deployed to production, here are key enhancements I would make:

### Security
- **API authentication:** Add API key or OAuth2 authentication
- **Rate limiting:** Prevent abuse with per-user request limits
- **Input sanitization:** Additional validation to prevent injection attacks
- **HTTPS only:** Enforce encrypted connections

### Performance
- **Caching:** Cache identical requests to reduce LLM API calls
- **Async processing:** For large supplier lists (50+), use background jobs
- **Database integration:** Store historical analyses for trend tracking
- **Load balancing:** Distribute requests across multiple instances

### Reliability
- **Retry logic:** Automatically retry failed LLM API calls
- **Circuit breaker:** Temporarily disable LLM if error rate is too high
- **Fallback mechanisms:** Return cached or rule-based results if LLM is down
- **Health monitoring:** Track API uptime, response times, error rates

### Features
- **Historical analysis:** Compare current vs. past supplier performance
- **Batch processing:** Analyze multiple categories simultaneously
- **Custom thresholds:** Allow users to define their own risk criteria
- **Multi-language support:** Generate insights in different languages
- **Export functionality:** PDF reports, Excel exports for executives

### Data Integration
- **ERP integration:** Direct connection to SAP, Oracle, etc.
- **Real-time updates:** Sync supplier data automatically
- **Data validation:** Cross-check against master supplier database
- **Audit logging:** Track who accessed what insights when

### Quality Assurance
- **A/B testing:** Compare different prompts or models
- **Human feedback loop:** Allow users to rate insight quality
- **Confidence calibration:** Track if 0.85 confidence actually means 85% accuracy
- **Automated testing:** Unit tests, integration tests, load tests

### Cost Optimization
- **Intelligent routing:** Use cheaper models for simple cases
- **Request batching:** Group multiple small requests
- **Response streaming:** Start returning results before full completion
- **Usage analytics:** Track and optimize per-user costs

---

## API Endpoints

### `POST /generate-insights`
Generate procurement insights from supplier data.

**Input:** Category name + list of suppliers with metrics  
**Output:** Risk level, key risks, negotiation levers, recommended actions, confidence score

### `GET /health`
Check if the API is running.

**Output:** `{"status": "healthy"}`

### `GET /`
API information and available endpoints.

---

## Technology Stack

- **Framework:** FastAPI 0.115.0
- **LLM:** Google Gemini 2.5 Flash
- **Validation:** Pydantic 2.9.2
- **Language:** Python 3.9+

---

## Documentation

Detailed documentation is available in the `docs/` directory:

- `PROMPT_DESIGN.md` - How LLM prompts are structured
- `ERROR_HANDLING.md` - Error scenarios and guardrails
- `EXAMPLE_OUTPUT.md` - Detailed output analysis
- `CONFIDENCE_SCORE.md` - How confidence scores are calculated
- `DESIGN_DECISIONS.md` - Architectural choices and scaling
- `TIME_TRACKING.md` - Development time breakdown

---

## Troubleshooting

**Issue:** "GOOGLE_API_KEY not found in environment variables"  
**Solution:** Make sure you've created a `.env` file with your API key

**Issue:** "404 models/gemini-... is not found"  
**Solution:** The model name may have changed. Run `python list_models.py` to see available models

**Issue:** "LLM service is currently unavailable"  
**Solution:** Check your API key validity and internet connection. Verify you haven't exceeded Gemini's rate limits.

**Issue:** Response is slow (>10 seconds)  
**Solution:** This may happen with large supplier lists. Consider reducing the number of suppliers or implementing async processing.

---

## Testing

Run the test script:
```bash
python test/test_api.py
```

This will send the example request and display the response. The response is also saved to `examples/example_response.json`.

---

## License

This project was created as a coding assignment for educational purposes.

---

## Contact

For questions or issues, please refer to the documentation in the `docs/` directory or open an issue in the repository.