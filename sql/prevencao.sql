-- Migração de prevenção. Rodar DEPOIS de case/schema.sql.
-- Antes de rodar em produção, conferir o bloco "Duplicados" abaixo.

BEGIN;

-- 1. Duplicados 
-- Liste primeiro. Se houver linhas, a operação decide qual versão vale
-- (ver pergunta O5 em docs/DIAGNOSTICO.md) e remove as outras antes de seguir.
--   SELECT evento_id, count(*) FROM pagamento GROUP BY evento_id HAVING count(*) > 1;

-- 2. Pagamento: um evento do tribunal = uma linha 
ALTER TABLE pagamento ADD CONSTRAINT pagamento_evento_unico UNIQUE (evento_id);
-- Guarda a versão do evento para saber qual é a mais nova.
ALTER TABLE pagamento ADD COLUMN atualizado_em TIMESTAMPTZ;

-- 3. Precatório: número do processo só com dígitos 
-- CHAR(20) já era o tamanho certo para 20 dígitos; faltava impedir máscara/texto.
ALTER TABLE precatorio
    ADD CONSTRAINT precatorio_processo_20_digitos CHECK (numero_processo ~ '^[0-9]{20}$');

-- 4. Precatório: data de apresentação e prazo calculado pelo banco
-- apresentado_em é a data em horário de Brasília.
ALTER TABLE precatorio ADD COLUMN apresentado_em DATE;
ALTER TABLE precatorio ADD COLUMN prazo_pagamento DATE GENERATED ALWAYS AS (
    make_date(
        EXTRACT(YEAR FROM apresentado_em)::int
        + CASE WHEN apresentado_em <= make_date(EXTRACT(YEAR FROM apresentado_em)::int, 4, 2)
               THEN 1 ELSE 2 END,
        12, 31)
) STORED;

-- 5. Total pago calculado, nunca somado manualmente.
-- Estorno entra negativo. (Reimportar um arquivo não muda o resultado)
CREATE VIEW precatorio_total_pago AS
SELECT p.id,
       p.numero_processo,
       p.valor_face,
       COALESCE(SUM(CASE g.tipo WHEN 'pagamento' THEN g.valor ELSE -g.valor END), 0) AS total_pago
FROM precatorio p
LEFT JOIN pagamento g ON g.precatorio_id = p.id
GROUP BY p.id;

-- 6. Nada de ignorar em silêncio: evento recusado fica guardado
CREATE TABLE importacao_rejeitada (
    id          BIGSERIAL PRIMARY KEY,
    arquivo     TEXT        NOT NULL,
    registro    JSONB       NOT NULL,  -- o evento exatamente como chegou
    motivo      TEXT        NOT NULL,
    recebido_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolvido   BOOLEAN     NOT NULL DEFAULT false
);

COMMIT;
