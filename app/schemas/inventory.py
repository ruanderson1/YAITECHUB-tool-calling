from pydantic import BaseModel, ConfigDict, Field


class ConsultarEstoqueInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(strict=True, min_length=1, description="Nome do produto")


class BaixarEstoqueInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(strict=True, min_length=1, description="Nome do produto")
    quantity: int = Field(
        strict=True,
        gt=0,
        description="Quantidade a retirar do estoque",
    )
