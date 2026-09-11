from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from backend.app.database.neo4j_service import Neo4jService
from backend.app.services.ingestion_service import IngestionService
from backend.app.api.deps import get_current_user_id

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])
db = Neo4jService()
ingestion = IngestionService(db=db)

class TransactionCreateSchema(BaseModel):
    account_id: Optional[str] = Field(None, description="Account ID")
    amount: Optional[float] = Field(None, gt=0, description="Transaction Amount (if structured)")
    description: Optional[str] = Field(None, max_length=250, description="Description")
    category_name: Optional[str] = Field(None, max_length=100, description="Category name")
    transaction_type: Optional[str] = Field("EXPENSE", description="EXPENSE or INCOME")
    date_str: Optional[str] = Field(None, description="Date in YYYY-MM-DD")
    natural_language_input: Optional[str] = Field(None, description="Natural language input e.g. 'I spent ₹5000 on food today'")

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, value):
        if value is None:
            return value
        normalized = value.upper()
        if normalized not in {"EXPENSE", "INCOME"}:
            raise ValueError("transaction_type must be EXPENSE or INCOME")
        return normalized

class TransactionUpdateSchema(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category_name: Optional[str] = None
    date_str: Optional[str] = None

@router.get("")
def list_transactions(user_id: str = Depends(get_current_user_id), limit: int = Query(100, ge=1, le=1000)):
    transactions = db.get_all_transactions(user_id, limit=limit)
    categories = db.get_categories()
    accounts = db.get_user_accounts(user_id)
    return {
        "transactions": transactions,
        "categories": categories,
        "accounts": accounts
    }

@router.post("")
def create_transaction(payload: TransactionCreateSchema, user_id: str = Depends(get_current_user_id)):
    try:
        if payload.natural_language_input:
            return ingestion.ingest_transaction_from_text(
                text=payload.natural_language_input,
                user_id=user_id,
                account_id=payload.account_id
            )
        
        if payload.amount is None or payload.amount <= 0:
            raise HTTPException(status_code=400, detail="Transaction amount must be greater than 0")

        return ingestion.ingest_transaction(
            user_id=user_id,
            account_id=payload.account_id,
            amount=payload.amount,
            description=payload.description or "Transaction",
            category_name=payload.category_name or "General",
            transaction_type=payload.transaction_type or "EXPENSE",
            date_str=payload.date_str
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{transaction_id}")
def update_transaction(transaction_id: str, payload: TransactionUpdateSchema, user_id: str = Depends(get_current_user_id)):
    try:
        updated = db.update_transaction(
            user_id=user_id,
            transaction_id=transaction_id,
            amount=payload.amount,
            description=payload.description,
            category_name=payload.category_name,
            date_str=payload.date_str
        )
        return {
            "status": "SUCCESS",
            "transaction": updated
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        res = db.delete_transaction(user_id, transaction_id)
        return {
            "status": "SUCCESS",
            "message": f"Transaction '{transaction_id}' deleted successfully",
            "restored_balance": res["restored_balance"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
