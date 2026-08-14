from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Product


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_name(self, name: str) -> Product | None:
        normalized_name = name.strip().lower()
        return self.session.scalar(
            select(Product).where(func.lower(Product.name) == normalized_name)
        )

    def decrease_quantity(self, name: str, quantity: int) -> Product | None:
        product = self.get_by_name(name)
        if product is None:
            return None

        product.quantity -= quantity
        self.session.commit()
        self.session.refresh(product)
        return product
