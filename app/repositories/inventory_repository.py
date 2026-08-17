"""Operações de persistência do estoque."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Product


class InventoryRepository:
    """Acesso aos produtos persistidos em uma sessão SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        """Inicializa o repositório com a sessão da unidade de trabalho atual."""
        self.session = session

    def get_by_name(self, name: str) -> Product | None:
        """Busca um produto por nome completo, ignorando caixa e espaços externos."""
        normalized_name = name.strip().lower()
        return self.session.scalar(
            select(Product).where(func.lower(Product.name) == normalized_name)
        )

    def decrease_quantity(self, name: str, quantity: int) -> Product | None:
        """Persiste a redução de estoque e retorna o produto atualizado.

        A existência do produto e a disponibilidade da quantidade são regras da
        camada de serviço. Este método pressupõe que ambas já foram validadas.
        """
        product = self.get_by_name(name)
        if product is None:
            return None

        product.quantity -= quantity
        self.session.commit()
        self.session.refresh(product)
        return product
