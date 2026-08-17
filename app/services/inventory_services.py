"""Regras de negócio do controle de estoque."""

from app.db.models import Product
from app.repositories.inventory_repository import InventoryRepository


class InventoryService:
    """Coordena consultas e baixas, protegendo as invariantes do estoque."""

    def __init__(self, repository: InventoryRepository) -> None:
        """Recebe o repositório usado para ler e persistir produtos."""
        self.repository = repository

    def get_by_name(self, name: str) -> Product:
        """Retorna um produto existente.

        Raises:
            ValueError: Se não houver produto com o nome informado.
        """
        product = self.repository.get_by_name(name)
        if product is None:
            raise ValueError(f"Produto não encontrado: {name}")
        return product

    def decrease_quantity(self, name: str, quantity: int) -> Product:
        """Retira unidades sem permitir que o estoque fique negativo.

        A validação estrutural de ``quantity > 0`` pertence ao schema da
        ferramenta. Aqui é aplicada a regra que depende do estado atual.

        Raises:
            ValueError: Se o produto não existir ou o estoque for insuficiente.
        """
        product = self.get_by_name(name)
        if product.quantity < quantity:
            raise ValueError(
                f"Estoque insuficiente para {name}: disponível {product.quantity}"
            )

        updated_product = self.repository.decrease_quantity(name, quantity)
        if updated_product is None:
            raise ValueError(f"Produto não encontrado: {name}")
        return updated_product
