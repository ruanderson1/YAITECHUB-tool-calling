from sqlalchemy import select

from app.db.database import Base, SessionLocal, engine
from app.db.models import Product


PRODUCTS = (
    ("Teclado", 10),
    ("Mouse", 20),
    ("Monitor", 5),
)


def seed_database() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        if session.scalar(select(Product.id).limit(1)) is None:
            session.add_all(
                Product(name=name, quantity=quantity) for name, quantity in PRODUCTS
            )
            session.commit()


if __name__ == "__main__":
    seed_database()
