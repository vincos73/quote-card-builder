# Visual Review Studio 0.4

Usare questo riferimento dopo `candidato_selezionato` quando la sessione può eseguire Python, aprire `127.0.0.1` e ricevere gli eventi del server locale.

## Principio

Trattare l'editor come superficie editoriale e visuale strutturata, non come canvas grafico libero. Rendere modificabili testo e formattazione inline, attribuzione, ruolo e presentazione; mostrare trattamento e prova come informazioni nel ledger inferiore. Mantenere protetti fonte osservata, brand e dimensioni dei formati.

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
    "attribution": {"label": "vincos.it", "role": "publisher"}
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
    "output_mode": "all"
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
- `attribution.label` e `attribution.role`: `speaker`, `author`, `publisher` o `none`;
- `direction`: `editorial`, `statement`, `contextual`;
- `content.styles`: al massimo 64 intervalli `{start, end, type}` sul testo normalizzato, con `type` fra `bold`, `italic`, `underline`, `highlight`, `accent`; gli intervalli possono attraversare gli a capo. `highlight` non è disponibile nella direzione `statement` / Poster: il controllo resta visibile ma disabilitato e un'eventuale evidenziazione applicata in un'altra direzione viene rimossa con un messaggio esplicito quando si passa a Poster;
- `content.emphasis`: campo legacy facoltativo; l'editor lo converte in `bold` quando apre un manifest precedente e poi lo svuota nel batch;
- `presentation.logo_mode`: `auto` o `hidden`;
- `presentation.graphic_mode`: `auto` applica il motivo fisso della direzione (`editorial` → linee di contorno, `statement` → moduli angolari discreti, `contextual` → campo puntinato); `hidden` lo rimuove;
- `presentation.output_mode`: `all`, `4x5`, `1x1` o `9x16`; controlla soltanto la consegna finale, non la disponibilità delle tab di anteprima;
- per ogni formato: `lines`, `text_scale` fra `0.80` e `1.00`, `vertical_position` fra `upper`, `center`, `lower`. I valori legacy fra `1.00` e `1.08` restano accettati in lettura, ma sono limitati a `1.00`.

`text_scale` è una percentuale del massimo sicuro, non una variazione rispetto a una dimensione nominale. Il renderer calcola prima il vero max-fit per ciascuna combinazione di formato, direzione e posizione, includendo larghezza, guide verticali e aree riservate a logo, attribuzione, metadati ed elemento grafico. `1.00` usa quel massimo; valori inferiori lo riducono. Preview, quality gate ed export devono condividere lo stesso calcolo e lo stesso valore effettivo.

Quando il testo cambia, sincronizzare le parole in tutti i formati, mantenendo autonomi gli a capo. Nel formato attivo preservare letteralmente ogni newline inserito dall'utente. Una riga vuota non aggiunge parole ma produce una riga intera di spazio verticale nel renderer. Durante la digitazione non riscrivere l'editor e non scartare newline terminali ancora privi della parola successiva. Non modificare automaticamente trattamento, prova o attribuzione.

La toolbar visuale applica o rimuove grassetto, corsivo, sottolineato, evidenziato e colore accento sulla selezione corrente, anche quando attraversa più righe o righe vuote. Prima di qualsiasi selezione manuale, una card senza stili né enfasi legacy mostra una firma per direzione: riga centrale in grassetto per Contorni, riga finale in accento per Moduli × Poster e riga centrale evidenziata per Campo. La prima selezione manuale sostituisce questa firma. Se cambiano le parole, riallineare gli intervalli rispetto alla porzione modificata: conservare quelli non coinvolti, spostare quelli successivi e rimuovere soltanto gli intervalli rimasti vuoti. Se cambiano soltanto gli a capo, conservarli senza variazioni.

La sessione deve esporre le capacità del font risolto. `bold_path` garantisce il grassetto reale; in sua assenza il renderer può dichiarare una resa sintetica quando esiste `regular_path`. `italic_path` è necessario per abilitare il corsivo. Se una faccia manca, mostrare vicino alla toolbar un messaggio con funzione interessata, causa e recupero; un controllo non disponibile resta focalizzabile per spiegare il problema ma non applica lo stile. Sottolineato ed evidenziato non richiedono facce aggiuntive.

Fonte osservata, brand e dimensioni restano immutabili nell'editor. Tutti i campi editoriali sono dichiarazioni dell'utente.

## Batch

```json
{
  "base_revision": 1,
  "action": "feedback",
  "text": "Un agente non si commuove per il tuo claim: confronta.",
  "transformation": "VERBATIM",
  "evidence_status": "VERIFIED",
  "attribution": {"label": "vincos.it", "role": "publisher"},
  "direction": "statement",
  "emphasis": "",
  "styles": [
    {"start": 44, "end": 54, "type": "highlight"}
  ],
  "presentation": {
    "logo_mode": "auto",
    "graphic_mode": "auto",
    "output_mode": "all"
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

L'interfaccia espone soltanto `Genera`. `POST /api/generate` applica nello stesso batch le modifiche correnti, può portare il manifest da `candidato_selezionato` a `contenuto_approvato`, rigenera le prove, esegue il QA tecnico, registra `prova_visuale_approvata` nel production manifest, produce un preflight locale e avvia il chatbot Codex. La risposta contiene i link autenticati ai formati prodotti e lo `request_id` del chatbot; `GET /api/agent-status` espone `queued`, `running`, `completed` o `failed` per il polling dell'interfaccia.

## Percorso locale

1. Creare una cartella di sessione esterna alla skill.
2. Avviare:

```text
python3 scripts/card_review_server.py <manifest.json> --session-dir <session-dir>
```

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
