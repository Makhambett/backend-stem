from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter()

# ==========================================
# 🔧 БЕЗОПАСНАЯ ФУНКЦИЯ КОНВЕРТАЦИИ
# (работает с любой структурой модели)
# ==========================================

def product_to_dict(product: models.Product) -> dict:
    """
    Конвертирует SQLAlchemy модель в словарь.
    Использует getattr с дефолтными значениями — не упадёт, если поля нет.
    """
    if not product:
        return None
    
    # Безопасно получаем поля: если нет в модели — вернётся None
    return {
        "id": getattr(product, "id", None),
        "title": getattr(product, "title", ""),
        "article": getattr(product, "article", None),
        "description": getattr(product, "description", None),
        "price": getattr(product, "price", None),
        "old_price": getattr(product, "old_price", None),
        "img": getattr(product, "img", None),
        "category": getattr(product, "category", None),
        "category_slug": getattr(product, "category_slug", None),
        "in_stock": getattr(product, "in_stock", True),
        "slug": getattr(product, "slug", None),
        
        # Генерируем поля для фронтенда (на основе имеющихся данных)
        "path": f"/product/{getattr(product, 'id', '')}",
        "url": f"/product/{getattr(product, 'slug', '')}" if getattr(product, "slug", None) else None,
        "srcSet": None,  # Можно настроить позже, если есть разные размеры картинок
        "badge": "new" if getattr(product, "is_new", False) else ("sale" if getattr(product, "old_price", None) else None),
        "colors": getattr(product, "colors", None),
        "specs": getattr(product, "specs", None),
        "images": [getattr(product, "img", None)] if getattr(product, "img", None) else [],
    }


# ==========================================
# 🚀 ЭНДПОИНТЫ
# ==========================================

@router.get("/")
def get_products(
    category: str = Query(None),
    q: str = Query(None),
    in_stock: bool = Query(None),
    db: Session = Depends(get_db)
):
    """
    Получение списка товаров с фильтрацией и поиском
    """
    query = db.query(models.Product)
    
    # Фильтр по категории
    if category:
        query = query.filter(models.Product.category_slug == category)
    
    # Поиск по названию (регистронезависимый)
    if q:
        query = query.filter(models.Product.title.ilike(f"%{q}%"))
    
    # Фильтр по наличию
    if in_stock is not None:
        query = query.filter(models.Product.in_stock == in_stock)
    
    # Получаем товары
    products = query.all()
    
    # Конвертируем в словари (безопасно)
    return [product_to_dict(p) for p in products]


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Получение детальной информации о товаре по ID
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Товар с ID {product_id} не найден"
        )
    
    return product_to_dict(product)