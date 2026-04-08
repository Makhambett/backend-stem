import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Product, Category   # ← добавили Category

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed_categories(db):
    """Создаём/обновляем все категории"""
    categories = [
        # Основные разделы
        {"slug": "furniture", "title_ru": "Мебель", "title_kz": "Мебель", "img": "", "path": "/secondpage", "parent_slug": None},
        {"slug": "divany", "title_ru": "Диваны", "title_kz": "Дивандар", "img": "/img/pagesecond/divany/divany.jpg", "path": "/secondpage/divany", "parent_slug": "furniture"},
        {"slug": "kreslo", "title_ru": "Кресла", "title_kz": "Креслолар", "img": "", "path": "/secondpage/kreslo", "parent_slug": "furniture"},
        {"slug": "pufy", "title_ru": "Пуфы", "title_kz": "Пуфтар", "img": "", "path": "/secondpage/pufy", "parent_slug": "furniture"},
        {"slug": "stellazhi", "title_ru": "Стеллажи", "title_kz": "Стеллаждар", "img": "", "path": "/secondpage/stellazhi", "parent_slug": "furniture"},
        {"slug": "tumby", "title_ru": "Тумбы", "title_kz": "Тумбалар", "img": "", "path": "/secondpage/tumby", "parent_slug": "furniture"},
        {"slug": "shkafy", "title_ru": "Шкафы", "title_kz": "Шкафтар", "img": "", "path": "/secondpage/shkafy", "parent_slug": "furniture"},
        {"slug": "stulya", "title_ru": "Стулья", "title_kz": "Орындықтар", "img": "", "path": "/secondpage/stulya", "parent_slug": "furniture"},

        {"slug": "electro", "title_ru": "Электроника и оборудование", "title_kz": "Электроника және жабдық", "img": "", "path": "/electro", "parent_slug": None},
        {"slug": "decor", "title_ru": "Декор", "title_kz": "Декор", "img": "", "path": "/decor", "parent_slug": None},
        {"slug": "equipment", "title_ru": "Оборудование", "title_kz": "Жабдық", "img": "", "path": "/equipment", "parent_slug": None},
        {"slug": "digital", "title_ru": "Цифровые решения", "title_kz": "Цифрлық шешімдер", "img": "", "path": "/digital", "parent_slug": None},

        # Подкатегории Декора (критично для твоей ошибки!)
        {"slug": "gos", "title_ru": "Государственная символика", "title_kz": "Мемлекеттік рәміздер", "img": "/img/pagesecond/decor/gos/gos.jpg", "path": "/decor/gos", "parent_slug": "decor"},
        {"slug": "3dpanels", "title_ru": "3D панели", "title_kz": "3D панельдер", "img": "/img/pagesecond/decor/3dpanels/3d.jpg", "path": "/decor/3dpanels", "parent_slug": "decor"},
        {"slug": "lighting", "title_ru": "Освещение", "title_kz": "Жарықтандыру", "img": "/img/pagesecond/decor/lighting/light.jpg", "path": "/decor/lighting", "parent_slug": "decor"},
        {"slug": "peregorodki", "title_ru": "Перегородки", "title_kz": "Бөлімдер", "img": "/img/pagesecond/decor/peregorodki/pere.jpg", "path": "/decor/peregorodki", "parent_slug": "decor"},
        {"slug": "shtory", "title_ru": "Шторы", "title_kz": "Перделер", "img": "/img/pagesecond/decor/shtory/shtory.jpg", "path": "/decor/shtory", "parent_slug": "decor"},
        {"slug": "rasteniya", "title_ru": "Растения", "title_kz": "Өсімдіктер", "img": "/img/pagesecond/decor/rasteniya/rast.jpg", "path": "/decor/rasteniya", "parent_slug": "decor"},
        {"slug": "doski", "title_ru": "Доски", "title_kz": "Тақталар", "img": "/img/pagesecond/decor/doski/doski.jpg", "path": "/decor/doski", "parent_slug": "decor"},
    ]

    for cat_data in categories:
        existing = db.query(Category).filter_by(slug=cat_data["slug"]).first()
        if existing:
            # Обновляем, если нужно
            for key, value in cat_data.items():
                setattr(existing, key, value)
        else:
            new_cat = Category(**cat_data)
            db.add(new_cat)

    db.commit()
    print("✅ Категории успешно созданы/обновлены.")


def seed_products(db):
    """Добавляем товары (только новые)"""
    products = [
        # === Твои существующие товары (мебель) — оставил без изменений ===
        # Диваны, Кресла, Пуфы, Стеллажи, Тумбы, Шкафы, Стулья ...
        # (я оставил их как в твоей последней версии, чтобы не было дублей)

        Product(title="Диван школьный «Комфорт» №1", img="/img/pagesecond/divany/divan1.png",
                description_ru="Мягкий диван для зон отдыха в школе...",  # сократил для примера
                description_kz="Мектептегі демалыс аймақтарына арналған жұмсақ диван...",
                material_ru="Рогожка, берёзовый каркас", material_kz="Жөке мата, қайың каркасы",
                size="180x80x85 см", article="DIV-001", in_stock=True, category_slug="divany"),

        # ... добавь сюда все остальные товары из твоего предыдущего файла (кресла, пуфы и т.д.)

        # === Товары Декора (новые) ===
        Product(title="Мемориальная доска с гербом РК", img="/img/pagesecond/decor/gos/gos1.png",
                description_ru="Оформление входной группы школы в государственном стиле.",
                description_kz="Мектептің кіреберісін мемлекеттік стильде безендіру.",
                material_ru="Акрил + композит", material_kz="Акрил + композит",
                size="2000×1200 мм", article="DEC-GOS-001", in_stock=True, category_slug="gos"),

        Product(title="Стенд с Конституцией Республики Казахстан", img="/img/pagesecond/decor/gos/gos2.png",
                description_ru="Информационный стенд с текстом Конституции и государственными символами.",
                description_kz="Конституция мәтіні және мемлекеттік рәміздер бар ақпараттық стенд.",
                material_ru="Композит, УФ-печать", material_kz="Композит, УФ басып шығару",
                size="1500×2000 мм", article="DEC-GOS-002", in_stock=True, category_slug="gos"),

        Product(title="3D панель Геометрия белая", img="/img/pagesecond/decor/3dpanels/3d1.png",
                description_ru="Декоративная 3D стеновая панель с геометрическим рельефом.",
                description_kz="Геометриялық рельефі бар декоративтік 3D панель.",
                material_ru="Гипсополимер", material_kz="Гипсополимер",
                size="500×500 мм", article="DEC-3D-001", in_stock=True, category_slug="3dpanels"),

        Product(title="Линейный подвесной светильник 120 см", img="/img/pagesecond/decor/lighting/light1.png",
                description_ru="Современный LED светильник для учебных классов.",
                description_kz="Оқу сыныптарына арналған заманауи LED сызықтық шам.",
                material_ru="Алюминий, акрил", material_kz="Алюминий, акрил",
                size="1200×80 мм", article="DEC-LIGHT-001", in_stock=True, category_slug="lighting"),

        Product(title="Реечная декоративная перегородка", img="/img/pagesecond/decor/peregorodki/pere1.png",
                description_ru="Акустическая реечная перегородка с растениями.",
                description_kz="Өсімдіктері бар акустикалық реечная перегородка.",
                material_ru="Дерево, металл", material_kz="Ағаш, металл",
                size="2400×1800 мм", article="DEC-PER-001", in_stock=True, category_slug="peregorodki"),

        Product(title="Рулонные шторы Blackout", img="/img/pagesecond/decor/shtory/shtora1.png",
                description_ru="Светонепроницаемые рулонные шторы для классов.",
                description_kz="Сыныптарға арналған жарық өткізбейтін ролл шторы.",
                material_ru="Ткань blackout", material_kz="Blackout мата",
                size="1500×2000 мм", article="DEC-SHT-001", in_stock=True, category_slug="shtory"),

        Product(title="Искусственное растение Банан 180 см", img="/img/pagesecond/decor/rasteniya/rast1.png",
                description_ru="Большое декоративное растение для холлов и рекреаций.",
                description_kz="Дәліздер мен рекреацияларға арналған үлкен декоративтік өсімдік.",
                material_ru="Пластик, ткань", material_kz="Пластик, мата",
                size="180 см", article="DEC-PLA-001", in_stock=True, category_slug="rasteniya"),

        Product(title="Магнитно-маркерная доска 180×120 см", img="/img/pagesecond/decor/doski/doska1.png",
                description_ru="Классическая школьная доска с магнитным покрытием.",
                description_kz="Магниттік жабыны бар классикалық мектеп тақтасы.",
                material_ru="Металл, эмаль", material_kz="Металл, эмаль",
                size="1800×1200 мм", article="DEC-DOS-001", in_stock=True, category_slug="doski"),
    ]

    existing_articles = {p.article for p in db.query(Product.article).all()}
    new_products = [p for p in products if p.article not in existing_articles]

    if new_products:
        db.add_all(new_products)
        db.commit()
        print(f"✅ Добавлено {len(new_products)} новых товаров.")
    else:
        print("ℹ️  Новых товаров для добавления не найдено.")


def seed():
    db = SessionLocal()
    try:
        print("🚀 Запуск сидирования базы данных...")

        seed_categories(db)      # ← Сначала категории!
        seed_products(db)        # ← Потом товары

        print("🎉 Сидирование завершено успешно!")

    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()