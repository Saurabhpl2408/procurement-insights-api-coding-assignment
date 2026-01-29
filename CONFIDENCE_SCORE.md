# Confidence Score Logic Documentation

## Overview
The confidence score is a number between 0.70 and 0.98 that shows how confident the system is in its analysis and recommendations.

---

## How It's Calculated

The LLM calculates the confidence score using guidelines I provided in the prompt.

**Guidelines Given to LLM:**
```
Start with base 0.85 (we have complete, structured data)
Deduct 0.05 if only 1-2 suppliers (limited comparison basis)
Deduct 0.05 if any data appears inconsistent or unclear
Deduct 0.10 if analysis requires significant assumptions
Add 0.05 if there are clear, unambiguous risk signals

Expected ranges:
- 0.90-0.95: Complete data, 3+ suppliers, clear patterns
- 0.80-0.89: Good data quality, some minor gaps
- 0.70-0.79: Acceptable data, but requires assumptions
```

---

## Why Start with 0.85?

**Why not 1.0 (perfect confidence)?**

Because we're making predictions about the future. We don't have:
- Market conditions or competitor pricing
- Internal budgets and constraints
- Future supplier capacity or performance trends
- All the political and relationship factors that affect real decisions

**Why not lower like 0.5?**

Because we do have good data:
- All required fields are present and validated
- Multiple suppliers to compare (not just one)
- Clear metrics like delivery percentages and spend amounts
- Objective risk indicators (single-source flag, contract dates)

**So 0.85 means:** "I have solid data and can make good recommendations, but I'm not claiming to know everything."

Think of it like a weather forecast:
- 1.0 = "The sun rose this morning" (already happened, certain)
- 0.85 = "It will rain tomorrow based on radar" (good data, likely)
- 0.5 = "It might rain next month" (too far out, too uncertain)

---

## Adjustment Factors

### Factor 1: Number of Suppliers
- 1-2 suppliers: -0.05 (hard to compare with so few)
- 3+ suppliers: No deduction (good sample size)

Our dataset has 3 suppliers, so no deduction.

### Factor 2: Data Quality
- Missing or inconsistent fields: -0.05
- Everything complete and logical: No deduction

Our dataset is complete, so no deduction.

### Factor 3: Assumptions
- Need to make significant guesses: -0.10
- Can work directly from the data: No deduction

Our dataset has all the info needed, so no deduction.

### Factor 4: Clear Signals
- Obvious problems visible in data: +0.05 bonus
- Ambiguous or unclear situation: No bonus

Our dataset has clear signals (single-source risk, low delivery performance, expiring contracts), but the LLM didn't add the bonus because 0.85 already felt right.

---

## Our Dataset Example

```
Base Score:                    0.85
Number of suppliers (3):       -0.00  (no penalty)
Data quality:                  -0.00  (complete)
Assumptions needed:            -0.00  (none)
Clear signals:                 +0.00  (not added)
Final Score:                   0.85
```

---

## Safety Bounds

After the LLM calculates the score, the code validates it:

```python
if score is missing:
    use 0.85 as default
else:
    clamp score between 0.70 and 0.98
```

**Why 0.70 minimum?** Below that suggests data quality is too poor to trust.

**Why 0.98 maximum?** Never 1.0 because perfect certainty doesn't exist in business decisions.

---

## What Different Scores Mean

**0.90-0.98: Excellent**
- 5+ suppliers with complete data
- Clear patterns and signals
- "Follow these recommendations confidently"

**0.80-0.89: Good** (Our case: 0.85)
- 3-4 suppliers with complete data
- Some clear signals
- "Analysis is solid, proceed with normal due diligence"

**0.70-0.79: Acceptable**
- 1-2 suppliers or some missing data
- Requires moderate assumptions
- "Use as guidance but validate before major decisions"

**Below 0.70: Poor**
- Would trigger a warning
- "Data quality too low, gather more information"

---

## Key Takeaway

**Confidence = 0.85 means:**

"I have good data, the analysis makes sense, and these are solid recommendations. But I'm acknowledging there's always some uncertainty in business decisions, so use appropriate judgment."
