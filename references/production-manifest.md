# Production manifest 0.3

Usare questo riferimento soltanto dopo l'approvazione esplicita di una prova visuale.

## Scopo

Il production manifest congela contenuto, direzione e brand approvati, poi descrive gli adattamenti compositivi richiesti per ogni rapporto. Ogni formato conserva esattamente le stesse parole, ma può avere a capo diversi. Nessun output è un ritaglio di un altro.

## Struttura minima

```json
{
  "schema_version": "0.3",
  "state": "prova_visuale_approvata",
  "approval": {
    "direction": "statement",
    "proof_path": "quote-card-statement.png",
    "content_sha256": "digest SHA-256 del testo approvato",
    "approved_by": "user",
    "approved_at": "2026-08-10"
  },
  "content": {
    "text": "Un agente non si commuove per il tuo claim: confronta.",
    "transformation": "VERBATIM",
    "evidence_status": "VERIFIED",
    "use_quotation_marks": true,
    "emphasis": "",
    "styles": [
      {"start": 44, "end": 54, "type": "highlight"}
    ],
    "attribution": {
      "label": "vincos.it",
      "role": "publisher"
    }
  },
  "formats": [
    {
      "id": "4x5",
      "width": 1440,
      "height": 1800,
      "lines": ["Un agente non si commuove", "", "per il tuo claim: confronta."]
    },
    {
      "id": "1x1",
      "width": 1080,
      "height": 1080,
      "lines": ["Un agente non si commuove", "per il tuo claim:", "confronta."]
    },
    {
      "id": "9x16",
      "width": 1080,
      "height": 1920,
      "lines": ["Un agente", "non si commuove", "per il tuo claim:", "confronta."]
    }
  ],
  "presentation": {
    "logo_mode": "auto",
    "show_quotation_marks": true,
    "graphic_mode": "auto",
    "output_mode": "all"
  },
  "brand": {},
  "source": {},
  "output": {
    "basename": "quote-card"
  }
}
```

`brand`, `source` e i campi editoriali di `content` hanno lo stesso significato del visual manifest 0.2. Il profilo font può includere `regular_path`, `medium_path`, `bold_path` e `italic_path`; gli stili approvati devono conservare la stessa disponibilità tipografica della prova.

## Invarianti

1. Accettare soltanto `schema_version: 0.3` e `state: prova_visuale_approvata`.
2. Richiedere una direzione approvata fra `editorial`, `statement` e `contextual`.
3. Verificare che `approval.content_sha256` coincida con il testo corrente.
4. Richiedere un file di prova esistente: l'approvazione non può riferirsi a una prova astratta.
5. Accettare soltanto gli identificatori `4x5`, `1x1` e `9x16`, senza duplicati.
6. Verificare rispettivamente i rapporti 4:5, 1:1 e 9:16 con tolleranza tecnica minima.
7. Ricostruire `content.text` dalle linee di ogni formato. Rifiutare qualsiasi differenza di parole, segni o maiuscole.
8. Consentire da 1 a 6 linee per formato, con almeno una riga di testo; ogni stringa vuota rappresenta una riga intera di spazio verticale.
9. Eseguire un vero max-fit per ogni formato, direzione e posizione: il testo deve arrivare alla prima guida o area riservata senza superarla. Includere logo, attribuzione, metadati ed elemento grafico nei vincoli; usare le metriche reali del font quando Pillow è disponibile e dichiarare esplicitamente il fallback euristico. `text_scale` fra `0.80` e `1.00` è una riduzione dal massimo.
10. Generare ogni formato dalla composizione approvata, non ridimensionando o ritagliando un PNG precedente.
11. Incorporare font e logo negli SVG e produrre hash SHA-256 per tutti gli artefatti.
12. Mantenere lo stato `qa` finché tutte le immagini non sono state ispezionate visivamente.
13. Conservare `presentation.graphic_mode` dalla prova approvata: `auto` usa il motivo fisso della direzione e `hidden` lo rimuove in tutti i formati.
14. Con `presentation.output_mode: all`, includere esattamente `4x5`, `1x1` e `9x16`; con un rapporto specifico, includere soltanto quel formato.

## Output

Il renderer genera per ogni formato richiesto:

- PNG come artefatto di consegna predefinito;
- SVG soltanto come intermedio tecnico, eliminato dopo una conversione PNG riuscita, oppure come fallback quando il convertitore non è disponibile;
- contact sheet HTML;
- report `*-production-qa.json` con dimensione effettiva, dimensione massima, fitting, contrasto e hash.

Dopo l'ispezione visuale, usare `scripts/finalize_quote_card_pack.py <qa.json> --all-formats --reviewer <nome>`. Il finalizzatore ricontrolla gli hash e porta il report a `status: passed`, `state: consegnato`.
