# Urban — seconda grammatica nativa

Disponibile nei sorgenti candidati 1.10.1 / UI v1.60. Verificare la versione del servizio collegato prima di usare i nuovi campi.

Urban usa tipografia dominante, pannelli sfalsati, fasce oblique, filetti e segni di stampa. Il modello progetta la composizione; il renderer disegna geometria e testo editabili. Il colore proviene dai quattro ruoli della palette. La texture è parametrica e resta fuori dalle aree di citazione e autore. Le composizioni Urban geometriche esistenti restano disponibili.

**Urban · Xerox (beta)** è un’opzione distinta basata sull’asset fisso `urban-xerox-lime-v1.png`. È una prova artistica singola, riutilizzata senza una nuova chiamata ImageGen: mantiene i colori dell’immagine, mentre citazione, autore, logo e font restano elementi SVG modificabili. Il font iniziale è Barlow Condensed Black e può essere sostituito dall’utente. Il testo è dipinto in maiuscolo e, per impostazione predefinita, le ultime due parole hanno corpo ridotto; intervalli personalizzati di tipo `size` dell’utente prevalgono su questa enfasi. Il progetto e le basi personali conservano `artwork_id: "urban-xerox-lime-v1"`, non i byte dell’immagine: l’ID punta all’asset incluso nel runtime versionato. Il renderer incorpora l’immagine nello SVG e la adatta in modalità cover al formato selezionato, quindi il ritaglio può cambiare con il rapporto d’aspetto; la citazione può richiedere nuove righe o una revisione dell’area di lettura. La [prova visiva Xerox/lime](../assets/urban/urban-xerox-lime-reference.png) documenta l’art direction: è stata creata con ImageGen in questa chat, perché gli esempi originali citati non erano presenti nel workspace; non è una ricostruzione certificata degli originali. È stata provata con una frase breve. Per citazioni lunghe, rivedere la composizione e lo spazio di lettura prima di confermarla.

Per Nastri o per una scena Urban geometrica libera, usare `style`, `visual_grammar`, fino a tre `composition_candidates` progettate dal modello, la `composition` consigliata e `proposal_source: model`. Per la scelta esplicita Xerox usare una sola scena registrata, `xerox_composition()`, con `proposal_source: demo`: non è una scena progettata dal modello e non serve produrne tre. Nel web MCP 1.10.1 una richiesta `style: urban` / `visual_grammar: urban` senza scena o candidati apre questa composizione Xerox come default demo. Nel Visual Review Studio locale la galleria geometrica resta disponibile e Xerox è una scelta separata; le basi salvate conservano la composizione e il suo ID.

Esempio completo per Xerox, equivalente a `xerox_composition()`; `composition_candidates` contiene un solo elemento e `proposal_source` identifica onestamente l’origine demo:

```json
{
  "style": "urban",
  "visual_grammar": "urban",
  "composition": {
    "version": 1,
    "grammar": "urban",
    "id": "urban-xerox-lime",
    "artwork_id": "urban-xerox-lime-v1",
    "name": "Xerox / lime",
    "quote_box": {"x": 0.067, "y": 0.037, "width": 0.65, "height": 0.525},
    "author_box": {"x": 0.072, "y": 0.59, "width": 0.52, "height": 0.06},
    "logo_box": {"x": 0.072, "y": 0.665, "width": 0.2, "height": 0.035},
    "background_role": "background",
    "text_role": "text",
    "highlight_role": "accent",
    "blocks": [],
    "strips": [],
    "texture": {"seed": 0, "dots": 0, "scratches": 0, "color_role": "text"}
  },
  "composition_candidates": [
    {
      "version": 1,
      "grammar": "urban",
      "id": "urban-xerox-lime",
      "artwork_id": "urban-xerox-lime-v1",
      "name": "Xerox / lime",
      "quote_box": {"x": 0.067, "y": 0.037, "width": 0.65, "height": 0.525},
      "author_box": {"x": 0.072, "y": 0.59, "width": 0.52, "height": 0.06},
      "logo_box": {"x": 0.072, "y": 0.665, "width": 0.2, "height": 0.035},
      "background_role": "background",
      "text_role": "text",
      "highlight_role": "accent",
      "blocks": [],
      "strips": [],
      "texture": {"seed": 0, "dots": 0, "scratches": 0, "color_role": "text"}
    }
  ],
  "proposal_source": "demo"
}
```

Ogni scena contiene:

- `version: 1`, `grammar: urban`, `id` ASCII e `name` facoltativo;
- `artwork_id` facoltativo, solo con un ID registrato dal runtime, attualmente `urban-xerox-lime-v1`. Non accettare URL, percorsi file o dati base64; una scena non può introdurre immagini arbitrarie;
- `quote_box`, `author_box`, `logo_box`: `{x,y,width,height}` normalizzati fra 0 e 1, con aree positive dentro la card;
- `background_role`, `text_role`, `highlight_role` e facoltativamente `quote_backing_role`, `author_backing_role`: uno fra `primary`, `accent`, `background`, `text`;
- `blocks`: fino a 16 rettangoli o poligoni, ciascuno con `id`, `shape`, `color_role`, `x`, `y`, `width`, `height`; i poligoni hanno `points` con 3–12 vertici numerici;
- `strips`: fino a 12 fasce con `id`, `color_role`, `x1`, `y1`, `x2`, `y2`, `width`;
- `texture`: `{seed,dots,scratches,color_role}`, con seed 0–999999, fino a 160 punti e 24 graffi.

Le coordinate grafiche possono uscire dalla card entro -0.5–1.5 per creare ritagli ai bordi. I dati sono numerici: non sono ammessi markup SVG, URL, percorsi file o immagini arbitrarie nelle scene. L’unica eccezione per uno sfondo è un `artwork_id` registrato. Font e logo provengono invece dal brand kit.

Tre direzioni dimostrative mostrano pannello sfalsato, poster diagonale e composizione a colonne. Sono esempi per provare l’editor, non layout obbligatori per il modello. Le nuove proposte devono differire anche nello spazio di lettura, nei pieni/vuoti e nella gerarchia.

Le dimensioni assolute di citazione/autore e gli intervalli tipografici funzionano come in Nastri. Una dimensione manuale resta fissa. Avvisi di contrasto o overflow sono descrittivi e non bloccano l’export; dati invalidi e impossibilità di generare il file restano errori tecnici.

Nel locale la rasterizzazione nativa richiede Chromium/Playwright e attende font e immagini incorporati. Nel web il canvas esporta lo SVG corrente. Non sostituire silenziosamente i font con un backend diverso.
