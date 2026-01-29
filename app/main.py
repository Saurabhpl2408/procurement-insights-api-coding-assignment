from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from app.models import InsightsRequest, InsightsResponse
from app.llm_service import LLMService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Procurement Insights API",
    description="Generate structured sourcing insights for procurement decision-making",
    version="1.0.0"
)

llm_service = LLMService()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": errors,
            "message": "Invalid input data. Please check the request format."
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request."
        }
    )


@app.post(
    "/generate-insights",
    response_model=InsightsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Successfully generated procurement insights"},
        422: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
async def generate_insights(request: InsightsRequest):
    try:
        if not request.suppliers or len(request.suppliers) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Supplier list cannot be empty. At least one supplier is required."
            )
        
        for idx, supplier in enumerate(request.suppliers):
            if not supplier.supplier_name or not supplier.supplier_name.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Supplier at index {idx} has an empty or invalid name."
                )
            
            if supplier.annual_spend_usd <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Supplier '{supplier.supplier_name}' has invalid annual spend (must be > 0)."
                )
            
            if not (0 <= supplier.on_time_delivery_pct <= 100):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Supplier '{supplier.supplier_name}' has invalid delivery percentage (must be 0-100)."
                )
            
            if supplier.contract_expiry_months < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Supplier '{supplier.supplier_name}' has invalid contract expiry months (must be >= 0)."
                )
        
        logger.info(f"Processing insights request for category: {request.category}")
        
        insights = llm_service.generate_insights(request)
        
        logger.info(f"Successfully generated insights for category: {request.category}")
        
        return insights
    
    except HTTPException:
        raise
    
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Data validation failed: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        
        if "API" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service is currently unavailable. Please try again later."
            )
        elif "JSON" in str(e):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse LLM response. Please contact support."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while generating insights: {str(e)}"
            )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Procurement Insights API",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    return {
        "message": "Procurement Insights API",
        "endpoints": {
            "generate_insights": "/generate-insights (POST)",
            "health": "/health (GET)",
            "docs": "/docs (GET)"
        }
    }