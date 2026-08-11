---
name: quote-card-builder
description: Trasforma frasi, testi, URL, documenti e idee in quote card. Usa questa skill per trovare o scrivere una frase forte, mostrare provenienza e possibili classificazioni, confrontare candidati, progettare la direzione visuale e produrre una quote card o il relativo post kit lasciando all'utente la responsabilità editoriale finale.
---

# Quote Card Builder

Versione: **0.6.7 — Branded Header Release**

Separare sempre provenienza osservata, dichiarazioni editoriali dell'utente e produzione visuale. La skill non inventa dati né certifica le scelte dell'utente: propone etichette e segnala incongruenze, ma l'utente può modificare e approvare testo, classificazione, prova, attribuzione e virgolette ed è il garante finale.

Non ricavare il brand dalla fonte, dalla memoria o dal profilo dell'utente. Usare soltanto un profilo fornito o approvato nel lavoro corrente; offrire un profilo neutro solo come scelta esplicita.

Gestire il lavoro con questi stati: `bozza` → `candidati_pronti` → `candidato_selezionato` → `contenuto_approvato` → `prova_visuale_pronta` → `prova_visuale_approvata` → `rendering` → `qa` → `consegnato`. Le approvazioni dell'utente fanno avanzare gli stati editoriali; i gate automatici bloccano soltanto errori strutturali, tecnici o visuali.

## Preflight

1. Determinare se la sessione può leggere la fonte e produrre un artefatto grafico con controllo tipografico affidabile.
2. Se un URL o documento non è leggibile, chiedere il testo; non ricostruire passaggi mancanti.
3. Leggere [references/integrity-model.md](references/integrity-model.md).
4. Per produrre o validare un manifest, leggere [references/quote-manifest.md](references/quote-manifest.md).
5. Per produrre una prova 4:5, leggere [references/visual-manifest.md](references/visual-manifest.md).
6. Per produrre il pacchetto finale, leggere [references/production-manifest.md](references/production-manifest.md).
7. Per aprire l'editor locale vincolato, leggere [references/visual-editor.md](references/visual-editor.md).
8. Dichiarare in una frase il risultato realistico: selezione editoriale, scheda visuale, sessione di revisione, prova SVG, prova PNG o pacchetto finale.

## Fase 1: fonte e selezione

1. Chiedere «Cosa vuoi trasformare in quote card?» solo quando l'input non è già disponibile.
2. Classificare l'input come `phrase`, `text`, `url`, `document` o `idea`.
3. Leggere l'intera fonte disponibile. Il conferimento di un URL autorizza la lettura di quell'URL, non una ricerca aggiuntiva.
4. Se l'utente ha già scelto la frase, preservarla e valutarla prima di proporre riscritture.
5. Se occorre cercare la frase, proporre 3 candidati come scelta predefinita e al massimo 5.
6. Se l'input è un'idea, marcare tutte le nuove formulazioni `AI_GENERATED`.

## Fase 2: provenienza, dichiarazioni e classifica

1. Assegnare a ogni candidato due etichette indipendenti:
   - trasformazione: `VERBATIM`, `EDITED`, `PARAPHRASE`, `AI_GENERATED`;
   - prova: `VERIFIED`, `USER_SUPPLIED`, `UNVERIFIED`, `CONFLICT`.
2. Mostrare il passaggio sorgente e un riferimento per ogni candidato non generato da zero. Se non esiste una fonte accessibile, dichiararlo.
3. Separare i ruoli di attribuzione: `speaker`, `author`, `publisher`, `none`.
4. Applicare le segnalazioni consultive di [references/integrity-model.md](references/integrity-model.md) senza escludere o riclassificare automaticamente un candidato.
5. Valutare i candidati su chiarezza autonoma, rilevanza, specificità, concisione, ritmo e potenziale visuale.
6. Raccomandare un solo candidato con una motivazione di massimo due frasi. Non usare il punteggio per attenuare un problema di fonte.
7. Mostrare un confronto compatto con testo, trasformazione, prova, attribuzione e motivazione.

## Fase 3: approvazione editoriale

1. Dopo il confronto chiedere soltanto il numero del candidato e l'attribuzione visibile, distinguendo `speaker`, `author`, `publisher` e `none`.
2. Registrare la scelta come `candidato_selezionato`; non chiedere in chat una seconda conferma di etichette e virgolette quando l'editor locale è disponibile.
3. Aprire l'editor con il candidato come base interamente modificabile nei campi editoriali.
4. Consentire all'utente di cambiare liberamente testo, attribuzione, ruolo e virgolette nell'editor; mostrare trasformazione e stato della prova come informazioni nel ledger inferiore. Se l'utente chiede di cambiare queste dichiarazioni, aggiornarle conversazionalmente senza downgrade o correzioni automatiche.
5. `Invia` salva le scelte senza approvare la prova. `Approva` può salvare le stesse scelte e richiedere l'approvazione visuale in un solo passaggio.
6. Registrare `declared_by: user` e mantenere separati i dati osservati dalla fonte dalle dichiarazioni dell'utente.
7. Quando l'editor non è disponibile, chiedere conversazionalmente le scelte necessarie e registrarle come dichiarazioni dell'utente.
8. Quando serve un artefatto strutturato, creare il manifest e validarlo con `python3 scripts/validate_quote_manifest.py <manifest.json>`; la validazione è strutturale, non una certificazione editoriale.

## Fase 4: direzione visuale e brand

Procedere dopo `candidato_selezionato`; l'editor raccoglie le dichiarazioni dell'utente e può approvare direttamente la prova se il QA tecnico passa.

1. Risolvere un profilo brand fornito, approvato nel lavoro corrente, configurato con l'utente oppure neutro scelto esplicitamente.
2. Proporre tre direzioni adattate allo stesso contenuto e allo stesso brand:
   - `editorial`: gerarchia tipografica e spazio bianco;
   - `statement`: scala forte e una sola enfasi;
   - `contextual`: citazione con metadati o segnale documentale della fonte.
3. Differenziare le direzioni per composizione, non soltanto per colore o font.
4. Preparare una proposta di a capo coerente con il significato, ma lasciare all'utente il controllo finale: ogni newline inserito nel formato attivo deve restare esattamente dove viene scritto; una riga vuota vale come riga intera di spazio verticale.
5. Quando Python, browser locale e ricezione degli eventi sono disponibili, creare un manifest 0.4 conforme a [references/visual-editor.md](references/visual-editor.md), inizialmente in `candidato_selezionato`, con composizioni autonome per `4x5`, `1x1` e `9x16`.
6. Avviare `python3 scripts/card_review_server.py <manifest.json> --session-dir <session-dir>`, aprire esclusivamente l'URL `127.0.0.1` restituito e mantenere il processo attivo.
7. Nell'editor lasciare modificabili testo, attribuzione, ruolo, direzione, a capo manuali e righe vuote per formato, formattazioni `bold`, `italic`, `underline` e `highlight` applicate a selezioni testuali, scala limitata, posizione verticale, logo, virgolette, elemento grafico come `auto` o `hidden` e output finale come `all`, `4x5`, `1x1` o `9x16`. Le tab di anteprima restano disponibili per controllare tutti i rapporti anche quando l'utente ne consegna uno solo. Associare senza ulteriori opzioni `editorial` ai contorni, `statement` ai moduli e `contextual` al campo. Applicare sempre un auto-fit per formato basato sugli stessi vincoli del quality gate: la scala è una preferenza, ma non può produrre overflow e l'interfaccia deve dichiarare quando viene limitata. Mostrare trattamento e stato della prova soltanto nel ledger inferiore. Se il profilo non contiene i file necessari, dichiarare quali trattamenti non sono disponibili o usano una resa simulata e indicare di fornire i file mancanti o approvare un font sostitutivo. Non risincronizzare il form durante la digitazione in modo da cancellare newline o input parziali. Fonte osservata, brand e dimensioni restano protetti.
8. Il server locale deve applicare immediatamente e atomicamente ogni batch già validato, aggiornare la revisione e riabilitare l'editor nella stessa richiesta. `python3 scripts/apply_card_review.py <manifest.json> <session-dir>/feedback.json --session-dir <session-dir>` resta il fallback di recupero per feedback pendenti lasciati da versioni precedenti. Rifiutare revisioni superate o invarianti violate, quindi rigenerare la preview con lo stesso renderer usato per l'export.
9. Per `action: feedback`, applicare le scelte e rigenerare la prova. Per `action: approve`, applicare nello stesso batch eventuali modifiche correnti: non richiedere un `Invia` preliminare.
10. Dopo `action: approve`, ispezionare la prova aggiornata, eseguire il controllo qualità tecnico e soltanto dopo registrare `prova_visuale_approvata` nel production manifest.
11. Se l'editor locale non è disponibile, creare un visual manifest 0.2 conforme a [references/visual-manifest.md](references/visual-manifest.md) e generare le tre prove SVG con `python3 scripts/render_quote_card.py <manifest.json> --output-dir <cartella> --all-directions --png never`.
12. Quando la sessione espone Node.js e `sharp` già configurati, usare esclusivamente l'helper incluso `scripts/svg_to_png.cjs` passando al renderer `--png required --node <node> --node-modules <node_modules>`. Non installare dipendenze. Se il convertitore non è disponibile, consegnare SVG e dichiarare che il PNG non è stato prodotto.
13. Leggere il report `*-qa.json` e ispezionare visivamente tutte le prove renderizzate. Correggere logo, overflow, collisioni, contrasto, gerarchia e leggibilità prima di mostrarle.
14. Mostrare le prove con quote, attribuzione, layout, direzione visuale, formato e dichiarazioni editoriali. Impostare lo stato `prova_visuale_pronta`.
15. Chiedere `Approva la prova visuale`, `Cambia direzione` oppure `Torna al testo`. Fermarsi e attendere.

## Fase 5: generazione e controllo qualità

Procedere soltanto dopo `prova_visuale_approvata`.

1. Registrare l'approvazione in un production manifest 0.3 conforme a [references/production-manifest.md](references/production-manifest.md). Conservare direzione, prova, hash del testo, autore e data dell'approvazione.
2. Includere nel production manifest tutti i rapporti soltanto con `presentation.output_mode: all`; altrimenti includere esclusivamente il formato `4x5`, `1x1` o `9x16` scelto. Definire a capo autonomi per i formati richiesti e verificare che ognuno ricostruisca esattamente il testo approvato; non ritagliare o ridimensionare un altro output.
3. Produrre PNG come consegna predefinita. Quando Node.js e `sharp` sono già disponibili, eseguire `scripts/render_quote_card_pack.py <manifest.json> --output-dir <cartella> --png required --svg auto --node <node> --node-modules <node_modules>`: l'SVG è un intermedio tecnico e viene eliminato dopo la conversione riuscita. Non installare dipendenze.
4. Se la conversione PNG non è disponibile, conservare l'SVG come fallback dichiarato. Quando Python espone Pillow, usarlo per il fitting sulle metriche reali; in sua assenza accettare il fallback dichiarato `deterministic_heuristic`.
5. Mostrare fedeltà, etichette, attribuzione, virgolette, numeri, negazioni e cautele come riepilogo consultivo; non sovrascrivere le dichiarazioni approvate dall'utente.
6. Controllare leggibilità alla dimensione tipica del feed, contrasto, gerarchia, a capo, margini di sicurezza, sforamenti, font e risorse in ogni rapporto.
7. Non modificare il testo approvato durante il fitting. Limitare automaticamente la scala quando serve a evitare overflow; tornare all'approvazione editoriale soltanto se la dimensione risultante non è leggibile.
8. Leggere il report `*-production-qa.json` e verificare dimensioni, rapporti, metodo di fitting, contrasto e hash. Lo stato deve restare `qa` durante l'ispezione.
9. Ispezionare visivamente tutti i PNG richiesti in un solo passaggio comparativo; ispezionare gli SVG soltanto quando sono il fallback effettivamente consegnato. Correggere eventuali problemi, rigenerare e confermare al massimo una seconda volta.
10. Soltanto dopo l'ispezione, eseguire `scripts/finalize_quote_card_pack.py <qa.json> --all-formats --reviewer <nome>`. Mostrare gli artefatti finali solo quando il report è `passed` e lo stato è `consegnato`.
11. Su richiesta aggiungere caption, alt text e scheda di provenienza.

## Regole permanenti

- Scrivere nella lingua dell'utente.
- Non inventare fonte, autore, speaker, logo, firma, URL, colori o tagline.
- Non promuovere autonomamente `USER_SUPPLIED` a `VERIFIED`; se l'utente sceglie `VERIFIED`, registrarlo come sua dichiarazione.
- Non alterare autonomamente negazioni, condizioni, cautele, numeri o grado di certezza.
- Segnalare combinazioni potenzialmente ambigue senza correggerle, riclassificarle o bloccarle.
- Conservare separate identità del brand e attribuzione della frase.
- Registrare sempre la responsabilità editoriale dell'utente; `Approva` può includere le modifiche correnti senza un passaggio preliminare su `Invia`.
- Trattare l'editor locale come superficie di revisione vincolata, non come un editor grafico libero.
- Se una fase fallisce, conservare gli artefatti validi, non avanzare di stato e dichiarare il fallback disponibile.
