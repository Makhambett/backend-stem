from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter()

@router.get("/")
def get_products(
    category: str = Query(None),
    q: str = Query(None),
    in_stock: bool = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)
    if category:
        query = query.filter(models.Product.category_slug == category)
    if q:
        query = query.filter(models.Product.title.ilike(f"%{q}%"))
    if in_stock is not None:
        query = query.filter(models.Product.in_stock == in_stock)
    return query.all()

@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    return db.query(models.Product).filter(models.Product.id == product_id).first()