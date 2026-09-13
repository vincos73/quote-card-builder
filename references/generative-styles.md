# Generative styles — editor locale

La scelta visuale usa un solo livello, **Style**. Il renderer conserva le direzioni interne per riutilizzare fitting, formati e documenti esistenti.

| Nome nell'editor | Direzione interna | Motivo |
| --- | --- | --- |
| Blocks | editorial | cover |
| Cutouts | editorial | cutouts |
| Constellations | contextual | constellations |
| Gradient | editorial | gradient |

**Vary pattern** e **Previous** cambiano il seed, mantenendo testo, palette e impostazioni. Blocks conserva le due fasce al 9% e il generatore cover-v1 del test precedente. Contours ed Echo Rings sono rimossi dal selettore; i documenti precedenti restano renderizzabili come Legacy. Gli altri motivi precedenti restano renderizzabili; aprire un documento esistente non deve cambiarne la selezione.

Cutouts usa direttamente i colori primary e accent del brand in piani angolari ampi; il contrasto del testo viene controllato separatamente dai colori decorativi. Constellations usa nodi pieni di dimensioni diverse e reti indipendenti, variando geometria e collegamenti con il seed.

Gradient usa campi cromatici morbidi derivati dalla palette del brand, comprese tinte schiarite e intermedie. Il seed cambia posizione, direzione, ampiezza, diffusione e peso relativo dei campi; testo, font e palette dichiarata rimangono invariati. Non aggiunge controlli al pannello.

Il controllo Gradient legge gli stop SVG e calcola un limite conservativo sul contrasto di tutte le loro miscele, incluse le sovrapposizioni trasparenti. Verifica gli inchiostri effettivi del testo e dell’attribuzione; il contorno conserva la soglia più severa. Lo stesso controllo alimenta QA e punteggio del browser. Il logo deve avere colori SVG pieni verificabili: loghi raster o SVG con effetti/CSS non verificabili vengono segnalati e bloccano la produzione Gradient, anziché ricevere un esito positivo presunto.

**Save style** conserva una combinazione nominata di brand, famiglia visuale, seed, visibilità del logo e impostazioni di composizione. **My styles** la applica alla citazione corrente. Citazione, attribuzione, fonte, a capo, alt text e intervalli di formattazione legati al contenuto non appartengono allo stile salvato.

Gli stili sono persistiti in `~/.quote-card-builder/styles.json` (override `QUOTE_CARD_STYLE_STORE` o `--style-store`). Salvare con lo stesso nome aggiorna lo stile. Applicare uno stile aggiorna atomicamente il manifest locale e la sua revisione, preservando anche le modifiche correnti al testo; la produzione richiede il consueto comando Genera.

I profili di brand e gli stili salvati sono archivi separati: il primo descrive l'identità, il secondo aggiunge le scelte della card. Uno stile conserva i riferimenti agli asset locali, non incorpora i file dei font o dei loghi. Se un asset non è più disponibile, l'applicazione dello stile deve segnalarlo.

## Palette modificabile

Il pannello **Palette della card** offre palette pronte, modifica dei quattro colori e ripristino iniziale per tutte le famiglie. Il draft trasmette `palette` con `primary`, `accent`, `background` e `text`; il server valida i valori esadecimali e li applica a `brand.colors`. Gli altri campi della card rimangono invariati. Anteprima e produzione usano la stessa palette effettiva e mantengono i controlli di contrasto, incluso quello conservativo Gradient e dei loghi.

`palette_initial` conserva i colori originali della sessione e costituisce il riferimento stabile di **Ripristina iniziali**. Applicare uno stile, salvare un profilo o produrre la card non sostituisce questo riferimento. Il ripristino cambia i soli colori; non annulla eventuali altre modifiche alla card. Una nuova sessione creata da un altro manifest prende come riferimento i colori di quel manifest, salvo un riferimento originale già persistito.

La bozza nel browser conserva anche la palette alla riapertura; la palette approvata viene persistita nel manifest con gli altri cambiamenti. **Save style** salva la palette corrente e **Apply** la riapplica; **Salva profilo / Aggiorna** legge il brand effettivo della bozza. Le sperimentazioni non scrivono nell'archivio dei profili.

La sessione di verifica usa `work/generative-styles-test/` e un archivio di stili isolato. Questa implementazione riguarda l'editor locale; rilascio, installazione e interfaccia MCP distribuita rimangono operazioni separate.

La prova Gradient di questa worktree usa `output/gradient-proof/` per i raster e `output/gradient-editor/` per una sessione con archivi separati. Il checkout sorgente e la sua sessione non vengono modificati.
