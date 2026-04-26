from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
import models

router = APIRouter()


def product_to_dict(product: models.Product) -> dict:
    if not product:
        return None

    img = getattr(product, "img", None) or ""

    return {
        "id": getattr(product, "id", None),
        "title": getattr(product, "title", ""),
        "article": getattr(product, "article", None),
        "description": getattr(product, "description_ru", None),
        "price": getattr(product, "price", None),
        "old_price": getattr(product, "old_price", None),
        "img": img,
        "category": getattr(product, "category", None),
        "category_slug": getattr(product, "category_slug", None),
        "in_stock": getattr(product, "in_stock", True),
        "slug": getattr(product, "slug", None),
        "material": getattr(product, "material_ru", None),
        "size": getattr(product, "size", None),
        "path": f"/product/{getattr(product, 'id', '')}",
        "url": f"/product/{getattr(product, 'slug', '')}" if getattr(product, "slug", None) else None,
        "badge": "new" if getattr(product, "is_new", False) else ("sale" if getattr(product, "old_price", None) else None),
        "images": [img] if img else [],
    }


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
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        query = query.filter(
            or_(
                models.Product.title.ilike(like, escape="\\"),
                models.Product.article.ilike(like, escape="\\"),
                models.Product.description_ru.ilike(like, escape="\\"),
            )
        )

    if in_stock is not None:
        query = query.filter(models.Product.in_stock == in_stock)

    products = query.all()
    return [product_to_dict(p) for p in products]


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Товар с ID {product_id} не найден"
        )

    return product_to_dict(product)