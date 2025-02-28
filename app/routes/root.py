import asyncpg
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from aioprometheus.asgi.starlette import metrics
from app.db.database import get_pool

router = APIRouter(tags=['Root'])

# Pydantic model for request body
class EmailRequest(BaseModel):
    email: str


@router.get("/")
async def root():
    result = {"message": "Hello World"}

    return result


@router.post("/store-email/")
async def store_email(email_request: EmailRequest, pool: asyncpg.Pool = Depends(get_pool)):
    email = email_request.email

    # Validate email (basic validation)
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Insert email into the database
    try:
        async with pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO wishlists (email) VALUES ($1)",
                email
            )
        return {"message": "Email stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


router.add_route("/metrics", metrics)
