from app.db.models import Product
from app.repositories.inventory_repository import InventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    def get_by_name(self, name: str) -> Product:
        product = self.repository.get_by_name(name)
        if product is None:
            raise ValueError(f"Produto não encontrado: {name}")
        return product

    def decrease_quantity(self, name: str, quantity: int) -> Product:
        product = self.get_by_name(name)
        if product.quantity < quantity:
            raise ValueError(
                f"Estoque insuficiente para {name}: disponível {product.quantity}"
            )

        updated_product = self.repository.decrease_quantity(name, quantity)
        if updated_product is None:
            raise ValueError(f"Produto não encontrado: {name}")
        return updated_product
