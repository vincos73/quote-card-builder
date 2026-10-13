# Quote Card Builder — Product Requirements Document

<!-- impeccable:product-schema 1 -->

Stato del documento: rilascio v1.0.1; addendum candidato locale 1.8.2
Data: 15 agosto 2026
Ambito: skill Codex, con primo nucleo editoriale riutilizzabile

## Platform

web

## Users

Creator, marketer, autori, giornalisti, curatori di newsletter, consulenti e social media manager che devono trasformare rapidamente una frase o una fonte in una quote card affidabile. Il pubblico comprende sia utenti neofiti, che devono arrivare al primo output senza imparare un editor professionale, sia utenti ricorrenti, che si aspettano di riutilizzare il proprio profilo di brand.

## Product Purpose

Trasformare frase, testo, URL, documento o idea in una quote card pronta da condividere, mantenendo sotto il controllo dell’utente testo, attribuzione, provenienza e scelte visuali. Il successo è ottenere un artefatto leggibile e coerente in pochi passaggi, con un controllo reale prima della generazione.

## Positioning

Quote Card Builder non compete con un canvas libero. Unisce selezione editoriale, dichiarazioni di provenienza, composizioni vincolate, preview ed export dallo stesso renderer e quality gate tecnico. La promessa specifica è velocità senza confondere parole della fonte, formulazione pubblicata, attribuzione e identità del brand.

## Operating Context

La skill può aprire il Visual Review Studio web locale su `127.0.0.1` oppure usare il plugin MCP locale. Il nuovo workspace Extension apre un editor vuoto; il flusso MCP conversazionale continua ad aprire l’editor con i dati già scelti. Il Visual Review Studio locale gestisce 4:5, 1:1 e 9:16 e profili locali espliciti. Il workspace MCP produce 4:5 o 1:1 con palette scelta nell’editor; non trasferisce i profili locali.

## Capabilities and Constraints

- editor vincolato, non canvas grafico libero;
- font e logo del brand, fonte e dimensioni protetti durante la revisione; palette della card modificabile esplicitamente dall’utente;
- profili di brand locali riutilizzabili, esportabili come JSON e scelti sempre esplicitamente;
- profili limitati a nome, colori, font e logo, senza contenuti editoriali;
- alt text automatico con sostituzione facoltativa nel pannello avanzato `Accessibilità`;
- master e adattamenti compositivi distinti per `4:5`, `1:1` e `9:16`;
- PNG come consegna predefinita e SVG come fallback dichiarato quando manca un convertitore;
- nessuna deduzione automatica del brand da fonte, memoria o profilo personale.

## Addendum — workspace MCP locale candidato 1.8.2

Questo addendum descrive il sorgente locale candidato e l'installazione personale. Non dichiara
che la versione sia stata pubblicata o distribuita su un servizio remoto.

- `quote_card_builder_open_workspace` accetta `{}` e apre l’editor vuoto da navigazione globale,
  scheda del thread o selezione del plugin senza frase. Non inventa
  una frase, un’attribuzione o una palette; l’utente sceglie tutti e tre prima della preview o
  della generazione.
- `quote_card_builder_open_editor` apre una scheda contenuto fullscreen per contenuti già
  selezionati nella conversazione, con le relative scelte preliminari.
- La bozza si recupera localmente nel workspace. Non c’è sincronizzazione fra dispositivi o
  conversazioni, associazione a file o menzioni, né applicazione automatica di modifiche proposte
  dal modello.
- I formati MCP restano 4:5 e 1:1. Il 9:16, i profili salvati e il pacchetto multiformato
  appartengono al Visual Review Studio locale.
- Il renderer Python canonico resta la base della preview e della produzione. Il servizio remoto
  mantiene il proprio stato fino a un deployment verificato; l’Extension non implica una
  migrazione dell’hosting né un nuovo deployment.

## Storico — MCP remoto live 1.8.5/UI v1.52

La versione live v1.52 aggiorna l'esperienza del workspace remoto, mantenendo l'endpoint e il
trasporto MCP senza OAuth. Il server apre con `{}` e restituisce stato vuoto. Se non è recuperata una
bozza, la UI presenta il demo editabile “Le idee migliori meritano di essere condivise.” senza nome
di autore, con attribuzione vuota e le scelte nessuna attribuzione/palette neutra marcate demo-only.
Se arriva una frase esplicita mentre il demo è intatto, lo sostituisce. Per trattare il risultato come card reale, l'utente sceglie testo, attribuzione e palette; il demo resta identificato come esempio.

Nel workspace remoto **Download PNG** è l'unica azione di produzione e consegna: con un clic genera
e salva il PNG. Non esiste un invio separato dell'immagine alla chat. Gli URL temporanei degli export
scadono entro 24 ore. Queste sono caratteristiche del servizio remoto live; l'installazione locale
confermata resta 1.8.3 e conserva il flusso documentato sopra.

## Storico — MCP remoto live 1.8.6/UI v1.53

La versione live aggiorna il demo iniziale alla frase su quattro righe “Le idee migliori / meritano /
di essere / condivise.”, con prima riga in grassetto, “meritano” e “di essere” in corsivo e “condivise” evidenziato. Le modifiche di formattazione e spaziatura non azzerano le scelte demo e lo stato delle
scelte ancora pendenti resta visibile dopo il rendering. La palette neutra è preselezionata nei nuovi
workspace, in New Card, negli input senza palette e nei draft ripristinati che non hanno ancora una
scelta. La modifica del testo conserva la palette neutra o una palette personalizzata esplicita.
La versione è live su Cloud Run; l’installazione locale confermata resta 1.8.3. La chat ChatGPT già aperta poteva mostrare UI v1.52 in cache; il client è stato ricaricato per la versione successiva.

## Addendum — MCP remoto live 1.8.7/UI v1.54

La versione live preimposta l'attribuzione come “nessuna” nei nuovi workspace, New Card, input senza
attribuzione e bozze legacy con attribuzione vuota, così l'utente può visualizzare il testo senza una
domanda obbligatoria. Le attribuzioni nominative esplicite vengono mantenute; una scelta esplicita
“con autore” senza testo resta incompleta e visibile. Modificare il demo non ripristina una scelta
“nessuna attribuzione” e digitare avvia l'anteprima. La palette neutra e il resto del comportamento
UI v1.53 rimangono invariati. La versione è live su Cloud Run; l'installazione locale confermata resta 1.8.3. Una nuova chat ha mostrato il badge v1.54, senza una prova manuale dei pulsanti nel client reale.

## Storico — MCP remoto live 1.8.8 / UI v1.55

Per una richiesta chiara di procedere da un URL leggibile, il modello usa la navigazione disponibile nell'host, seleziona una citazione esatta e apre una sola volta l'editor già popolato. Il server non acquisisce URL. Attribuzione assente resta nessuna, a meno che l'utente la fornisca o la fonte verifichi il nome; la palette neutra è il default. Una modifica esplicita successiva dalla chat usa una patch revisionata sulla bozza completa corrente; il widget applica la patch solo se bozza e revisione corrispondono, altrimenti segnala il conflitto. Per rendere disponibile il tool nel follow-up, richiama il plugin nella chat. La revisione è stata sostituita da UI v1.56; i test nativi su v1.55 hanno verificato apertura e due aggiornamenti con conservazione delle scelte. Evidenze in `RELEASE-STATUS.md`.

## Storico — MCP remoto live 1.8.8 / UI v1.56

La UI live usa la navigazione dell'host per leggere un URL e apre un solo editor già popolato quando la richiesta di procedere è chiara. Le modifiche successive usano il tool `quote_card_builder_update_editor` sulla bozza e revisione correnti; ogni follow-up deve richiamare il plugin in ChatGPT. Il server non acquisisce URL. La versione è live al 100% su Cloud Run, con smoke di produzione PASS, 352 test senza skip e 33 controlli browser superati. Il browser usa un host MCP Apps simulato. Due aggiornamenti consecutivi sono stati verificati nella UI nativa v1.56, con conservazione di testo, stile e scelte non modificate. L'installazione locale confermata resta 1.8.3. Dettagli in `RELEASE-STATUS.md`.

## Brand Commitments

L’identità dell’interfaccia è Vincos e segue il sistema Plotter Bench documentato in `DESIGN.md`. L’identità della card resta invece quella del profilo fornito o approvato dall’utente: palette dell’editor e palette dell’output non devono essere confuse.

## Evidence on Hand

- renderer deterministico SVG/PNG e adattatori di formato nel repository;
- Visual Review Studio locale con preview ed export prodotti dallo stesso motore;
- manifest, report QA, output e sessioni di prova sotto `work/`;
- suite automatica Python e controlli JavaScript per validazione, rendering, server e formattazione;
- nessun testimonial, benchmark commerciale o dato di utilizzo pubblico da inventare.

## Product Principles

1. La provenienza resta visibile e la decisione editoriale appartiene all’utente.
2. Brand, attribuzione e persona citata sono ruoli distinti.
3. Il percorso principale deve restare rapido; opzioni avanzate e spiegazioni appaiono soltanto quando servono.
4. Preview, quality gate ed export devono condividere lo stesso renderer e gli stessi vincoli.
5. La persistenza locale deve essere esplicita, leggibile e resistente agli aggiornamenti della skill.

## Addendum 1.8.10 — composizione per smartphone

Questo addendum descrive le regole della versione 1.8.10/UI v1.57, condivise dalla skill e dai flussi locale/MCP. Lo stato della distribuzione è registrato in `RELEASE-STATUS.md`. Quando l'utente ha già fornito una frase e chiede chiaramente di procedere, l'editor deve aprirsi una sola volta con una composizione iniziale leggibile, senza una conferma separata per layout o trattamenti. La composizione può cambiare gli a capo e aggiungere enfasi, ma deve conservare esattamente parole, punteggiatura, negazioni e cautele. Non riscrivere editorialmente la citazione per adattarla alla card.

Per circa 20–40 parole, comporre in genere 6–9 righe brevi e semanticamente bilanciate, con 12–20 caratteri per riga e un limite morbido di 22. La guida resta flessibile: non isolare parole funzionali né forzare molte righe per citazioni brevi. Puntare a un testo di circa 30–40 px quando la card è vista a 375 px di larghezza, occupando circa il 45–60% dell’altezza. Accorciare le righe semanticamente anziché ridurre tutto il testo. Applicare 1–3 enfasi brevi, di norma con non più di due trattamenti, preservando ogni parola della fonte. Le richieste esplicite di layout, stile o testo semplice dell'utente prevalgono.

Nel percorso MCP, `lines` trasferisce la composizione e `text` è la loro unione con newline. `styles` trasporta separatamente le enfasi con intervalli Unicode che includono i newline nel conteggio. I marcatori Markdown non fanno parte del contenuto. Un cambio di soli a capo o stili mantiene `VERBATIM` e lo stato della prova: la formattazione non costituisce una modifica editoriale.

## Accessibility & Inclusion

Ogni output deve avere un alt text disponibile. L’interfaccia usa controlli nativi, focus visibile, stati comprensibili senza dipendere dal solo colore, regioni live, target mobili di almeno 44px e rispetto di `prefers-reduced-motion`. La simulazione delle principali condizioni di visione dei colori è un controllo di anteprima, non sostituisce il quality gate di contrasto.

## 1. Sintesi

Quote Card Builder trasforma una frase, un contenuto o un'idea in una quote card pronta per la pubblicazione, mantenendo esplicita la distanza fra le parole della fonte e il testo mostrato nella card.

Il prodotto non compete sul semplice rendering. Compete sulla fiducia editoriale:

> Trasforma qualsiasi contenuto nella quote card giusta, senza inventare quello che la persona ha detto.

La differenza è prodotta da tre capacità congiunte:

1. trovare la frase più forte in una fonte;
2. dichiarare come è stata ottenuta e quanto è verificabile;
3. trasformarla in un artefatto leggibile e coerente con il brand senza confondere autore, editore e persona citata.

## 2. Problema

I generatori di quote card trattano quasi sempre la frase come un campo di testo già risolto. Lasciano quindi all'utente i passaggi più rischiosi:

- estrarre una frase significativa da una fonte lunga;
- accorciarla senza alterarne il senso;
- distinguere parole letterali, editing, parafrasi e copy originale;
- verificare attribuzione e provenienza;
- scegliere una direzione visiva coerente con il contenuto e con il brand;
- controllare leggibilità e fedeltà prima della pubblicazione.

Il risultato può essere graficamente gradevole ma editorialmente falso, ambiguo o debole.

## 3. Utenti e lavori da svolgere

### Utenti primari

- autori, giornalisti e curatori di newsletter;
- social media manager e designer di contenuti;
- consulenti, ricercatori e formatori;
- brand che pubblicano estratti di interviste, interventi, articoli e report.

### Esigenza principale

Quando incontro un passaggio interessante o ho un'idea da pubblicare, voglio trasformarlo rapidamente in una quote card forte, mantenendo visibile la provenienza e potendo assumermi la responsabilità di ogni scelta editoriale.

## 4. Principi di prodotto

1. **La provenienza resta visibile, la decisione è dell'utente.** La skill distingue dati osservati e dichiarazioni dell'utente senza certificare queste ultime.
2. **Trasformazione e verificabilità sono assi distinti.** `VERBATIM` non significa automaticamente verificato.
3. **Persona citata, autore del testo, editore e brand sono ruoli distinti.** Non usare un logo o una firma come attribuzione implicita.
4. **Il brand non si inferisce.** Usare solo un profilo fornito o approvato nel lavoro corrente; il profilo neutro richiede una scelta esplicita.
5. **L'utente è il garante editoriale.** Può cambiare testo, classificazione, prova e attribuzione.
6. **Solo la qualità tecnica e visuale è bloccante.** Le incongruenze editoriali sono segnalazioni consultive.
7. **Il core deve essere indipendente dal formato.** Evidenze e brand potranno servire anche Carousel Builder e Infographic Builder.

## 5. Obiettivi

### Obiettivi della prima versione di prodotto

- accettare frase, testo, URL, documento o idea;
- proporre da 3 a 5 candidati quando la selezione non è già determinata;
- mostrare per ogni candidato trasformazione, stato della prova, attribuzione e passaggio di supporto;
- raccomandare una frase con una motivazione breve;
- proporre tre direzioni grafiche realmente diverse nella composizione;
- risolvere un brand approvato oppure guidare una configurazione minima;
- mostrare un'anteprima prima del rendering completo;
- offrire un editor visuale locale vincolato quando la sessione lo consente;
- produrre un master 4:5 e adattamenti compositivi 1:1 e 9:16;
- consegnare, su richiesta, caption e alt text.

### Non obiettivi iniziali

- verifica fattuale generale di tutto il contenuto;
- ricerca automatica della fonte originaria nel web senza richiesta dell'utente;
- pubblicazione sui social;
- editor grafico libero simile a Canva;
- generazione in serie su grandi archivi;
- deduzione automatica del brand dal sito, dalla fonte o dalla memoria;
- generazione di ritratti realistici della persona citata senza asset e diritti espliciti.

## 6. Modello di provenienza e dichiarazione

Ogni candidato deve avere due etichette indipendenti.

### 6.1 Tipo di trasformazione

| Valore | Significato | Regola di pubblicazione |
|---|---|---|
| `VERBATIM` | Testo dichiarato come coincidente con un passaggio della fonte | Etichetta scelta dall'utente |
| `EDITED` | Testo accorciato o corretto rispetto alla fonte senza introdurre nuove tesi | Mostrare sempre il passaggio originale e le modifiche materiali |
| `PARAPHRASE` | Significato ricostruito con parole diverse | Non presentare come parole letterali; preferire “idea tratta da” |
| `AI_GENERATED` | Formulazione nuova ottenuta da un'idea o da un brief | Non attribuire come frase pronunciata da una persona |

### 6.2 Stato della prova

| Valore | Significato |
|---|---|
| `VERIFIED` | Il testo o il passaggio sono stati riscontrati nella fonte disponibile |
| `USER_SUPPLIED` | La frase o l'attribuzione sono state fornite dall'utente, ma non verificate nella sessione |
| `UNVERIFIED` | Manca una fonte sufficiente o accessibile |
| `CONFLICT` | Le fonti disponibili sono discordanti o contraddicono l'attribuzione proposta |

### 6.3 Responsabilità editoriale

- La skill propone etichette e mostra la provenienza osservata, senza sovrascrivere le scelte dell'utente.
- Ogni combinazione di trasformazione, prova e attribuzione è salvabile e renderizzabile.
- Le scelte approvate sono registrate con `declared_by: user`.
- Restano obbligatori soltanto tipi, enum, campi strutturali e locator tecnicamente validi quando presenti.

## 7. Flusso ideale

### 1. Fonte (`SOURCE`)

Chiedere: «Cosa vuoi trasformare in quote card?»

Input supportati:

- frase già scelta;
- testo incollato;
- URL o documento leggibile dagli strumenti della sessione;
- idea da trasformare in una formulazione originale.

### 2. Ricerca dei candidati (`DISCOVERY`)

- Se la frase è già scelta, preservarla e valutarla.
- Se la fonte contiene più possibilità, proporre 3 candidati per default e al massimo 5.
- Se l'input è un'idea, produrre formulazioni marcate `AI_GENERATED`.

### 3. Provenienza e dichiarazioni (`PROVENANCE`)

Per ogni candidato mostrare:

- testo proposto;
- tipo di trasformazione;
- stato della prova;
- passaggio sorgente o nota “nessuna fonte letterale”;
- attribuzione proposta e ruolo;
- eventuale osservazione consultiva.

### 4. Classifica (`RANKING`)

Usare provenienza e possibili incongruenze come contesto, poi assegnare un punteggio editoriale:

- chiarezza autonoma: 25;
- rilevanza per la tesi: 20;
- specificità e memorabilità: 20;
- concisione: 15;
- ritmo orale e potenziale tipografico: 10;
- potenziale visuale: 10.

Raccomandare un solo candidato e motivarlo in massimo due frasi. Il punteggio non deve nascondere problemi di prova.

### 5. Approvazione editoriale

Ottenere un'approvazione esplicita su:

- testo;
- dichiarazioni di trasformazione e prova;
- attribuzione;

### 6. Direzione visuale (`VISUAL CONCEPT`)

Proporre tre archetipi di composizione, adattati al brand approvato:

1. `editorial` / Contorni: pagina aperta, testo di grande scala e linee di livello agli angoli;
2. `statement` / Manifesto: sistema Moduli × Poster, maiuscolo visuale dominante, forme angolari discrete e fonte sempre a destra;
3. `contextual` / Campo: foglio editoriale nel campo d'accento, punti di orientamento e una regola verticale accanto alla citazione;

Le tre direzioni devono differire per struttura, non solo per palette o font.

### 7. Identità di brand (`BRAND`)

Risolvere il brand da una di queste fonti, in ordine:

1. profilo o brand pack fornito;
2. profilo approvato nel lavoro corrente;
3. configurazione guidata minima;
4. profilo neutro scelto esplicitamente.

### 8. Anteprima e approvazione visuale (`PREVIEW`)

Mostrare una prova con:

- frase e a capo reali;
- attribuzione;
- ruolo del brand;
- layout e direzione visuale;
- formato e margini di sicurezza;
- dichiarazioni editoriali dell'utente.

L'approvazione del concetto non equivale all'approvazione della prova renderizzata.

### 9. Controllo qualità (`QUALITY GATE`)

Bloccare la generazione finale in presenza di errori critici.

Controlli editoriali consultivi:

- fedeltà alla fonte;
- etichetta di trasformazione corretta;
- stato della prova corretto;
- assenza di perdita di cautele, negazioni, numeri o condizioni.

Controlli visuali:

- leggibilità alla dimensione tipica del feed;
- contrasto;
- gerarchia;
- a capo coerenti con il significato;
- assenza di vedove, parole isolate e collisioni;
- coerenza con il profilo di brand approvato.

Controlli tecnici:

- dimensioni e formato corretti;
- margini di sicurezza;
- font e asset risolti;
- testo alternativo disponibile;
- nessun ritaglio o overflow.

### 10. Generazione e materiali per la pubblicazione

Produrre il master 4:5. Su richiesta derivare:

- 1:1;
- 9:16;
- caption;
- alt text;
- scheda di provenienza interna.

Ogni rapporto richiede un adattamento del layout, non un ritaglio silenzioso.

## 8. Stati del lavoro

```text
bozza
  -> candidati_pronti
  -> candidato_selezionato
  -> contenuto_approvato
  -> prova_visuale_pronta
  -> prova_visuale_approvata
  -> rendering
  -> qa
  -> consegnato
```

Tornare a `bozza` se cambia la fonte. Dopo il numero del candidato passare a `candidato_selezionato`. `Genera` salva le dichiarazioni, registra la prova corrente dopo il gate tecnico e produce i formati selezionati nello stesso batch.

## 9. Nuclei costruiti

Il primo incremento è stato il **Content/Evidence Core**, una porzione completa, utilizzabile e verificabile, che copre:

1. acquisizione di frase, testo o idea;
2. generazione di candidati;
3. registrazione di evidence span e locator;
4. classificazione sui due assi;
5. classifica accompagnata da provenienza e osservazioni consultive;
6. scelta esplicita del candidato, con tutti i campi editoriali modificabili nell'editor;
7. produzione di un manifest validato per il successivo adapter visuale.

### Criteri di accettazione del nucleo

- una frase letterale presente nella fonte può essere validata come `VERBATIM + VERIFIED`;
- una frase modificata può conservare `VERBATIM` se l'utente lo dichiara;
- parafrasi, stato della prova e ruolo restano scelte dell'utente;
- un conflitto è registrabile e non blocca la selezione;
- il candidato selezionato include motivazione, attribuzione e stato editoriale;
- il manifest è indipendente da renderer, brand e canale.

Gli incrementi successivi completano il percorso visuale senza indebolire il core:

- **0.2 Visual Proof Renderer:** tre direzioni SVG deterministiche, brand esplicito e report QA;
- **0.3 Production Renderer:** composizioni autonome `4x5`, `1x1` e `9x16`, fitting, hash e finalizzazione dopo ispezione;
- **0.4 Visual Review Studio:** editor locale desktop-first con preview live prodotta dal renderer, salvataggio locale, batch revisionato e applicazione atomica.
- **0.5 Editorial + Visual Studio:** testo modificabile, trattamento riclassificabile e due checkpoint nello stesso editor: `Invia` per il contenuto, `Approva` per la prova visuale.
- **0.6 User-Owned Editorial Studio:** tutti i campi editoriali sono modificabili; nessun downgrade automatico e approvazione diretta con responsabilità dell'utente.
- **0.6.1 Manual Composition Controls:** newline manuali preservati per formato ed enfasi estesa a locuzioni su una o più righe.
- **0.6.2 Visual Text Styling:** editor visuale con grassetto, corsivo, sottolineato, evidenziato e righe vuote come interlinea; trattamento e prova restano informazioni nel ledger; le facce font mancanti producono un messaggio esplicativo e disabilitano soltanto lo stile non garantito.
- **0.6.7 Branded Header Release:** output finale selezionabile per tutti i rapporti o per un singolo aspect ratio, consegna PNG-first con SVG intermedio e testata coordinata `Quote Card Builder by Vincos` in Orbitron, Onest e palette lavanda dell’interfaccia.
- **0.6.8 True Max Fit:** il 100% tipografico diventa il massimo sicuro specifico per formato, direzione e posizione, tenendo conto di guide, logo, attribuzione, metadati ed elemento grafico; il cursore consente soltanto riduzioni fino all'80%.
- **0.6.9 Distinct Layout Core:** Contorni, Moduli × Poster e Campo adottano tre grammatiche strutturali autonome; il maiuscolo del Manifesto resta soltanto visuale e l'editor conserva e riallinea la formattazione dopo le modifiche al testo.
- **0.6.10 One-Step Generate:** una sola CTA `Genera` sostituisce i checkpoint separati, applica la bozza, esegue QA e renderer e restituisce i link ai PNG selezionati nella stessa richiesta.

User-Owned Editorial Studio non espone un canvas libero. Consente di modificare testo, formattazione, attribuzione e ruolo senza riclassificazioni automatiche; trattamento e prova sono dichiarazioni dell'utente mostrate nel ledger e aggiornabili conversazionalmente. Fonte osservata, brand e dimensioni restano immutabili.

## 10. Architettura evolutiva

```text
Content/Evidence Core
  SourceRecord
  EvidenceSpan
  Candidate
  TransformationRecord
  Attribution
  Approval

Brand Identity Core
  BrandProfile
  AssetResolver
  TypographyRoles
  ContrastRules

Format adapters
  Quote Card Builder
  Carousel Builder
  Infographic Builder
```

Il core condiviso deve esporre contratti stabili, non decisioni di layout. Quote Card Builder aggiunge selezione della singola frase, line breaking, attribuzione e composizione. Carousel Builder aggiunge sequenza narrativa. Infographic Builder aggiunge gerarchie di dati e relazioni.

## 11. Requisiti funzionali

| ID | Requisito | Priorità |
|---|---|---|
| QCB-001 | Accettare frase, testo e idea | P0 |
| QCB-002 | Accettare URL e documenti quando leggibili nella sessione | P0 |
| QCB-003 | Proporre 3–5 candidati | P0 |
| QCB-004 | Registrare trasformazione e stato della prova separatamente | P0 |
| QCB-005 | Conservare passaggio sorgente e locator | P0 |
| QCB-006 | Segnalare combinazioni editoriali potenzialmente ambigue senza bloccarle | P0 |
| QCB-007 | Raccomandare un candidato con motivazione breve | P0 |
| QCB-008 | Richiedere approvazione editoriale esplicita | P0 |
| QCB-009 | Proporre tre direzioni visuali strutturalmente diverse | P1 |
| QCB-010 | Risolvere un profilo brand esplicito | P1 |
| QCB-011 | Produrre e approvare una prova visuale | P1 |
| QCB-012 | Renderizzare master 4:5 | P1 |
| QCB-013 | Eseguire QA editoriale, visuale e tecnico | P1 |
| QCB-014 | Adattare la composizione in 1:1 e 9:16 | P1 |
| QCB-015 | Produrre caption, alt text e scheda di provenienza | P2 |
| QCB-016 | Revisionare direzione e composizione in un editor locale vincolato | P1 |
| QCB-017 | Rendere modificabili tutti i campi editoriali e proteggere fonte, brand e dimensioni | P0 |
| QCB-018 | Usare lo stesso renderer per anteprima ed export | P0 |
| QCB-019 | Esportare un profilo brand portabile e validare gli allegati prima del manifest | P1 |

## 12. Requisiti non funzionali

- Nessuna dipendenza obbligatoria per il Content/Evidence Core oltre alla libreria standard Python.
- Manifest leggibile e versionato.
- Errori strutturali, tecnici e visuali bloccanti, espliciti e azionabili.
- Nessuna rete richiesta per validare fonti già acquisite.
- Nessun asset personale incorporato nella skill.
- Informazioni progressive: flusso essenziale in `SKILL.md`, dettagli nei riferimenti.
- Output nella lingua dell'utente.

## 13. Metriche

### Qualità editoriale

- percentuale di candidati selezionati senza riclassificazione successiva;
- percentuale di card consegnate con fonte o stato `USER_SUPPLIED` esplicito;
- numero di osservazioni consultive mostrate prima del rendering;
- tasso di modifica del testo dopo l'approvazione editoriale.

### Utilità

- tempo da input a candidato approvato;
- tasso di accettazione della prima raccomandazione;
- numero medio di cicli prima dell'approvazione visuale;
- percentuale di richieste che includono il post kit.

Non usare engagement social come unica metrica: incentiverebbe frasi più estreme e meno fedeli.

## 14. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Una frase sembra vera perché ha una fonte, ma non compare nella fonte | evidence span validato e doppia etichetta |
| Editing che cambia una cautela o una negazione | confronto visibile e responsabilità esplicita dell'utente |
| Brand scambiato per autore | ruoli separati nel modello dati |
| Tre direzioni visuali cosmeticamente identiche | firma compositiva obbligatoria |
| Ambito troppo ampio al primo rilascio | costruire prima il Content/Evidence Core |
| Manifest troppo legato a Quote Card | mantenere oggetti condivisi e adapter separati |
| Falsa precisione della classifica | provenienza visibile e motivazione leggibile |

## 15. Roadmap proposta

### 0.1 — Evidence Core

Flusso conversazionale, modello dati, validatore e approvazione editoriale.

### 0.2 — Visual Brief e Proof Renderer

Tre archetipi, profilo brand minimo, a capo espliciti, SVG deterministico, conversione PNG opzionale e report QA.

### 0.3 — Production Renderer

Direzione approvata persistente, fitting sulle metriche reali del font, master 4:5, adattamenti compositivi 1:1 e 9:16, SVG e PNG con hash, QA finalizzabile dopo ispezione.

### 0.4 — Visual Review Studio

Editor locale desktop-first, preview prodotta dal renderer production, direzione e a capo per formato, scala limitata, posizione, logo, QA live e batch revisionato dall'agente.

### 0.5 — Editorial + Visual Studio

Scelta conversazionale ridotta a candidato e attribuzione, testo modificabile nell'editor e un solo comando di produzione `Genera`.

### 0.6 — User-Owned Editorial Studio

Tutti i campi editoriali modificabili, dichiarazioni registrate come responsabilità dell'utente, nessun downgrade automatico e generazione diretta dopo il gate tecnico.

### 0.6.1 — Manual Composition Controls

A capo manuali persistenti per formato ed enfasi di parole o locuzioni, anche quando attraversano una separazione di riga.

### 0.6.2 — Visual Text Styling

Editor visuale per selezionare e applicare grassetto, corsivo, sottolineato ed evidenziato; righe vuote persistenti come spazio verticale e dichiarazioni di trattamento/prova spostate nel ledger informativo.

### 0.6.7 — Branded Header Release

Scelta fra tutti i rapporti o un singolo output finale, consegna PNG-first e identità della testata coordinata con gli altri builder Vincos senza introdurre colori estranei alla UI.

### 0.6.8 — True Max Fit

Fitting tipografico condiviso fra anteprima, quality gate ed export: ogni composizione parte dalla massima dimensione sicura compatibile con guide e aree riservate; il controllo utente esprime una riduzione percentuale da quel massimo.

### 0.6.9 — Distinct Layout Core

Tre sistemi compositivi riconoscibili, selezioni multilinea affidabili e conservazione degli stili durante l'editing. Il testo resta di proprietà dell'utente: la resa può aumentarne l'impatto senza mutare il contenuto approvato.

### 0.6.10 — One-Step Generate

Una sola azione primaria `Genera` sostituisce invio e approvazione separati. Il server applica la bozza, esegue il quality gate, congela la prova e produce i formati selezionati nella stessa richiesta, mostrando i relativi link di download.

### 0.7 — Post Kit

Caption, alt text, provenance sheet e convenzioni di esportazione per canale.

### 1.0 — Shared Cores

Estrazione formale di Content/Evidence Core e Brand Identity Core per il riuso fra skill.

## 16. Decisioni aperte

1. Il manifest deve conservare il testo completo della fonte o soltanto locator, estratti e fingerprint? Default proposto: testo nel workspace di lavoro, estratti e fingerprint negli artefatti esportati.
2. Il profilo neutro deve essere incluso nella skill? Default proposto: sì, ma attivabile solo con scelta esplicita.
3. La provenance sheet deve essere pubblica o interna? Default proposto: interna, esportabile su richiesta.
4. Quando un testo `AI_GENERATED` può essere firmato dall'utente come autore? Default proposto: solo dopo approvazione esplicita della formulazione, registrata separatamente dall'attribuzione della fonte.
