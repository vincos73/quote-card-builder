# Visual manifest 0.2

Usare questo riferimento dopo l'approvazione editoriale, prima di generare una prova visuale.

## Scopo

Il visual manifest registra il contenuto dichiarato e approvato dall'utente, poi aggiunge linee, direzione compositiva, brand e formato. Il renderer tratta quel testo come immutabile durante il fitting, senza certificare le dichiarazioni editoriali.

## Struttura minima

```json
{
  "schema_version": "0.2",
  "state": "contenuto_approvato",
  "content": {
    "text": "Un agente non si commuove per il tuo claim: confronta.",
    "lines": [
      "Un agente non si commuove",
      "",
      "per il tuo claim: confronta."
    ],
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
  "canvas": {
    "width": 1440,
    "height": 1800
  },
  "direction": "statement",
  "presentation": {
    "graphic_mode": "auto"
  },
  "brand": {
    "name": "Nome del brand",
    "colors": {
      "primary": "#072743",
      "accent": "#E3F4FF",
      "background": "#FEFDFB",
      "text": "#323232"
    },
    "font": {
      "family": "Barlow",
      "regular_path": "/percorso/Barlow-Regular.ttf",
      "medium_path": "/percorso/Barlow-Medium.ttf",
      "bold_path": "/percorso/Barlow-Bold.ttf",
      "italic_path": "/percorso/Barlow-Italic.ttf"
    },
    "logo": {
      "dark_path": "/percorso/logo-navy.svg",
      "light_path": "/percorso/logo-white.svg"
    }
  },
  "source": {
    "label": "Titolo breve opzionale",
    "title": "Titolo opzionale",
    "locator": "URL o riferimento opzionale"
  },
  "output": {
    "basename": "quote-card"
  }
}
```

## Invarianti

1. Accettare soltanto lo stato `contenuto_approvato` per una prova.
2. Ricostruire `content.text` unendo `content.lines` con spazi e normalizzando soltanto gli spazi. Rifiutare qualsiasi differenza di parole, segni o maiuscole.
3. Consentire da 1 a 6 linee e almeno una riga di testo; una stringa vuota è una riga intera di spazio verticale e non modifica la ricostruzione del testo.
4. Validare `styles`, quando presente, come lista di intervalli sul testo con tipo `bold`, `italic`, `underline` o `highlight`. Accettare `emphasis` come compatibilità legacy soltanto se compare esattamente nel testo.
5. Rifiutare `evidence_status: CONFLICT`.
6. Accettare le combinazioni editoriali dichiarate dall'utente; verificare soltanto tipi, enum e campi obbligatori.
7. Richiedere un canvas 4:5; il renderer 0.2 non produce ancora altri rapporti.
8. Usare soltanto colori esadecimali `#RRGGBB`.
9. Verificare contrasto minimo 4,5:1 per testo, attribuzione ed enfasi.
10. Trattare font e logo come asset del profilo, non della skill. Non incorporare un brand predefinito.
11. Caricare `italic_path` per il corsivo reale e `bold_path` per il grassetto reale. Se mancano, non presentare la resa come garantita: dichiarare l'eventuale sintesi o disabilitare il trattamento con un messaggio di recupero.

## Direzioni

- `editorial`: fondo chiaro, allineamento a sinistra, molto spazio, enfasi tipografica sobria.
- `statement`: fondo primario, testo grande, ultima unità semantica in accento.
- `contextual`: fondo accento, pannello chiaro, metadati e segnale documentale della fonte.

Le direzioni cambiano struttura, non soltanto palette. Il testo, l'attribuzione e gli a capo restano identici.

Ogni direzione include un motivo evergreen fisso: contorni per `editorial`, moduli per `statement`, campo per `contextual`. `presentation.graphic_mode` può essere `auto` (predefinito) oppure `hidden`; non sono previste sostituzioni, posizione, scala, colore o opacità manuali.

## Output

Il renderer genera sempre SVG. Genera PNG soltanto quando è disponibile un convertitore dichiarato. La prova non cambia automaticamente lo stato del manifest: l'utente deve approvarla esplicitamente.

Quando `source.title` è troppo lungo per la resa a dimensione feed, fornire un `source.label` breve e fedele. Non troncare silenziosamente il titolo nel renderer.
