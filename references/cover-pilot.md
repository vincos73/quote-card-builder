# Cover: prova locale della doppia fascia

Cover si seleziona in **Editorial → Motivo → Cover** nell'editor locale. Si aggiunge ai motivi esistenti senza creare una quarta direzione. Le due fasce occupano ciascuna il 9% dell'altezza; testo, logo e attribuzione hanno aree riservate all'interno.

**Varia motivo** passa al seed successivo; **Precedente** torna al precedente. Cambiare motivo, formato o testo non rigenera il seed. I vecchi motivi ignorano il seed e mantengono la resa precedente. Con **Nessuno** vengono nascoste entrambe le fasce.

La scelta viene salvata in `presentation.graphic_variant: "cover"` e `presentation.graphic_seed` (intero 0–999999, predefinito 0). Il numero visibile della variante è seed + 1. Preview e PNG usano lo stesso renderer. Il generatore `cover-v1` usa SHA-256 e geometria normalizzata, mantenendo lo stesso disegno nei tre formati. Non modificare questa grammatica retroattivamente: per una grammatica futura usare un nuovo identificatore di variante.

La sessione dimostrativa è in `work/cover-seed-test/review-manifest.json` e si apre con `scripts/card_review_server.py`, passando `--session-dir work/cover-seed-test/session`. I file sotto work restano locali. La prova riguarda l'editor locale: nessuna nuova UI MCP, pubblicazione, installazione o release è inclusa.

Verifiche mirate: `tests/test_cover_motif.py`, renderer, produzione, applicazione revisioni, server locale e ispezione SVG. I test Cover verificano ripetibilità, isolamento dei vecchi motivi, geometria nei tre formati, collisioni e conservazione del seed dopo approvazione/esportazione.
