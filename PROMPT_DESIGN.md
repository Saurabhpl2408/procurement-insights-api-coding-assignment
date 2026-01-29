# LLM Prompt Design Documentation

## Overview
This document explains the prompts used to generate procurement insights from supplier data using Google Gemini 2.5 Flash.

---

## 1. System Prompt

```
You are a procurement analytics expert specializing in supplier risk assessment and sourcing strategy for manufacturing companies.

Your task is to analyze supplier data and generate actionable insights for procurement executives.

CRITICAL REQUIREMENTS:
1. You must respond ONLY with valid JSON matching the exact schema provided
2. No explanatory text before or after the JSON
3. No markdown formatting or code blocks
4. All risk assessments must be data-driven and based on the input metrics
5. Focus on actionable, executive-level insights suitable for mobile dashboards

ANALYSIS FRAMEWORK:
- Assess concentration risk (single source dependencies, spend distribution)
- Evaluate delivery performance and operational risk
- Identify contract timing urgencies (expiring within 6 months = high priority)
- Consider geographic diversification
- Generate concrete, time-bound action items
```

**Purpose:** 
- Sets the LLM's role as a procurement expert.
- Defines output constraints (JSON only, no extra text).
- Provides the analytical framework to follow.

---

## 2. User Prompt

The user prompt is dynamically generated for each request with the actual supplier data.

```
Analyze the following procurement data and generate structured insights.

CATEGORY: {category}

SUPPLIER DATA:
{suppliers_json}

Generate a JSON response with this EXACT structure:
{
  "category": "string (the category name)",
  "overall_risk_level": "Low OR Medium OR High",
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "negotiation_levers": ["lever 1", "lever 2", "lever 3"],
  "recommended_actions_next_90_days": ["action 1", "action 2", "action 3"],
  "confidence_score": 0.XX
}

SCORING GUIDELINES:
- overall_risk_level: "High" if single-source dependency exists OR contracts expiring within 3 months OR delivery performance < 90%
- overall_risk_level: "Medium" if moderate concerns (contracts 3-6 months, delivery 90-95%, concentrated spend)
- overall_risk_level: "Low" if well-diversified, strong performance, adequate contract runway
- key_risks: Must identify 3-5 specific risks based on data (concentration, timing, performance, geographic)
- negotiation_levers: Must identify 3-5 specific leverage points (competitive alternatives, volume, contract timing, performance gaps)
- recommended_actions_next_90_days: Must provide 3-5 concrete, time-bound actions prioritized by urgency

Calculate confidence_score based on these factors:
- Start with base 0.85 (we have complete, structured data)
- Deduct 0.05 if only 1-2 suppliers (limited comparison basis)
- Deduct 0.05 if any data appears inconsistent or unclear
- Deduct 0.10 if analysis requires significant assumptions
- Add 0.05 if there are clear, unambiguous risk signals

Typical ranges:
- 0.90-0.95: Complete data, 3+ suppliers, clear patterns
- 0.80-0.89: Good data quality, some minor gaps or ambiguity
- 0.70-0.79: Acceptable data, but requires some assumptions

For this specific dataset with 3 suppliers and complete fields, confidence should be 0.85-0.92.

Respond with ONLY the JSON object, no other text.
```

---

## 3. How These Prompts Enforce Structured Output

### Strategy 1: Explicit Schema
The prompt shows the exact JSON structure expected, including field names and types. This acts as a template for the LLM.

### Strategy 2: Multiple Reminders
The requirement for JSON-only output is repeated several times:
- In the system prompt: "respond ONLY with valid JSON"
- In the user prompt: "Generate a JSON response with this EXACT structure"
- At the end: "Respond with ONLY the JSON object, no other text"

This repetition helps because LLMs can sometimes forget instructions midway through generation.

### Strategy 3: Specific Constraints
Instead of saying "assess the risk level," the prompt provides concrete rules:
- "High if delivery performance < 90%"
- "Medium if contracts 3-6 months"

These objective thresholds prevent subjective interpretation.

### Strategy 4: Low Temperature Setting
The model uses temperature=0.2, which means:
- Less randomness in responses
- More deterministic outputs
- Favors structured completions over creative variations

---

## 4. How These Prompts Avoid Hallucination

### Method 1: Data Grounding
The prompt explicitly provides all supplier data and instructs the LLM to base analysis only on that data. No external knowledge is needed.

### Method 2: Objective Thresholds
Using mathematical comparisons like "< 90%" instead of subjective terms like "poor performance" prevents the LLM from making up facts.

### Method 3: Constrained Scope
The prompt specifies exactly what categories to analyze: concentration, timing, performance, and geographic factors. This prevents inventing new risk categories.

### Method 4: Specific Output Requirements
Requiring "3-5 concrete, time-bound actions" prevents vague recommendations and forces specificity.

### Method 5: Post-Generation Validation
After the LLM responds, the code:
1. Cleans the response (removes markdown artifacts)
2. Parses and validates JSON structure
3. Checks field types and ranges
4. Validates enum values ("Low"/"Medium"/"High")
5. Clamps confidence score to [0.70, 0.98]

Even if the LLM makes a mistake, validation catches it.

---

## 5. Why Gemini 2.5 Flash

I selected Google Gemini 2.5 Flash for this project because:

- Good at following JSON schemas precisely
- Fast response time (under 2 seconds)
- Cost-effective for the number of requests
- Large context window handles multiple suppliers well
- I had available API credits

Alternative options like Claude Sonnet 4 would work similarly but required more API credits than I had available.

---

## 6. Testing and Refinement

During development, I encountered a few issues that required prompt adjustments:

**Issue 1:** LLM sometimes wrapped JSON in markdown code blocks
**Solution:** Added explicit instruction "No markdown formatting or code blocks" and implemented cleaning logic

**Issue 2:** Occasionally got non-standard risk levels like "Critical" or "Moderate-High"
**Solution:** Strengthened the constraint by showing "Low OR Medium OR High" with capitalized OR

**Issue 3:** Confidence scores sometimes came back as 0.99 or 1.0
**Solution:** Added expected ranges and clamping logic to keep scores realistic

---

## Summary

The prompts achieve structured output and avoid hallucination through:

1. Explicit JSON schema with examples
2. Objective threshold-based rules
3. Data grounding (analysis must use provided data)
4. Specific output constraints
5. Low temperature configuration
6. Post-generation validation

This approach ensures the API returns valid, useful, and trustworthy insights for procurement decisions.