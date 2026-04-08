from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from datetime import datetime
import models

router = APIRouter()

class OrderCreate(BaseModel):
    product_id: int
    product_title: str
    client_name: str = None
    client_phone: str = None
    message: str = None

@router.post("/")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    db_order = models.Order(
        product_id=order.product_id,
        product_title=order.product_title,
        client_name=order.client_name,
        client_phone=order.client_phone,
        message=order.message,
        status="new",
        created_at=str(datetime.now())
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/")
def get_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).all()