[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Миграции базы данных ядра

Запускайте Alembic из `services/core`, задав `DATABASE_URL`. URL может использовать синхронный или асинхронный драйвер PostgreSQL для SQLAlchemy. Миграции выполняются только вперёд; после применения их нельзя редактировать.
