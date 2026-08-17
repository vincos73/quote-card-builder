---
name: quote-card-builder
description: Trasforma frasi, testi, URL, documenti e idee in quote card. Usa questa skill per trovare o scrivere una frase forte, mostrare provenienza e possibili classificazioni, confrontare candidati, progettare la direzione visuale e produrre una quote card o il relativo post kit lasciando all'utente la responsabilità editoriale finale.
---

# Quote Card Builder

Versione: **1.1.0 — Poster Highlights**

Separare sempre provenienza osservata, dichiarazioni editoriali dell'utente e produzione visuale. La skill non inventa dati né certifica le scelte dell'utente: propone etichette e segnala incongruenze, ma l'utente può modificare e approvare testo, classificazione, prova, attribuzione ed è il garante finale.

Non ricavare il brand dalla fonte, dalla memoria o dal profilo dell'utente. Usare soltanto un profilo fornito o approvato nel lavoro corrente; offrire un profilo neutro solo come scelta esplicita.

Gestire il lavoro con questi stati: `bozza` → `candidati_pronti` → `candidato_selezionato` → `contenuto_approvato` → `prova_visuale_pronta` → `prova_visuale_approvata` → `rendering` → `qa` → `consegnato`. Le approvazioni dell'utente fanno avanzare gli stati editoriali; i gate automatici bloccano soltanto errori strutturali, tecnici o visuali.

## Gate obbligatorio dell'editor

Quando Python, un browser locale e la ricezione degli eventi del server sono disponibili, il percorso editoriale è obbligatorio: dopo aver preparato e validato il manifest, avviare `scripts/card_review_server.py`, aprire nello stesso turno l'URL `127.0.0.1` restituito e verificare che il Visual Review Studio sia effettivamente visibile. Non mostrare una card come prodotta e non eseguire `render_quote_card_pack.py` direttamente prima che l'utente abbia usato `Genera` nell'editor. L'azione `Genera` è l'unico evento che può far avanzare la sessione da revisione a produzione.

Il fallback conversazionale o il rendering diretto sono ammessi soltanto dopo aver osservato e dichiarato un'indisponibilità o un errore reale di una delle capacità necessarie. Non scegliere il fallback per comodità, non sostituire l'apertura dell'editor con un link scritto in chat e non considerare sufficiente la sola creazione di SVG/PNG locale. Se l'URL è stato avviato ma non è stato aperto o non è visibile, la sessione resta in revisione e non può essere consegnata.

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
5. Se occorre cercare la frase, proporre 3 candidati come scelta predefinita e al massimo 5. Se l'utente ha già fornito una frase unica, non trasformarla artificialmente in un elenco numerato.
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

1. Dopo un confronto chiedere soltanto il numero del candidato e l'attribuzione visibile (testo libero, senza classificarne il ruolo). Se non è stato offerto alcun elenco di candidati, chiedere direttamente solo l'attribuzione visibile; non richiedere un numero fittizio.
2. Registrare la scelta come `candidato_selezionato`; non chiedere in chat una seconda conferma di etichette quando l'editor locale è disponibile.
3. Aprire l'editor con il candidato come base interamente modificabile nei campi editoriali.
4. Consentire all'utente di cambiare liberamente testo e attribuzione nell'editor; mostrare trasformazione e stato della prova come informazioni nel ledger inferiore. Il ruolo di attribuzione non ha un controllo dedicato nell'editor, perché non produce alcun trattamento visivo diverso sulla card: viene derivato automaticamente come `author` quando l'etichetta non è vuota, `none` quando è vuota. Se l'utente chiede di cambiare queste dichiarazioni, aggiornarle conversazionalmente senza downgrade o correzioni automatiche.
5. L'editor espone una sola azione primaria: `Genera`. Il clic salva le scelte correnti, registra la responsabilità editoriale dell'utente, supera il gate tecnico e produce direttamente i formati selezionati; non richiedere un passaggio preliminare di invio o approvazione.
6. Registrare `declared_by: user` e mantenere separati i dati osservati dalla fonte dalle dichiarazioni dell'utente.
7. Quando l'editor non è disponibile, chiedere conversazionalmente le scelte necessarie e registrarle come dichiarazioni dell'utente.
8. Quando serve un artefatto strutturato, creare il manifest e validarlo con `python3 scripts/validate_quote_manifest.py <manifest.json>`; la validazione è strutturale, non una certificazione editoriale.

## Fase 4: direzione visuale e brand

Procedere dopo `candidato_selezionato`; l'editor raccoglie le dichiarazioni dell'utente e può approvare direttamente la prova se il QA tecnico passa.

1. Risolvere un profilo brand fornito, approvato nel lavoro corrente, configurato con l'utente oppure neutro scelto esplicitamente. Il profilo neutro canonico usa `primary: #072743`, `accent: #E3F4FF`, `background: #FEFDFB`, `text: #323232`, font `Arial` con fallback `Helvetica`; non rappresenta l'identità dell'utente e non va sostituito senza una scelta esplicita.
2. Proporre tre direzioni adattate allo stesso contenuto e allo stesso brand:
   - `editorial` / Contorni: pagina aperta, testo di grande scala con alternanza iniziale normale/grassetto e contorni di livello nei margini;
   - `statement` / Manifesto: maiuscolo visuale e scala dominante, con una riga inizialmente in accento, eco concentrica d'angolo e fonte allineata a destra;
   - `contextual` / Campo: foglio editoriale incastonato in un campo cromatico con una riga inizialmente evidenziata e una sola regola verticale.
3. Differenziare le direzioni per composizione, non soltanto per colore o font.
4. Preparare una proposta di a capo coerente con significato e impatto: privilegiare attacco forte, unità semantiche nette, ritmo e chiusura memorabile, evitando righe deboli o parole isolate. Calcolare la divisione sulla lunghezza visiva delle parole, non sul conteggio dei caratteri, e penalizzare le righe di una sola parola: il numero di righe corrente è soltanto una preferenza debole, non un vincolo. Nell'editor questo calcolo resta un'azione esplicita dell'utente, mai un riassetto automatico dopo una modifica testuale: proporlo con un solo comando, annullabile. Il controllo finale resta all'utente: ogni newline che scrive deve restare esattamente dove viene scritto; una riga vuota vale come riga intera di spazio verticale.
5. Quando Python, browser locale e ricezione degli eventi sono disponibili, creare un manifest 0.4 conforme a [references/visual-editor.md](references/visual-editor.md), inizialmente in `candidato_selezionato`, con la stessa composizione per `4x5`, `1x1` e `9x16`: l'editor condivide testo e a capo fra i rapporti, quindi righe diverse per formato verrebbero comunque riallineate alla prima modifica. Impostare `presentation.output_mode` sul formato attivo iniziale (il primo elenco in `formats`), non su `all`: l'utente lavora tipicamente su un solo rapporto e la consegna finale non deve includere gli altri due senza una scelta esplicita.
6. Avviare `python3 scripts/card_review_server.py <manifest.json> --session-dir <session-dir>`, aprire immediatamente nello stesso turno ed esclusivamente l'URL `127.0.0.1` restituito nel browser locale, verificare che l'editor sia visibile all'utente e mantenere il processo attivo in attesa di `Genera`.
7. Nell'editor lasciare modificabili testo, attribuzione, direzione, a capo manuali e righe vuote, formattazioni `bold`, `italic`, `underline`, `highlight`, `accent` e `outline` applicate a selezioni testuali, scala dal massimo, posizione verticale, logo, elemento grafico come `auto` o `hidden` e output finale come `all`, `4x5`, `1x1` o `9x16`. `highlight` è disponibile in tutte le direzioni, inclusa `statement` / Poster: la fascia di evidenziazione va misurata con le metriche del font in grassetto (reali quando disponibili, altrimenti un fattore di compensazione), perché nel Poster tutto il testo è renderizzato in grassetto e una misura basata sul regular produce una fascia troppo corta. `highlight`, `accent` e `outline` decidono tutti e tre di cosa è riempito un glifo: tenerli mutuamente esclusivi sullo stesso intervallo ed esporli come un solo controllo a stati, non come tre interruttori che si sovrascrivono in silenzio. `outline` disegna glifi cavi nel colore d'inchiostro che il testo avrebbe comunque avuto, con spessore proporzionale alla riga che traccia: è un cambio di forma e non deve promuovere una riga Poster a enfasi. Poiché un glifo cavo mette sulla pagina una frazione dell'inchiostro di uno pieno, il quality gate lo misura sullo `stroke` e non sul `fill` assente, con una soglia di contrasto più severa di quella del testo pieno, e segnala un contorno troppo piccolo perché le aste restino aperte. Applicare un trattamento non deve costare la selezione all'utente, e l'editor deve possedere la propria cronologia di annullamento su righe e stili: la ricostruzione del markup azzera quella nativa del browser. Testo, a capo e formattazioni restano identici tra `4x5`, `1x1` e `9x16`: cambiare formato non deve mai ricomporre righe o stili scelti dall'utente, solo la dimensione carattere adattata al formato. Per il profilo neutro usare Arial, disponibile su macOS e Windows, con fallback Helvetica; un font dichiarato dal brand resta protetto e non viene sostituito. Quando una card non contiene ancora trattamenti manuali né enfasi legacy, mostrare una firma iniziale per direzione: normale/grassetto in Contorni, una riga accentata in Moduli × Poster e una riga evidenziata in Campo. La prima formattazione selezionata dall'utente sostituisce quel trattamento iniziale. Mostrare inoltre un pannello non editabile con i colori del profilo applicato alla card, inclusi campione, valore esadecimale e uso previsto. Il pannello non deve mostrare né descrivere la palette dell'interfaccia: i colori della card restano protetti e cambiano solo con un profilo scelto o approvato dall'utente. Le tab di anteprima restano disponibili per controllare tutti i rapporti anche quando l'utente ne consegna uno solo. Associare senza ulteriori opzioni `editorial` al sistema Contorni, `statement` al sistema Moduli × Poster con fonte sempre a destra e `contextual` al sistema Campo. Calcolare sempre un vero max-fit separato per formato, direzione e posizione: il 100% è la massima dimensione che resta entro guide e aree riservate a logo, attribuzione, metadati ed elemento grafico; il cursore può soltanto ridurla fino all'80%. Preview, quality gate ed export devono usare lo stesso calcolo. Mostrare trattamento e stato della prova soltanto nel ledger inferiore. Se il profilo non contiene i file necessari, dichiarare quali trattamenti non sono disponibili o usano una resa simulata e indicare di fornire i file mancanti o approvare un font sostitutivo. Non risincronizzare il form durante la digitazione in modo da cancellare newline o input parziali; quando cambia il testo, riallineare gli intervalli di formattazione e rimuovere soltanto quelli il cui contenuto non esiste più. Fonte osservata, brand e dimensioni restano protetti.
8. Il server locale deve applicare immediatamente e atomicamente ogni batch già validato, aggiornare la revisione e riabilitare l'editor nella stessa richiesta. `python3 scripts/apply_card_review.py <manifest.json> <session-dir>/feedback.json --session-dir <session-dir>` resta il fallback di recupero per feedback pendenti lasciati da versioni precedenti. Rifiutare revisioni superate o invarianti violate, quindi rigenerare la preview con lo stesso renderer usato per l'export.
9. Su `POST /api/generate`, applicare nello stesso batch le modifiche correnti, rigenerare la prova, eseguire il controllo qualità tecnico e registrare `prova_visuale_approvata` nel production manifest.
10. Il server deve produrre un preflight deterministico, poi attivare il chatbot Codex locale con un prompt fisso e path-scoped che lancia `render_quote_card_pack.py` sul production manifest senza modificare codice o manifest. Restituire link autenticati ai PNG prodotti, lo `request_id` del chatbot e lo stato aggiornabile via `GET /api/agent-status`; se il CLI Codex non è disponibile, dichiarare il fallback locale senza simulare l'attivazione.
11. Se e soltanto se l'editor locale non è disponibile dopo un preflight osservabile, creare un visual manifest 0.2 conforme a [references/visual-manifest.md](references/visual-manifest.md) e generare le tre prove SVG con `python3 scripts/render_quote_card.py <manifest.json> --output-dir <cartella> --all-directions --png never`; dichiarare sempre quale capacità è mancata e non chiamare questa prova una produzione finale.
12. Quando la sessione espone Node.js e `sharp` già configurati, usare esclusivamente l'helper incluso `scripts/svg_to_png.cjs` passando al renderer `--png required --node <node> --node-modules <node_modules>`. Non installare dipendenze. Se il convertitore non è disponibile, consegnare SVG e dichiarare che il PNG non è stato prodotto.
13. Leggere il report `*-qa.json` e ispezionare visivamente tutte le prove renderizzate. Correggere logo, overflow, collisioni, contrasto, gerarchia e leggibilità prima di mostrarle.
14. Mostrare le prove con quote, attribuzione, layout, direzione visuale, formato e dichiarazioni editoriali. Impostare lo stato `prova_visuale_pronta`.
15. Lasciare all'utente `Genera`, `Cambia direzione` oppure `Torna al testo`. `Genera` costituisce l'istruzione esplicita di congelare la prova corrente e produrre gli output selezionati.

## Fase 5: generazione e controllo qualità

Procedere dopo `prova_visuale_approvata`, registrato automaticamente quando l'utente preme `Genera` e il quality gate tecnico passa.

1. Registrare l'approvazione in un production manifest 0.3 conforme a [references/production-manifest.md](references/production-manifest.md). Conservare direzione, prova, hash del testo, autore e data dell'approvazione.
2. Includere nel production manifest tutti i rapporti soltanto con `presentation.output_mode: all`; altrimenti includere esclusivamente il formato `4x5`, `1x1` o `9x16` scelto. Conservare per ogni formato richiesto gli a capo approvati — identici fra i rapporti quando l'approvazione arriva dall'editor visuale — e verificare che ognuno ricostruisca esattamente il testo approvato; non ritagliare o ridimensionare un altro output.
3. Produrre PNG come consegna predefinita. Quando Node.js e `sharp` sono già disponibili, eseguire `scripts/render_quote_card_pack.py <manifest.json> --output-dir <cartella> --png required --svg auto --node <node> --node-modules <node_modules>`: l'SVG è un intermedio tecnico e viene eliminato dopo la conversione riuscita. Non installare dipendenze.
4. Se la conversione PNG non è disponibile, conservare l'SVG come fallback dichiarato. Quando Python espone Pillow, usarlo per il fitting sulle metriche reali; in sua assenza accettare il fallback dichiarato `deterministic_heuristic`.
5. Mostrare fedeltà, etichette, attribuzione, numeri, negazioni e cautele come riepilogo consultivo; non sovrascrivere le dichiarazioni approvate dall'utente.
6. Controllare leggibilità alla dimensione tipica del feed, contrasto, gerarchia, a capo, margini di sicurezza, sforamenti, font e risorse in ogni rapporto.
7. Non modificare il testo approvato durante il fitting. Calcolare il massimo sicuro per ciascun formato e applicare `text_scale` come sola riduzione da quel massimo; tornare all'approvazione editoriale soltanto se la dimensione risultante non è leggibile.
8. Leggere il report `*-production-qa.json` e verificare dimensioni, rapporti, metodo di fitting, contrasto e hash. Lo stato deve restare `qa` durante l'ispezione.
9. Ispezionare visivamente tutti i PNG richiesti in un solo passaggio comparativo; ispezionare gli SVG soltanto quando sono il fallback effettivamente consegnato. Correggere eventuali problemi, rigenerare e confermare al massimo una seconda volta.
10. Soltanto dopo l'ispezione, eseguire `scripts/finalize_quote_card_pack.py <qa.json> --all-formats --reviewer <nome>`. Mostrare gli artefatti finali solo quando il report è `passed` e lo stato è `consegnato`.
11. Su richiesta aggiungere caption, alt text e scheda di provenienza.

## Regole permanenti

- Scrivere nella lingua dell'utente.
- Non inventare fonte, autore, speaker, logo, firma, URL, colori o tagline.
- Non promuovere autonomamente `USER_SUPPLIED` a `VERIFIED`; se l'utente sceglie `VERIFIED`, registrarlo come sua dichiarazione.
- Non alterare autonomamente negazioni, condizioni, cautele, numeri o grado di certezza.
- Cercare sempre una formulazione e una scansione visiva d'impatto, ma proporre ogni riscrittura all'utente invece di modificare silenziosamente il testo approvato.
- Segnalare combinazioni potenzialmente ambigue senza correggerle, riclassificarle o bloccarle.
- Conservare separate identità del brand e attribuzione della frase.
- Registrare sempre la responsabilità editoriale dell'utente; `Genera` include le modifiche correnti e non richiede altri pulsanti di invio o approvazione.
- Trattare l'editor locale come superficie di revisione vincolata, non come un editor grafico libero.
- Non saltare mai il Visual Review Studio quando è disponibile: l'editor deve essere aperto e visibile prima di qualunque produzione, e il rendering diretto non è un sostituto dell'azione `Genera`.
- Se una fase fallisce, conservare gli artefatti validi, non avanzare di stato e dichiarare il fallback disponibile.
