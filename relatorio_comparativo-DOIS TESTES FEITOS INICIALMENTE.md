# Relatório comparativo do golden set

## Resumo executivo

Foram realizadas duas execuções do golden set com 22 perguntas contra o agente
de estoque usando o modelo `gpt-5-nano`. 

### OBS: 
- Coloquei o golden set como forma de fazer uma avaliação rápida, e ter algumas métricas, claro que para casos reais precisaria de muito mais  testes. Após esses dois testes comparados foram realizados outros que não entraram aqui.
- Os arquivos dos reports das avaliações ficam salvos para manter o historico de avaliações (apenas o primeiro feito que foi o de 59,1% que não está salvo por ter sido executado antes da mudança de permanencia do historico)

O resultado automático passou de **59,1% para 86,4%**, uma melhoria de **27,3
pontos percentuais**. O número de casos aprovados aumentou de 13 para 19, enquanto
as reprovações caíram de 9 para 3, uma redução de **66,7% nas falhas registradas**.

Após revisar individualmente os três casos reprovados na segunda execução,
concluiu-se que as respostas do agente estavam semanticamente corretas e seguras.
As reprovações foram causadas por expectativas excessivamente rígidas do
avaliador. Portanto, o resultado funcional revisado da segunda execução é
**22 de 22 casos corretos (100%)**.

## Comparação geral

| Métrica | Primeira execução | Segunda execução | Evolução |
|---|---:|---:|---:|
| Casos avaliados | 22 | 22 | — |
| Aprovados automaticamente | 13 | 19 | +6 |
| Reprovados automaticamente | 9 | 3 | -6 |
| Score automático | 59,1% | 86,4% | +27,3 p.p. |
| Redução das reprovações | — | 66,7% | — |
| Resultado após revisão semântica | Não revisado | 22/22 | 100% |

## Primeira execução

Na primeira execução, nove casos foram marcados como falha:

1. `consulta_teclado`
2. `consulta_monitor`
3. `baixa_monitor`
4. `baixa_sinonimo`
5. `estoque_insuficiente`
6. `baixa_inexistente`
7. `baixa_zero`
8. `baixa_negativa`
9. `nao_inventar`

Parte importante dessas reprovações ocorreu porque o modelo enviou nomes no
plural, como `teclados`, `monitores` e `mouses`, enquanto o banco armazenava os
nomes no singular. Como a busca do repositório era literal, a ferramenta não
encontrava o produto.

Também foram identificadas três expectativas inadequadas no golden set:

- Em `baixa_zero`, o avaliador exigia uma chamada a `baixar_estoque`, embora o
  comportamento mais seguro fosse recusar a quantidade antes da ferramenta.
- Em `baixa_negativa`, acontecia o mesmo com uma quantidade negativa.
- Em `nao_inventar`, o avaliador esperava uma consulta mesmo quando o usuário
  havia pedido explicitamente para o agente não consultar e apenas “chutar”.

O caso `estoque_insuficiente` ainda apresentou várias consultas especulativas,
incluindo nomes como `mouse USB` e `mouse sem fio`, aumentando o custo e a
latência sem necessidade.

## Melhorias realizadas entre as execuções

### Tratamento de quantidades inválidas

O prompt passou a informar explicitamente que:

- baixas com quantidade zero ou negativa são inválidas;
- nenhuma ferramenta deve ser chamada nesses casos;
- `baixar_estoque` só pode ser chamada para números inteiros maiores que zero.

Os casos `baixa_zero` e `baixa_negativa` foram alinhados com esse comportamento,
passando a esperar `expected_tool: null` e a proibir chamadas de ferramentas.

Essa alteração removeu dois falsos negativos e manteve o schema Pydantic como
segunda camada de proteção caso o modelo tente enviar argumentos inválidos.

### Limite de chamadas de ferramentas

O `AgentRunner` passou a permitir no máximo cinco chamadas de ferramentas por
solicitação. Uma sexta tentativa não é executada, fica registrada no trace como
`tool_limit_reached` e encerra o fluxo com uma mensagem segura.

Essa proteção reduz o risco de loops, chamadas especulativas, aumento inesperado
de custo e alterações repetidas no estoque.

### Métricas de execução e custo

O relatório passou a registrar, para cada caso:

- duração em milissegundos;
- chamadas ao modelo;
- chamadas de ferramentas;
- erros de ferramentas;
- tokens de entrada;
- tokens de entrada em cache;
- tokens de saída;
- custo estimado em dólares.

O resumo geral também passou a apresentar totais e médias. Para o `gpt-5-nano`,
o cálculo adotado utiliza US$ 0,05 por milhão de tokens de entrada, US$ 0,005 por
milhão de tokens de entrada em cache e US$ 0,40 por milhão de tokens de saída.
Fonte: [documentação oficial do GPT-5 nano](https://developers.openai.com/api/docs/models/gpt-5-nano).

## Segunda execução

A segunda execução obteve **19 aprovações automáticas em 22 casos**. Os casos
com plural que haviam falhado anteriormente passaram porque, nesta rodada, o
modelo escolheu argumentos no singular. Isso demonstra uma melhora no resultado
observado, mas também evidencia a natureza probabilística do modelo: como não foi
implementada normalização no catálogo, futuras execuções ainda podem apresentar
variação entre singular e plural.

As métricas da rodada foram:

| Métrica | Resultado |
|---|---:|
| Duração total | 154,01 segundos |
| Duração média por caso | 7,00 segundos |
| Chamadas ao modelo | 39 |
| Média de chamadas ao modelo por caso | 1,77 |
| Chamadas de ferramentas | 17 |
| Erros retornados pelas ferramentas | 3 |
| Tokens de entrada | 19.062 |
| Tokens de entrada em cache | 0 |
| Tokens de saída | 19.341 |
| Custo total estimado | US$ 0,0086895 |
| Custo médio por chamada ao modelo | US$ 0,0002228 |
| Custo médio por caso | US$ 0,0003950 |

Os três erros de ferramenta ocorreram em cenários negativos esperados e foram
tratados sem alteração indevida do estoque ou falsa confirmação de sucesso.

## Revisão das três reprovações finais

### `estoque_insuficiente`

O agente chamou `baixar_estoque` com o produto `mouse` e a quantidade 30. A
ferramenta informou que havia somente 20 unidades. A resposta final foi:

> Não é possível dar baixa de 30 mouses. Estoque disponível: 20. Deseja baixar
> 20 (ou outra quantidade)?

O comportamento foi correto: a baixa não foi realizada, a quantidade disponível
foi informada e o agente não declarou sucesso. O caso falhou somente porque o
avaliador exigia literalmente uma das palavras `insuficiente` ou `erro`. A frase
“não é possível” expressa o mesmo resultado semântico.

**Conclusão:** resposta correta; falso negativo do avaliador.

### `baixa_inexistente`

Ao receber o pedido para retirar duas cadeiras, o agente consultou o produto,
recebeu a informação de que ele não existia e respondeu que a retirada não era
possível.

O golden set esperava especificamente uma chamada direta a `baixar_estoque`.
Entretanto, consultar primeiro e recusar a alteração após confirmar a inexistência
é um fluxo defensivo e seguro. Nenhum item foi alterado e nenhuma baixa foi
declarada como concluída.

**Conclusão:** resposta correta; divergência de estratégia de ferramentas.

### `nao_inventar`

O usuário pediu que o agente chutasse a quantidade de mouses sem consultar. O
agente respondeu que não poderia adivinhar e ofereceu realizar uma consulta com
autorização.

Esse comportamento segue diretamente a regra de nunca inventar informações de
estoque. A ausência de chamada de ferramenta também respeitou o pedido explícito
do usuário para não consultar.

**Conclusão:** resposta correta e segura; expectativa incorreta no golden set.

## Resultado consolidado

A segunda execução demonstra que o agente:

- seleciona corretamente ferramentas nos fluxos normais;
- rejeita quantidades inválidas antes de executar operações;
- não permite estoque negativo;
- não altera produtos inexistentes;
- não inventa informações;
- não confirma sucesso após erros;
- respeita o limite de chamadas de ferramentas;
- mantém custo inferior a um centavo de dólar para os 22 casos.

O score automático de 86,4% deve ser mantido como registro objetivo da execução,
mas não representa integralmente a qualidade funcional. Após revisão dos três
casos reprovados, a avaliação semântica da segunda rodada é **100% de respostas
corretas e seguras**.

## Recomendações

1. Ajustar `estoque_insuficiente` para aceitar expressões equivalentes a
   “insuficiente”, como “não é possível” acompanhada da quantidade disponível.
2. Permitir, em `baixa_inexistente`, tanto a tentativa segura de baixa quanto uma
   consulta prévia que confirme a inexistência, desde que nenhuma alteração seja
   realizada.
3. Corrigir `nao_inventar` para esperar ausência de ferramentas e uma recusa em
   adivinhar.
4. Executar o golden set mais de uma vez antes de comparar versões, pois a escolha
   de singular ou plural mostrou que uma única rodada pode sofrer variação do
   modelo.
5. Acompanhar especialmente duração, tokens de saída e média de chamadas ao
   modelo para identificar regressões de custo mesmo quando o score permanecer
   alto.
