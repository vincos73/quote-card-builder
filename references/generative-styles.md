# Generative styles — editor locale

La scelta visuale usa un solo livello, **Style**. Il renderer conserva le direzioni interne per riutilizzare fitting, formati e documenti esistenti.

| Nome nell'editor | Direzione interna | Motivo |
| --- | --- | --- |
| Blocks | editorial | cover |
| Cutouts | editorial | cutouts |
| Constellations | contextual | constellations |

**Vary pattern** e **Previous** cambiano il seed, mantenendo testo, palette e impostazioni. Blocks conserva le due fasce al 9% e il generatore cover-v1 del test precedente. Contours ed Echo Rings sono rimossi dal selettore; i documenti precedenti restano renderizzabili come Legacy. Gli altri motivi precedenti restano renderizzabili; aprire un documento esistente non deve cambiarne la selezione.

Cutouts usa direttamente i colori primary e accent del brand in piani angolari ampi; il contrasto del testo viene controllato separatamente dai colori decorativi. Constellations usa nodi pieni di dimensioni diverse e reti indipendenti, variando geometria e collegamenti con il seed.

**Save style** conserva una combinazione nominata di brand, famiglia visuale, seed, visibilità del logo e impostazioni di composizione. **My styles** la applica alla citazione corrente. Citazione, attribuzione, fonte, a capo, alt text e intervalli di formattazione legati al contenuto non appartengono allo stile salvato.

Gli stili sono persistiti in `~/.quote-card-builder/styles.json` (override `QUOTE_CARD_STYLE_STORE` o `--style-store`). Salvare con lo stesso nome aggiorna lo stile. Applicare uno stile aggiorna atomicamente il manifest locale e la sua revisione, preservando anche le modifiche correnti al testo; la produzione richiede il consueto comando Genera.

I profili di brand e gli stili salvati sono archivi separati: il primo descrive l'identità, il secondo aggiunge le scelte della card. Uno stile conserva i riferimenti agli asset locali, non incorpora i file dei font o dei loghi. Se un asset non è più disponibile, l'applicazione dello stile deve segnalarlo.

La sessione di verifica usa `work/generative-styles-test/` e un archivio di stili isolato. Questa implementazione riguarda l'editor locale; rilascio, installazione e interfaccia MCP distribuita rimangono operazioni separate.
