# Quote manifest 0.1

Usare questo riferimento quando bisogna salvare, validare o passare il lavoro a un adapter visuale.

## Struttura

```json
{
  "schema_version": "0.1",
  "state": "candidati_pronti",
  "source": {
    "id": "source-1",
    "kind": "text",
    "title": "Titolo opzionale",
    "locator": "https://example.com/opzionale",
    "text": "Testo disponibile nella sessione"
  },
  "candidates": [
    {
      "id": "q1",
      "text": "Frase candidata",
      "transformation": "VERBATIM",
      "evidence_status": "VERIFIED",
      "evidence": [
        {
          "start": 0,
          "end": 16,
          "excerpt": "Frase candidata",
          "locator": "paragrafo 1"
        }
      ],
      "attribution": {
        "label": "Nome opzionale",
        "role": "author",
        "source": "byline opzionale",
        "authorship_approved": false
      },
      "use_quotation_marks": true,
      "ranking": {
        "score": 80,
        "reason": "Motivazione breve."
      },
      "warnings": []
    }
  ],
  "selection": {
    "candidate_id": "q1",
    "reason": "Motivazione della scelta.",
    "content_approved": false
  }
}
```

## Campi obbligatori

- root: `schema_version`, `state`, `source`, `candidates`;
- source: `id`, `kind`, `text`;
- candidate: `id`, `text`, `transformation`, `evidence_status`, `evidence`, `attribution`, `use_quotation_marks`, `ranking`;
- attribution: `role`; `label` può essere vuoto solo con `role: none`;
- ranking: `score`, `reason`.

`selection` è obbligatorio da `contenuto_approvato` in poi.

Quando è disponibile Visual Review Studio 0.6, dopo la scelta del candidato usare `candidato_selezionato` nel manifest editor 0.4. `Genera` salva le dichiarazioni dell'utente, registra la prova corrente come approvata dopo il gate tecnico e produce i formati selezionati nello stesso batch. Registrare `declared_by: user` per distinguere queste scelte dai dati osservati nella fonte.

## Stati ammessi nel core 0.1

- `bozza`
- `candidati_pronti`
- `contenuto_approvato`

Gli stati visuali appartengono al manifest esteso del futuro Visual Brief Adapter. Il validatore 0.1 li rifiuta per evitare che un manifest soltanto editoriale dichiari una card renderizzata o consegnata.

## Evidence span

Gli offset usano indici Python sul testo Unicode. Deve valere:

```python
source[span["start"]:span["end"]] == span["excerpt"]
```

Gli evidence span descrivono ciò che la skill ha osservato nella fonte e devono restare tecnicamente validi quando presenti. Non usarli per sovrascrivere o bloccare le dichiarazioni editoriali dell'utente.

## Persistenza

Durante il lavoro il manifest può contenere il testo completo per consentire la validazione. Negli artefatti esportati pubblicamente preferire fingerprint, locator ed estratti minimi, salvo richiesta diversa.
