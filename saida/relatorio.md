# Relatório de limpeza

- Precatórios na base: 6 (2 ok, 4 com dúvida)
- Pagamentos e estornos aceitos: 8
- Ocorrências: 8 corrigidas, 2 descartadas, 10 em dúvida

## Em dúvida (precisa de decisão humana; ver perguntas em docs/DIAGNOSTICO.md)

| Arquivo | Registro | Motivo |
|---|---|---|
| precatorios | 0023456-21.2020.8.26.0053 | valor_face diverge: tribunal=30000.00 hub=31000.00 |
| precatorios | 0045678-43.2021.5.02.0011 | ente diverge: tribunal='União' hub='Município de Santos' |
| precatorios | 0045678-43.2021.5.02.0011 | prazo depende do fuso: '2025-04-02T23:30:00-03:00' é dia 2025-04-02 em Brasília e dia 2025-04-03 em UTC; usado Brasília |
| precatorios | 0056789-54.2017.4.03.6100 | processo não consta no tribunal.csv |
| precatorios | 0056789-54.2017.4.03.6100 | prazo depende do fuso: '2025-04-03T01:00:00Z' é dia 2025-04-02 em Brasília e dia 2025-04-03 em UTC; usado Brasília |
| precatorios | 0067890-65.2016.8.26.0053 | processo não consta no hub.csv |
| pagamentos.json | evento ev-004 (item 5) | valor ausente |
| pagamentos.json | evento ev-009 (item 11) | valor -200.00 não é positivo (estorno deve vir com tipo 'estorno') |
| pagamentos.json | evento ev-010 (item 12) | processo '' não tem 20 dígitos; não dá para ligar a um precatório |
| pagamentos.json | evento ev-001 (item 9) | pago em 2025-03-10, antes da apresentação (2025-04-02); mantido nos totais, confirmar |

## Descartado (não entrou na base; havia versão melhor ou era cópia)

| Arquivo | Registro | Motivo |
|---|---|---|
| pagamentos.json | evento ev-001 (item 1) | versão antiga (valor 15000.00), substituída pelo item 9 (valor 15500.00, atualizado_em mais recente) |
| pagamentos.json | evento ev-002 (item 2) | cópia exata do item 4 |

## Corrigido (o valor foi arrumado e entrou na base)

| Arquivo | Registro | Motivo |
|---|---|---|
| tribunal.csv | arquivo | codificação lida como cp1252 (não era UTF-8); a documentação diz UTF-8, e o separador é ';' com valores no formato brasileiro (45.000,00) |
| hub.csv | linha 3 | processo '00234562120208260053' reescrito como 0023456-21.2020.8.26.0053 |
| hub.csv | 0012345-10.2019.8.26.0053 | ente 'MUNICIPIO DE SAO PAULO' padronizado como 'Município de São Paulo' (grafia do tribunal) |
| hub.csv | 0012345-10.2019.8.26.0053 | prazo_pagamento 2027-12-31 recalculado para 2026-12-31 (apresentado em 2025-04-02) |
| hub.csv | 0056789-54.2017.4.03.6100 | prazo_pagamento 2027-12-31 recalculado para 2026-12-31 (apresentado em 2025-04-02) |
| pagamentos.json | evento ev-002 (item 4) | valor '2.500,50' convertido para 2500.50 |
| pagamentos.json | evento ev-002 (item 4) | data '10/04/2025' convertida para 2025-04-10 |
| pagamentos.json | evento ev-005 (item 6) | processo '00234562120208260053' reescrito como 0023456-21.2020.8.26.0053 |

## Totais pagos (pagamentos menos estornos)

| Processo | Valor de face | Total pago | Situação |
|---|---|---|---|
| 0012345-10.2019.8.26.0053 | 45000.00 | 18000.50 | ok |
| 0023456-21.2020.8.26.0053 | 30000.00 | 9200.00 | duvida |
| 0034567-32.2018.8.26.0405 | 12500.00 | 0.00 | ok |
| 0045678-43.2021.5.02.0011 | 9800.00 | 3000.00 | duvida |
| 0056789-54.2017.4.03.6100 | 22000.00 | 0.00 | duvida |
| 0067890-65.2016.8.26.0053 | 7000.00 | 4000.00 | duvida |
