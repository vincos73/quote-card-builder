# Urban — seconda grammatica nativa

Disponibile nei sorgenti candidati 1.9.0 / UI v1.59. Verificare la versione del servizio collegato prima di usare i nuovi campi.

Urban usa tipografia dominante, pannelli sfalsati, fasce oblique, filetti e segni di stampa. Il modello progetta la composizione; il renderer disegna geometria e testo editabili. Il colore proviene dai quattro ruoli della palette. La texture è parametrica e resta fuori dalle aree di citazione e autore.

Per aprire una card usare `style: urban`, `visual_grammar: urban`, `composition`, fino a tre `composition_candidates` e `proposal_source: model`. Nel locale usare `presentation.visual_grammar: urban`. Il formato scelto viene renderizzato dalla medesima scena, senza ritaglio di una preview diversa.

Ogni scena contiene:

- `version: 1`, `grammar: urban`, `id` ASCII e `name` facoltativo;
- `quote_box`, `author_box`, `logo_box`: `{x,y,width,height}` normalizzati fra 0 e 1, con aree positive dentro la card;
- `background_role`, `text_role`, `highlight_role` e facoltativamente `quote_backing_role`, `author_backing_role`: uno fra `primary`, `accent`, `background`, `text`;
- `blocks`: fino a 16 rettangoli o poligoni, ciascuno con `id`, `shape`, `color_role`, `x`, `y`, `width`, `height`; i poligoni hanno `points` con 3–12 vertici numerici;
- `strips`: fino a 12 fasce con `id`, `color_role`, `x1`, `y1`, `x2`, `y2`, `width`;
- `texture`: `{seed,dots,scratches,color_role}`, con seed 0–999999, fino a 160 punti e 24 graffi.

Le coordinate grafiche possono uscire dalla card entro -0.5–1.5 per creare ritagli ai bordi. I dati sono numerici: non sono ammessi markup SVG, URL o immagini arbitrarie nelle scene. Font e logo provengono invece dal brand kit.

Tre direzioni dimostrative mostrano pannello sfalsato, poster diagonale e composizione a colonne. Sono esempi per provare l’editor, non layout obbligatori per il modello. Le nuove proposte devono differire anche nello spazio di lettura, nei pieni/vuoti e nella gerarchia.

Le dimensioni assolute di citazione/autore e gli intervalli tipografici funzionano come in Nastri. Una dimensione manuale resta fissa. Avvisi di contrasto o overflow sono descrittivi e non bloccano l’export; dati invalidi e impossibilità di generare il file restano errori tecnici.

Nel locale la rasterizzazione nativa richiede Chromium/Playwright e attende font e immagini incorporati. Nel web il canvas esporta lo SVG corrente. Non sostituire silenziosamente i font con un backend diverso.
