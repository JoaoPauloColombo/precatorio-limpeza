# Limpeza de dados de precatórios

Case técnico: os números de pagamento do sistema não batem com os do tribunal.
Este projeto lê os arquivos como vieram, gera uma base confiável e explica o que mudou.

- **Diagnóstico, prevenção e dúvidas:** [docs/DIAGNOSTICO.md](docs/DIAGNOSTICO.md)
- **Resultado da limpeza:** [saida/relatorio.md](saida/relatorio.md)
- **SQL de prevenção:** [sql/prevencao.sql](sql/prevencao.sql)

## Como rodar

Precisa de Python 3.10 ou mais novo. Não há dependências para instalar.

```bash
python -m limpeza                 # lê dados/ e grava em saida/
python -m limpeza <dados> <saida> # outras pastas, se quiser
python -m unittest -v             # testes
python scripts/inspecionar_dados.py  # olhada inicial nos arquivos
```

Arquivos gerados em `saida/`: `precatorios.csv`, `pagamentos.csv`, `ocorrencias.csv`, `relatorio.md`.
Os arquivos em `dados/` e `case/` nunca são alterados (há um teste que confere isso).

## Como o código está organizado

| Arquivo | Para que serve |
|---|---|
| `limpeza/normalizar.py` | Arruma um valor por vez: processo, valor, data, ente, prazo |
| `limpeza/leitura.py` | Lê CSV e JSON (detecta codificação e separador) |
| `limpeza/pipeline.py` | Junta as fontes e decide: corrigir, descartar ou deixar em dúvida |
| `limpeza/relatorio.py` | Grava os CSVs e o relatório |
| `tests/` | Testes das regras de dinheiro e de prazo |

## Regras principais

1. O tribunal é a fonte oficial de ente e valor de face; o hub só entra se o tribunal não lista o processo.
2. Processo é comparado pelos 20 dígitos, sem máscara.
3. Mesmo `evento_id`: cópia exata conta uma vez; se mudou, vale o `atualizado_em` mais novo.
4. Estorno subtrai do total pago.
5. Prazo: apresentado até 2 de abril (inclusive, horário de Brasília) → 31/12 do ano seguinte; depois → 31/12 do ano subsequente.
6. **Na dúvida, o registro não entra nos totais** e aparece no relatório para alguém decidir.

## Como importar um evento no banco (SQL)

Parte da prevenção (`sql/prevencao.sql`). Com ela, **rodar o mesmo arquivo quantas vezes quiser dá o mesmo resultado**,
e um evento só é substituído se a versão que chegou for mais nova que a gravada.

```sql
INSERT INTO pagamento (precatorio_id, evento_id, tipo, valor, pago_em, atualizado_em)
SELECT p.id, :evento_id, :tipo, :valor, :pago_em, :atualizado_em
FROM precatorio p
WHERE p.numero_processo = :processo_20_digitos
ON CONFLICT (evento_id) DO UPDATE
   SET tipo = EXCLUDED.tipo, valor = EXCLUDED.valor,
       pago_em = EXCLUDED.pago_em, atualizado_em = EXCLUDED.atualizado_em
 WHERE pagamento.atualizado_em IS NULL
    OR pagamento.atualizado_em < EXCLUDED.atualizado_em;
```

Como funciona, passo a passo:
1. O `SELECT` procura o precatório pelo número do processo (20 dígitos). Se não achar, **nenhuma linha entra**.
2. Nesse caso, grave o evento em `importacao_rejeitada` com o motivo "processo desconhecido", para ninguém perder o dado sem saber.
3. Se o `evento_id` ainda não existe, o evento é inserido.
4. Se já existe (`ON CONFLICT`), o evento só é atualizado quando o `atualizado_em` que chegou é mais novo.
5. Se for o mesmo arquivo de novo, nada muda: o `atualizado_em` é igual, então a condição do `WHERE` é falsa.

Os valores com `:` (`:evento_id`, `:valor` etc.) são parâmetros: o script de importação preenche cada um com os dados do evento.

## Uso de IA

Usei o Claude principalmente para:

- **Planejamento do projeto:** definir a ordem do trabalho (análise, solução, melhorias, documentação) e a estrutura das pastas.
- **Estudo das linguagens e bibliotecas:** entender o que usar (Python 3.10+, `csv`, `json`, `decimal`, `unittest`, PostgreSQL) e como cada parte funciona.
- **Idealização dos testes:** escolher quais regras testar, de acordo com o escopo do projeto (duplicidade, estorno, versões, prazo, originais intactos).
- **Formatação da documentação:** organizar o diagnóstico e este README para ficarem fáceis de ler.