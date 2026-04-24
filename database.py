from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os
import logging

# ✅ Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Загружаем переменные окружения
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не настроен в переменных окружения!")

# ✅ Оптимизированные настройки пула соединений для Neon (Serverless PostgreSQL)
engine = create_engine(
    DATABASE_URL,
    # === Настройки пула соединений ===
    poolclass=QueuePool,          # ✅ Стандартный пул с очередью
    pool_size=5,                  # ✅ Количество постоянных соединений (оптимально для бесплатного тарифа)
    max_overflow=10,              # ✅ Дополнительные соединения при пиковой нагрузке
    pool_pre_ping=True,           # ✅ Проверка соединения перед использованием (защита от "broken pipe")
    pool_recycle=600,             # ✅ Пересоздавать соединения каждые 10 минут (было 300) — критично для Neon!
    
    # === Настройки подключения ===
    connect_args={
        "connect_timeout": 10,    # ✅ Таймаут подключения: 10 секунд
        "sslmode": "require",     # ✅ Принудительный SSL (требуется Neon)
        "sslrootcert": None,      # ✅ Использовать системные сертификаты
        "options": "-c timezone=Asia/Almaty"  # ✅ Таймзона Казахстана для консистентности дат
    },
    
    # === Дополнительные опции ===
    echo=False,                   # ❌ Отключить логирование SQL-запросов в продакшене (включите True для отладки)
    future=True                   # ✅ Использовать новый стиль SQLAlchemy 2.0
)

# ✅ Factory для создания сессий
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # ✅ Предотвращает ошибки при доступе к объектам после коммита
)

# ✅ Базовый класс для моделей
Base = declarative_base()


def get_db():
    """
    Генератор для получения сессии БД (FastAPI Depends).
    Автоматически закрывает соединение после использования.
    
    Yields:
        Session: Активная сессия SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"❌ Database error: {type(e).__name__}: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Инициализирует базу данных: создаёт все таблицы, если их нет.
    Вызывайте один раз при старте приложения.
    """
    logger.info("🗄️ Инициализация базы данных...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблицы созданы/проверены")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise


# ✅ Обработчик событий пула (для отладки соединений)
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, record):
    """Вызывается при каждом новом подключении к БД"""
    logger.debug("🔗 Новое соединение с БД установлено")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Вызывается при получении соединения из пула"""
    logger.debug("📦 Соединение взято из пула")


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """Вызывается при возврате соединения в пул"""
    logger.debug("🔄 Соединение возвращено в пул")