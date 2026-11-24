# Diagnóstico, prevenção e dúvidas

Fatos reproduzíveis com `python scripts/inspecionar_dados.py`. O script de importação atual
**não foi entregue**: "o script soma tudo" é o que o enunciado descreve (passo 2). É uma premissa (pergunta O1).
**Causa** = origina outros problemas. **Consequência** = nasce de outro.

## 1. Diagnóstico (do mais grave ao menos grave)

| # | Problema | Evidência | Impacto | Tipo |
| 1 | Soma sem controle de repetição | `pagamentos.json`: `ev-002` repetido (itens 2 e 4); `ev-001` com 15.000 (item 1) e 15.500 (item 9, mais novo). `schema.sql`: `evento_id` sem `UNIQUE`. Reexecutar o arquivo é parte do fluxo (passo 2) e o arquivo cobre 10/03 a 10/08, não 7 dias | `0012345-10.2019.8.26.0053`: 15.000 + 2.500,50 + 2.500,50 + 15.500 = **35.500,00**; o certo é **18.000,50**. Cada reexecução soma de novo | Causa |
| 2 | Estorno somado como pagamento | `ev-006` (+5.000) e `ev-007` (`estorno`, 5.000) em `0034567-32.2018.8.26.0405`; a documentação diz `tipo` "sempre pagamento" | Total **10.000,00** em vez de **0,00** (parece 80% pago sem ter pago nada) | Consequência do 10 |
| 3 | Falhas ignoradas em silêncio | Passo 5. Não entram: `ev-004` (valor `null`), `ev-009` (-200, barrado pelo `CHECK`), `ev-010` (sem processo, R$ 750), `ev-011` (R$ 4.000; `0067890...0053` não está no hub) | O dinheiro some do total sem aviso; ninguém sabe onde está a diferença | Causa |
| 4 | Prazo errado no hub | Regra: até 2/abr → 31/12 do ano seguinte. `0012345`: apresentado 2025-04-02, hub 2027, certo **2026**. `0056789`: `2025-04-03T01:00:00Z` é 02/04 em Brasília; hub 2027, certo **2026**. `0045678` acerta só se o fuso for Brasília | 2 de 5 prazos com um ano a mais: carteira priorizada errado, risco de atraso | Consequência (datas sem padrão em `apresentacoes.json`) |
| 5 | Processo sem forma única | `hub.csv` linha 3 e `ev-005` sem máscara; demais com máscara. `CHAR(20)` não comporta os 25 caracteres da máscara | Busca exata não junta o mesmo processo; `ev-005` (R$ 1.200) não acha o precatório. Excel ainda remove zeros à esquerda | Causa |
| 6 | `tribunal.csv` não segue a documentação | Documentação v2.1: UTF-8, `,`, ponto decimal. Real: Windows-1252 (byte `0xED`), `;`, CRLF, `45.000,00`. `pagamentos.json` tem `"2.500,50"` e `"10/04/2025"` (dia/mês, confirmado pelo `atualizado_em`) | Lido como documentado: uma coluna só, acentos quebrados, valor não vira número | Consequência do 10 |
| 7 | Hub e tribunal divergem | `0023456`: face 30.000 × 31.000. `0045678`: "União" × "Município de Santos". `0056789` só no hub; `0067890` só no tribunal (com R$ 4.000 pagos) | Saldo e devedor possivelmente errados; o sistema não deve escolher sozinho | Consequência do 8 |
| 8 | Conferência manual no Excel, texto exato | Passo 3. `MUNICIPIO DE SAO PAULO` ≠ `Município de São Paulo` na busca exata; salvar altera o original | Diferenças falsas escondem as reais; trabalho manual e semanal | Causa |
| 9 | Pagamento antes da apresentação | `ev-001` pago em 2025-03-10; precatório apresentado em 2025-04-02 | Uma das datas está errada (e o prazo pode mudar). Mantido nos totais, marcado em dúvida | Causa desconhecida |
| 10 | Documentação incompleta | Sem `apresentacoes.json` e `hub.csv`; "tipo sempre pagamento"; não explica reenvio de `evento_id`; sem fuso; "7 dias" não confere | Alimenta os itens 2 e 6 | Causa |
| 11 | O banco não impede os erros | Sem `UNIQUE`, sem `atualizado_em`, sem `apresentado_em`/prazo, sem tabela de rejeitados; o processo fala em "total pago" mas o schema não tem essa coluna | Cada erro acima entra sem barreira | Causa |

| Processo | Soma simples (premissa) | Total limpo |
| `0012345-10.2019.8.26.0053` | 35.500,00 | 18.000,50 |
| `0034567-32.2018.8.26.0405` | 10.000,00 | 0,00 |

Resultado completo em `saida/relatorio.md`. Os dígitos verificadores do CNJ não foram usados como regra:
nenhum dos 6 números de exemplo passa (são fictícios). Em produção valem como validação (T11).

## 2. Prevenção

- **Processo:** guardar cada arquivo como chegou (data e hash) e nunca salvá-lo no Excel; trocar a
  conferência manual por comparação automática (este programa); alguém responde pelos itens "em dúvida";
  leiaute versionado com o tribunal e teste de contrato a cada arquivo.
- **Script:** idempotente (`evento_id` único, versão mais nova vence); uma transação por arquivo;
  nunca ignorar (recusado vai para tabela de rejeitados e gera aviso; script termina com erro);
  normalizar na entrada; total pago **calculado** (estorno negativo), não acumulado.
- **Banco:** `sql/prevencao.sql` (testado em PostgreSQL 16): `UNIQUE (evento_id)`, `atualizado_em`,
  `CHECK` de 20 dígitos, prazo calculado a partir de `apresentado_em`, view `precatorio_total_pago`,
  tabela `importacao_rejeitada` e exemplo de importação com `ON CONFLICT`.

## 3. Dúvidas antes de pôr em produção

**Tribunal**
- T1. O `tribunal.csv` é mesmo Windows-1252, `;` e vírgula decimal? A v2.1 está desatualizada?
- T2. Reenvio do mesmo `evento_id` com outro valor (`ev-001`) é correção? Vale o `atualizado_em` mais novo?
- T3. Como um estorno aponta para o pagamento original? Pode ser parcial? O `ev-009` (-200) é um estorno com tipo errado?
- T4. O que significa `ev-004` com valor `null`? Haverá novo envio?
- T5. De qual processo é o `ev-010` (R$ 750)?
- T6. No `ev-001`, qual data está errada: pagamento (10/03) ou apresentação (02/04)?
- T7. Datas com hora: qual fuso? Vale o dia em Brasília para o prazo?
- T8. Qual a versão certa: face de `0023456`, ente de `0045678`, e o que houve com `0056789`?
- T9. A lista semanal é completa ou só mudanças? Qual a janela real do `pagamentos.json`?
- T10. Quem gera `apresentacoes.json` e por que os formatos de data variam?
- T11. Os dígitos verificadores dos processos estão corretos?

**Operação**
- O1. Posso ver o script e o log? Ele soma mesmo todas as linhas? Onde fica o "total pago"?
- O2. O banco guarda o número do processo com ou sem máscara?
- O3. Quem calculou o prazo do hub e por que `02/04/2025` virou 2027?
- O4. Alguma priorização já foi feita com prazos errados (`0012345` e `0056789`)?
- O5. Há pagamentos duplicados no banco? Qual versão vale? (consulta no início do SQL)
- O6. Quem decide os itens "em dúvida" e em quanto tempo? Até lá ficam fora dos totais?
- O7. O operador salva por cima do arquivo original? Existe cópia como chegou?