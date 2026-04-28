from datetime import datetime
import os
import re
from typing import Optional, List, Union

import httpx
import models
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session

from database import get_db

# ✅ Загружаем переменные окружения
load_dotenv()

router = APIRouter()

# ==========================================
# 🔧 НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ==========================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("TELEGRAM_GROUP_CHAT_ID")
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")


# ==========================================
# 📦 PYDANTIC МОДЕЛИ (обновлено для корзины)
# ==========================================

class CartItem(BaseModel):
    """Модель товара в корзине"""
    name: str
    article: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = 1
    url: Optional[str] = None


class ApplicationCreate(BaseModel):
    name: str
    phone: str
    username: Optional[str] = None
    comment: Optional[str] = None
    
    # 🔹 Вариант 1: один товар (обратная совместимость)
    product_name: Optional[str] = None
    article: Optional[str] = None
    product_url: Optional[str] = None
    
    # 🔹 Вариант 2: корзина с товарами
    products: Optional[List[CartItem]] = None

    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2 or len(cleaned) > 50:
            raise ValueError('Имя должно быть от 2 до 50 символов')
        if not re.fullmatch(r"[A-Za-zА-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІіЁё\s\-]+", cleaned):
            raise ValueError('Имя содержит недопустимые символы')
        return cleaned

    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        if len(digits) == 10:
            digits = "7" + digits
        if len(digits) < 11 or len(digits) > 15:
            raise ValueError('Некорректный номер телефона')
        return v

    @field_validator('username')
    @classmethod
    def clean_username(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.replace("@", "").strip() or None
        return None

    # 🔹 Валидация: либо один товар, либо список товаров
    @model_validator(mode='after')
    def check_products_or_product_name(self):
        if not self.product_name and not self.products:
            raise ValueError('Укажите либо product_name, либо products')
        return self


class TakeApplication(BaseModel):
    manager_id: int
    manager_name: str


# ==========================================
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================

def normalize_phone(phone: str) -> str:
    """Нормализует номер телефона к формату +7 (XXX) XXX-XX-XX"""
    digits = "".join(ch for ch in phone if ch.isdigit())
    
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    if len(digits) < 11 or len(digits) > 15:
        raise HTTPException(status_code=400, detail="Некорректный номер телефона")
    
    if len(digits) == 11 and digits.startswith("7"):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return f"+{digits}"


def status_label(status: str) -> str:
    mapping = {
        "new": "🟡 Новая",
        "in_progress": "🟠 В работе",
        "done": "✅ Закрыта",
        "rejected": "❌ Отклонена",
    }
    return mapping.get(status, status)


def format_products_for_display(products: Optional[List[dict]]) -> tuple[str, str]:
    """
    Форматирует список товаров для отображения в Битрикс/Телеграм
    
    Returns:
        tuple: (краткое название, подробный список)
    """
    if not products:
        return "Не указан", "—"
    
    names = [p.get('name', 'Товар') for p in products if p.get('name')]
    articles = [p.get('article') for p in products if p.get('article')]
    
    # Краткое название для заголовка
    if len(names) == 1:
        short_name = names[0]
    elif len(names) <= 3:
        short_name = ", ".join(names)
    else:
        short_name = f"{names[0]}, {names[1]} и ещё {len(names) - 2} товаров"
    
    # Подробный список для комментариев
    if articles:
        detailed = "\n".join([f"• {names[i]} (арт: {articles[i]})" for i in range(len(names))])
    else:
        detailed = "\n".join([f"• {name}" for name in names])
    
    return short_name, detailed


def build_application_text(app) -> str:
    """Формирует текст заявки для отображения"""
    username_line = f"🔗 <b>Username:</b> @{app.username}\n" if app.username else ""
    product_url_line = f"🌐 <b>Ссылка:</b> {app.product_url}\n" if app.product_url else ""
    
    return (
        f"📥 <b>Новая заявка с сайта</b>\n\n"
        f"🆔 <b>ID:</b> #{app.id}\n"
        f"📌 <b>Статус:</b> {status_label(app.status)}\n"
        f"🕒 <b>Время:</b> {app.created_at}\n\n"
        f"📦 <b>Товар:</b> {app.product_name}\n"
        f"🔖 <b>Артикул:</b> {app.article or '—'}\n"
        f"{product_url_line}"
        f"👤 <b>Имя:</b> {app.name}\n"
        f"📞 <b>Телефон:</b> {app.phone}\n"
        f"{username_line}"
        f"💬 <b>Комментарий:</b> {app.comment or '—'}"
    )


def build_take_keyboard(app_id: int) -> dict:
    return {
        "inline_keyboard": [
            [{"text": "✋ Взять заявку", "callback_data": f"take:{app_id}"}]
        ]
    }


def build_action_keyboard(app_id: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Закрыть", "callback_data": f"appstatus:done:{app_id}"},
                {"text": "❌ Отклонить", "callback_data": f"appstatus:rejected:{app_id}"},
            ]
        ]
    }


# ==========================================
# 📤 ОТПРАВКА В BITRIX24 (обновлено для корзины)
# ==========================================

async def send_to_bitrix(data: dict) -> None:
    """Отправляет заявку в Битрикс24 (создает Лид)"""
    if not BITRIX_WEBHOOK_URL:
        print("⚠️ Bitrix webhook URL не настроен")
        return

    webhook_base = BITRIX_WEBHOOK_URL.rstrip('/')
    url = f"{webhook_base}/crm.lead.add"
    
    # 🔹 Форматируем товары (поддержка корзины)
    product_display, product_detailed = format_products_for_display(data.get('products_list'))
    
    comments = (
        f"📦 Товары ({data.get('items_count', 1)} шт.):\n{product_detailed}\n\n"
        f"👤 Клиент: {data.get('name')}\n"
        f"📞 Телефон: {data.get('phone')}\n"
        f"🔗 Telegram: @{data.get('username') if data.get('username') else 'Не указан'}\n"
        f"💬 Комментарий: {data.get('comment') or '—'}\n"
        f"🆔 ID заявки: #{data.get('id', 'N/A')}\n"
        f"🌐 Ссылка: {data.get('product_url') or '—'}"
    ).strip()
    
    payload = {
        "fields": {
            "TITLE": f"Заявка с сайта: {product_display}",
            "NAME": data.get('name') or 'Не указано',
            "PHONE": [{"VALUE": data.get('phone') or '', "VALUE_TYPE": "WORK"}],
            "COMMENTS": comments,
            "SOURCE_ID": "WEB",
            "SOURCE_DESCRIPTION": "Сайт STEM Academia",
            "OPENED": "Y"
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("result"):
                    print(f"✅ Битрикс24: Лид #{result['result']} создан")
                else:
                    print(f"❌ Битрикс24 ошибка: {result}")
            else:
                print(f"❌ Битрикс24 HTTP {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"❌ Ошибка отправки в Битрикс24: {type(e).__name__}: {e}")


# ==========================================
# 📤 ОТПРАВКА В TELEGRAM (обновлено для корзины)
# ==========================================

async def send_to_telegram(data: dict, app_id: int) -> None:
    """Отправляет уведомление в Telegram группу"""
    if not BOT_TOKEN or not GROUP_CHAT_ID:
        print("⚠️ Telegram токен или chat_id не настроены")
        return

    username_line = f"🔗 <b>Username:</b> @{data.get('username')}\n" if data.get('username') else ""
    
    # 🔹 Форматируем товары
    product_display, product_detailed = format_products_for_display(data.get('products_list'))
    
    text = (
        f"📥 <b>Новая заявка с сайта</b>\n\n"
        f"🆔 <b>ID:</b> #{app_id}\n"
        f"📌 <b>Статус:</b> 🟡 Новая\n"
        f"🕒 <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"📦 <b>Товары ({data.get('items_count', 1)} шт.):</b>\n{product_detailed}\n\n"
        f"👤 <b>Имя:</b> {data.get('name')}\n"
        f"📞 <b>Телефон:</b> {data.get('phone')}\n"
        f"{username_line}"
        f"💬 <b>Комментарий:</b> {data.get('comment') or '—'}"
    )

    keyboard = build_take_keyboard(app_id)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": GROUP_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
            print(f"📩 Telegram: Заявка #{app_id} отправлена")
            
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {type(e).__name__}: {e}")


# ==========================================
# 🎯 ЭНДПОИНТЫ
# ==========================================

@router.post("/")
async def create_application(
    data: ApplicationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Создаёт новую заявку и отправляет уведомления"""
    
    # ✅ Нормализация телефона
    try:
        normalized_phone = normalize_phone(data.phone)
    except HTTPException as e:
        raise e

    # 🔹 Определяем, один товар или корзина
    is_cart = bool(data.products)
    
    if is_cart:
        # 🛒 Корзина: несколько товаров
        product_display, product_detailed = format_products_for_display(
            [p.model_dump() for p in data.products]
        )
        # Берем первую ссылку из корзины или пустую строку
        first_url = next((p.url for p in data.products if p.url), None)
        
        db_app = models.Application(
            name=data.name.strip(),
            phone=normalized_phone,
            username=data.username,
            comment=data.comment.strip() if data.comment else None,
            product_name=product_display,  # Краткое название для БД
            article=", ".join([p.article for p in data.products if p.article]) or None,
            product_url=first_url,
            status="new",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    else:
        # 📦 Один товар (обратная совместимость)
        db_app = models.Application(
            name=data.name.strip(),
            phone=normalized_phone,
            username=data.username,
            comment=data.comment.strip() if data.comment else None,
            product_name=data.product_name.strip(),
            article=data.article.strip() if data.article else None,
            product_url=data.product_url.strip() if data.product_url else None,
            status="new",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    
    db.add(db_app)
    db.commit()
    db.refresh(db_app)

    # ✅ Готовим данные для отправки во внешние сервисы
    app_data = {
        "id": db_app.id,
        "name": db_app.name,
        "phone": db_app.phone,
        "username": db_app.username,
        "comment": db_app.comment,
        "product_name": db_app.product_name,
        "article": db_app.article,
        "product_url": db_app.product_url,
        "status": db_app.status,
        # 🔹 Для корзины передаем список товаров
        "products_list": [p.model_dump() for p in data.products] if is_cart else None,
        "items_count": len(data.products) if is_cart else 1,
    }

    # ✅ Отправляем в Битрикс24 и Telegram (параллельно, в фоне)
    background_tasks.add_task(send_to_bitrix, app_data)
    background_tasks.add_task(send_to_telegram, app_data, db_app.id)

    return {
        "status": "ok", 
        "id": db_app.id, 
        "normalized_phone": normalized_phone,
        "items_count": app_data["items_count"]
    }


@router.post("/{app_id}/take")
def take_application(
    app_id: int, 
    data: TakeApplication, 
    db: Session = Depends(get_db)
):
    """Позволяет менеджеру взять заявку в работу"""
    app = db.query(models.Application).filter(
        models.Application.id == app_id
    ).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    if app.status != "new":
        raise HTTPException(
            status_code=400, 
            detail=f"Заявка уже в статусе: {status_label(app.status)}"
        )

    app.status = "in_progress"
    app.manager_id = data.manager_id
    app.manager_name = data.manager_name
    app.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    db.commit()
    db.refresh(app)
    
    return app


@router.get("/free")
def get_free_applications(db: Session = Depends(get_db)):
    """Возвращает все свободные заявки (статус: new)"""
    return db.query(models.Application).filter(
        models.Application.status == "new"
    ).order_by(
        models.Application.id.asc()
    ).all()


@router.get("/manager/{manager_id}")
def get_manager_applications(manager_id: int, db: Session = Depends(get_db)):
    """Возвращает все заявки конкретного менеджера"""
    return db.query(models.Application).filter(
        models.Application.manager_id == manager_id
    ).all()


@router.get("/")
def get_applications(db: Session = Depends(get_db)):
    """Возвращает все заявки"""
    return db.query(models.Application).all()


@router.patch("/{app_id}/status")
def update_status(
    app_id: int, 
    status: str, 
    db: Session = Depends(get_db)
):
    """Обновляет статус заявки"""
    allowed = {"new", "in_progress", "done", "rejected"}
    
    if status not in allowed:
        raise HTTPException(
            status_code=400, 
            detail=f"Недопустимый статус. Разрешены: {', '.join(allowed)}"
        )

    app = db.query(models.Application).filter(
        models.Application.id == app_id
    ).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    app.status = status
    app.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    db.commit()
    db.refresh(app)
    
    return {
        "status": "updated", 
        "application_id": app.id, 
        "new_status": app.status
    }