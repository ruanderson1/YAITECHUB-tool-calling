from langchain_core.tools import tool

from app.db.database import SessionLocal
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import BaixarEstoqueInput, ConsultarEstoqueInput
from app.services.inventory_services import InventoryService


@tool(args_schema=ConsultarEstoqueInput)
def consultar_estoque(name: str) -> str:
    """
    Consulta a quantidade disponível de um produto pelo nome.
    Use quando o usuário perguntar se um produto está disponível ou
    quantas unidades existem. Não use para realizar baixas.
    """
    with SessionLocal() as session:
        service = InventoryService(InventoryRepository(session))
        product = service.get_by_name(name)
        return f"{product.name}: {product.quantity} unidades em estoque"


@tool(args_schema=BaixarEstoqueInput)
def baixar_estoque(name: str, quantity: int) -> str:
    """
    Retira uma quantidade do estoque de um produto.
    Use somente quando o usuário solicitar explicitamente a retirada
    ou baixa de uma quantidade. Não use apenas para consultas.
    """
    with SessionLocal() as session:
        service = InventoryService(InventoryRepository(session))
        product = service.decrease_quantity(name, quantity)
        return f"Baixa realizada. {product.name}: {product.quantity} unidades em estoque"
