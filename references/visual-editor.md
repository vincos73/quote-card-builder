# Visual Review Studio 0.4

Usare questo riferimento dopo `candidato_selezionato` quando la sessione può eseguire Python, aprire `127.0.0.1` e ricevere gli eventi del server locale.

## Principio

Trattare l'editor come superficie editoriale e visuale strutturata, non come canvas grafico libero. Rendere modificabili testo e formattazione inline, attribuzione e presentazione; mostrare trattamento e prova come informazioni nel ledger inferiore. Mantenere protetti fonte osservata, brand e dimensioni dei formati.

Il browser non scrive direttamente nel manifest. `Genera` invia un batch strutturato al server locale, che verifica revisione e invarianti, lo applica atomicamente, esegue il quality gate e prepara gli output selezionati. Dopo il rendering deterministico di preflight, il server attiva il chatbot Codex locale tramite un handoff path-scoped; il chatbot ricrea e verifica i PNG finali. Lo script separato resta disponibile come recupero per sessioni precedenti rimaste con un feedback pendente.

## Manifest di revisione

```json
{
  "schema_version": "0.4",
  "state": "candidato_selezionato",
  "revision": 1,
  "content": {
    "text": "Un agente non si commuove per il tuo claim: confronta.",
    "transformation": "VERBATIM",
    "evidence_status": "VERIFIED",
    "emphasis": "",
    "styles": [
      {"start": 44, "end": 54, "type": "highlight"}
    ],
    "attribution": {"label": "vincos.it", "role": "publisher"},
    "alt_text": ""
  },
  "direction": "statement",
  "formats": [
    {
      "id": "4x5",
      "width": 1440,
      "height": 1800,
      "lines": ["Un agente non si commuove", "", "per il tuo claim: confronta."],
      "text_scale": 1.0,
      "vertical_position": "center"
    }
  ],
  "presentation": {
    "logo_mode": "auto",
    "graphic_mode": "auto",
    "graphic_variant": "modules",
    "output_mode": "4x5"
  },
  "brand": {},
  "source": {},
  "output": {"basename": "quote-card"}
}
```

Includere uno o più formati fra `4x5`, `1x1` e `9x16`. Usare rispettivamente i rapporti 4:5, 1:1 e 9:16.

## Campi modificabili

- `text`: testo corrente ricostruito dalle righe del formato attivo;
- `transformation` ed `evidence_status`: dichiarazioni dell'utente conservate nel batch e mostrate come informazioni nel ledger, senza pulsanti di modifica nell'editor;
- `attribution.label`: unico campo editabile per l'attribuzione. `attribution.role` non ha un controllo in UI (non produce alcun trattamento visivo diverso sulla card): il batch lo deriva automaticamente come `author` quando `label` non è vuota, `none` quando è vuota;
- `content.alt_text`: descrizione accessibile, al più 400 caratteri. Il flusso principale mostra soltanto `Alt text automatico`; il campo di sostituzione vive nel pannello avanzato `Accessibilità`, richiuso per default. Vuoto mostra come segnaposto la stessa descrizione automatica (testo, attribuzione e fonte quando presente) che finisce nel `<desc>` dell'SVG e nella scheda di contatto. Un valore digitato dall'utente la sostituisce integralmente ed è quello che il production pack registra in `accessibility.alt_text` con `declared_by: user`; vuoto resta `declared_by: auto`;
- `direction`: `editorial`, `statement`, `contextual`;
- `content.styles`: al massimo 64 intervalli `{start, end, type}` sul testo normalizzato, con `type` fra `bold`, `italic`, `underline`, `highlight`, `accent`, `outline`; gli intervalli possono attraversare gli a capo. `highlight` è disponibile in tutte le direzioni, inclusa `statement` / Poster: la fascia va misurata con le metriche del font in grassetto (il Poster renderizza sempre in grassetto), reali quando disponibili o con un fattore di compensazione altrimenti, per non produrre una fascia più corta delle parole coperte. `highlight`, `accent` e `outline` decidono tutti e tre di cosa è riempito un glifo e restano quindi mutuamente esclusivi sullo stesso intervallo: applicarne uno rimuove l'altro. `outline` disegna glifi cavi (`fill="none"` più `stroke`) nel colore d'inchiostro che il testo avrebbe comunque avuto, con spessore proporzionale alla dimensione della riga che traccia: è un cambio di forma, mai di palette, e non promuove una riga Poster a enfasi;
- `content.emphasis`: campo legacy facoltativo; l'editor lo converte in `bold` quando apre un manifest precedente e poi lo svuota nel batch;
- `presentation.logo_mode`: `auto` o `hidden`;
- `presentation.graphic_mode`: `auto` mostra il motivo selezionato; `hidden` lo rimuove senza cambiare stile;
- `presentation.graphic_variant`: motivo contestuale alla direzione. `editorial` accetta `default` (Contours) o `rhythm_lines` (Rhythm Lines); `statement` accetta `default` (Echo Rings) o `modules` (Modules); `contextual` accetta `default` (Dot Grid) o `route_map` (Route Map). Se assente vale `default`; una variante appartenente a un'altra direzione è rifiutata;
- `presentation.output_mode`: `all`, `4x5`, `1x1` o `9x16`; controlla soltanto la consegna finale, non la disponibilità delle tab di anteprima. Senza una scelta esplicita, il default è il formato attivo (il primo elenco in `formats`), non `all`: l'utente lavora tipicamente su un solo rapporto e non va costretto a scartare gli altri due. `all` non consegna più file separati: `Genera` bundla i formati prodotti in un unico `.zip` con la scheda di contatto; un formato singolo resta un file singolo;
- per ogni formato: `lines`, `text_scale` fra `0.80` e `1.00`, `vertical_position` fra `upper`, `center`, `lower`. I valori legacy fra `1.00` e `1.08` restano accettati in lettura, ma sono limitati a `1.00`.

`text_scale` è una percentuale del massimo sicuro, non una variazione rispetto a una dimensione nominale. Il renderer calcola prima il vero max-fit per ciascuna combinazione di formato, direzione e posizione, includendo larghezza, guide verticali e aree riservate a logo, attribuzione, metadati ed elemento grafico. `1.00` usa quel massimo; valori inferiori lo riducono. Preview, quality gate ed export devono condividere lo stesso calcolo e lo stesso valore effettivo.

Quando il testo cambia, sincronizzare parole e a capo in tutti i formati: cambiare rapporto non ricompone mai le righe scelte dall'utente, cambia soltanto la dimensione del carattere adattata al formato. Preservare letteralmente ogni newline inserito dall'utente.

Il riequilibrio degli a capo resta un'azione esplicita, offerta con un solo comando (`⌘↵` o il pulsante nella riga dell'etichetta) e annullabile come qualsiasi altra modifica: calcola la divisione sulla lunghezza visiva delle parole, penalizza le righe di una sola parola e tratta il numero di righe corrente come preferenza debole. Non deve mai scattare da solo dopo una modifica testuale. Poiché conserva le stesse parole nello stesso ordine, gli intervalli di formattazione restano validi senza riallineamento; le righe vuote vengono assorbite dal nuovo assetto. Una riga vuota non aggiunge parole ma produce una riga intera di spazio verticale nel renderer. Durante la digitazione non riscrivere l'editor e non scartare newline terminali ancora privi della parola successiva. Non modificare automaticamente trattamento, prova o attribuzione.

La toolbar visuale applica o rimuove grassetto, corsivo e sottolineato sulla selezione corrente, anche quando attraversa più righe o righe vuote; i tre trattamenti di riempimento (accento, evidenziato, contorno) stanno in un unico controllo a stati che li percorre in quest'ordine e torna al testo semplice, così la toolbar resta a quattro pulsanti invece di sei. Restano disponibili le scorciatoie dirette `⌘B`, `⌘I`, `⌘U`, `⌘⇧A`, `⌘⇧H` e `⌘⇧O`.

Applicare un trattamento non deve costare all'utente la selezione: l'editor ricostruisce il proprio markup a ogni modifica, quindi va riancorata la selezione sugli offset canonici subito dopo il ridisegno, altrimenti un secondo trattamento sulle stesse parole richiede di riselezionarle. Per la stessa ragione l'editor possiede la propria cronologia di annullamento su righe e stili, con `⌘Z` e `⌘⇧Z`: la riscrittura del markup azzera quella nativa del browser, che quindi non può essere lasciata al browser.

Prima di qualsiasi selezione manuale, una card senza stili né enfasi legacy mostra una firma per direzione: riga centrale in grassetto per Contorni, riga finale in accento per Moduli × Poster e riga centrale evidenziata per Campo. La prima selezione manuale sostituisce questa firma. Se cambiano le parole, riallineare gli intervalli rispetto alla porzione modificata: conservare quelli non coinvolti, spostare quelli successivi e rimuovere soltanto gli intervalli rimasti vuoti. Se cambiano soltanto gli a capo, conservarli senza variazioni.

La sessione deve esporre le capacità del font risolto. `bold_path` garantisce il grassetto reale; in sua assenza il renderer può dichiarare una resa sintetica quando esiste `regular_path`. `italic_path` è necessario per abilitare il corsivo. Se una faccia manca, mostrare vicino alla toolbar un messaggio con funzione interessata, causa e recupero; un controllo non disponibile resta focalizzabile per spiegare il problema ma non applica lo stile. Sottolineato ed evidenziato non richiedono facce aggiuntive.

Fonte osservata, brand e dimensioni restano immutabili nell'editor. Tutti i campi editoriali sono dichiarazioni dell'utente.

Il pannello Palette può salvare il brand immutabile corrente come profilo locale riutilizzabile. `GET /api/profiles` restituisce nomi, palette, font, stato degli asset, filename di esportazione e l'eventuale profilo coincidente con il brand corrente. `POST /api/profiles` accetta soltanto `{ "name": "..." }`: il server prende il brand dal manifest validato, risolve come assoluti gli eventuali path relativi di font e logo e lo salva atomicamente in `~/.quote-card-builder/profiles.json`. Dopo il salvataggio, `GET /api/profiles/export?profile_id=<id>` scarica `<nome-brand>-quote-card-brand.json`; il file contiene soltanto `profile_type`, `schema_version`, nome del profilo e brand, senza ID, fingerprint, date o contenuti editoriali. Il client non può inviare o modificare il contenuto del brand attraverso queste API. Citazione, fonte, attribuzione e alt text non entrano mai nell'archivio o nell'export.

Prima di costruire un nuovo manifest, elencare l'archivio con `python3 scripts/brand_profiles.py list`; mostrare i profili disponibili e usarne uno soltanto dopo una scelta esplicita. `python3 scripts/brand_profiles.py show <id>` restituisce il brand completo. Un JSON allegato viene importato conversazionalmente: eseguire `python3 scripts/brand_profiles.py validate <profilo.json>`, mostrare il riepilogo e applicarlo soltanto dopo approvazione. Il validatore accetta esclusivamente `profile_type: quote-card-brand`, `schema_version: "1.0"`, `name` e `brand`; risolve i path relativi rispetto al JSON e segnala gli asset mancanti. Non aggiungere un file picker nell'editor, perché il brand deve essere risolto prima del manifest. Se `assets.ready` è falso, chiedere asset aggiornati o un altro profilo invece di usare riferimenti mancanti.

## Batch

```json
{
  "base_revision": 1,
  "action": "feedback",
  "text": "Un agente non si commuove per il tuo claim: confronta.",
  "transformation": "VERBATIM",
  "evidence_status": "VERIFIED",
  "attribution": {"label": "vincos.it", "role": "publisher"},
  "alt_text": "",
  "direction": "statement",
  "emphasis": "",
  "styles": [
    {"start": 44, "end": 54, "type": "highlight"}
  ],
  "presentation": {
    "logo_mode": "auto",
    "graphic_mode": "auto",
    "graphic_variant": "modules",
    "output_mode": "4x5"
  },
  "formats": [
    {
      "id": "4x5",
      "width": 1440,
      "height": 1800,
      "lines": ["Un agente non si commuove", "", "per il tuo claim: confronta."],
      "text_scale": 1.0,
      "vertical_position": "center"
    }
  ],
  "overall_note": ""
}
```

Il draft inviato a `/api/preview` e `/api/generate` conserva `width` e `height` perché il server possa verificare che l'identità del formato non sia cambiata. Nel `feedback.json` persistito, il server elimina questi due campi immutabili e registra `editorial_responsibility: user` e `content.declared_by: user`.

L'interfaccia espone soltanto `Genera`. `POST /api/generate` applica nello stesso batch le modifiche correnti, può portare il manifest da `candidato_selezionato` a `contenuto_approvato`, rigenera le prove, esegue il QA tecnico, registra `prova_visuale_approvata` nel production manifest, produce un preflight locale e avvia il chatbot Codex. La risposta contiene i link autenticati agli output prodotti (un unico `.zip` quando `output_mode` produce più di un formato, un singolo PNG/SVG altrimenti) e lo `request_id` del chatbot; `GET /api/agent-status` espone `queued`, `running`, `completed` o `failed` per il polling dell'interfaccia.

`POST /api/preview` include nella risposta `declaration.alt_text_suggestion` (la descrizione automatica corrente, per il segnaposto del campo) e `score`: un riepilogo `{overall, categories: {contrast, fit, structure}}` da 0 a 100 derivato dagli stessi controlli del quality gate — non un giudizio ulteriore — pensato per il ledger inferiore.

Dopo una generazione riuscita, l'editor deve separare esito e azione: mostra `PNG generato` o `Pacchetto generato`, nome file, percorso locale assoluto e link autenticato all'artefatto. Se il server è stato avviato con `--return-thread-id`, il pulsante primario diventa `Torna alla chat` e apre il deep link `codex://threads/<thread-id>` costruito soltanto da un identificatore validato; non accetta un URL arbitrario dal manifest o dal client. Senza task nota, il pulsante diventa `Chiudi editor`, tenta di chiudere la scheda locale e, se il browser impedisce la chiusura automatica, comunica di chiuderla manualmente mantenendo visibile il percorso. Una modifica successiva alla composizione rimuove lo stato di consegna precedente e ripristina `Genera`, senza far riapparire l'output obsoleto al polling successivo.

## Percorso locale

1. Creare una cartella di sessione esterna alla skill.
2. Avviare:

```text
python3 scripts/card_review_server.py <manifest.json> --session-dir <session-dir> [--return-thread-id <thread-id>]
```

`--profile-store <path>` sostituisce l'archivio profili soltanto per test o ambienti portabili; il percorso utente predefinito resta separato dalla skill.

3. Aprire l'URL `127.0.0.1` restituito dalla prima riga JSON.
4. Mantenere attivo il processo e attendere l'evento senza intervalli superiori a 50 secondi.
5. Il server applica il batch validato nella stessa richiesta. Solo per recuperare un feedback pendente lasciato da una versione precedente, eseguire:

```text
python3 scripts/apply_card_review.py <manifest.json> <session-dir>/feedback.json --session-dir <session-dir>
```

6. Interpretare `overall_note`, ripetere i controlli e far ricaricare automaticamente l'editor.
7. Chiudere il server alla fine della revisione.

## Sicurezza e resilienza

- Vincolare il server a `127.0.0.1` e richiedere token casuale e Host locale.
- Servire soltanto asset inclusi e asset esplicitamente risolti dal manifest.
- Applicare CSP, `no-store`, `nosniff` e `frame-ancestors 'none'`.
- Non riclassificare o correggere automaticamente le dichiarazioni editoriali dell'utente.
- Limitare la dimensione dei batch e rifiutare un secondo batch pendente.
- Legare la sessione al percorso assoluto del manifest.
- Rifiutare batch con `base_revision` superata.
- Scrivere feedback, stato e manifest in modo atomico e conservare un backup prima dell'applicazione.
- Conservare la bozza nel browser; se la revisione server cambia mentre esistono modifiche locali, bloccare l'invio e richiedere il ricarico.

## Fallback

Quando Python, browser locale o ricezione degli eventi non sono disponibili, usare la revisione conversazionale. Mostrare le stesse direzioni e gli stessi controlli in forma compatta, senza dichiarare che l'editor è stato aperto.
