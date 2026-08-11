# Modello di provenienza e dichiarazione

Leggere questo riferimento prima di classificare, approvare o renderizzare una frase.

## Principio

La skill distingue ciò che ha osservato nella fonte da ciò che l'utente dichiara. Può proporre una classificazione e mostrare incongruenze, ma non certifica il contenuto e non sostituisce le scelte dell'utente. L'utente può modificare tutti i campi editoriali ed è il garante finale.

Registrare `declared_by: user` quando l'utente salva o approva le proprie scelte. Non riscrivere automaticamente testo, trasformazione, prova, attribuzione o virgolette.

## Due assi descrittivi

### Trasformazione

- `VERBATIM`: dichiarato come coincidente con un passaggio della fonte.
- `EDITED`: dichiarato come derivato dalla fonte con tagli o modifiche.
- `PARAPHRASE`: dichiarato come formulazione diversa della stessa idea.
- `AI_GENERATED`: dichiarato come testo nuovo prodotto a partire da un'idea o un brief.

### Stato della prova

- `VERIFIED`: l'utente dichiara che testo e attribuzione sono verificati.
- `USER_SUPPLIED`: testo o attribuzione sono stati forniti dall'utente.
- `UNVERIFIED`: la verifica non è disponibile o non è stata completata.
- `CONFLICT`: l'utente vuole registrare una discordanza o un conflitto noto.

Queste etichette sono dati editoriali, non permessi. Ogni combinazione è salvabile e renderizzabile.

## Attribuzione

- `speaker`: persona indicata come voce della frase.
- `author`: autore indicato dall'utente.
- `publisher`: soggetto che pubblica la card.
- `none`: nessuna attribuzione visibile.

Il campo `label` è obbligatorio solo quando il ruolo non è `none`. La skill può mostrare l'attribuzione osservata nella fonte come riferimento separato, ma non deve usarla per sovrascrivere quella scelta dall'utente.

## Segnalazioni consultive

È utile avvisare, senza bloccare o correggere automaticamente, quando:

- `VERBATIM + VERIFIED` non coincide con il passaggio osservato;
- una `PARAPHRASE` personale usa virgolette;
- `AI_GENERATED` usa `speaker`;
- lo stato è `CONFLICT`;
- una modifica cambia negazione, cautela, condizione, numero, soggetto o grado di certezza;
- autore, speaker e publisher potrebbero essere confusi.

Le segnalazioni devono essere presentate come osservazioni della skill. L'azione `Approva` resta disponibile se i controlli strutturali e visuali sono superati.

## Controlli bloccanti

Bloccare soltanto problemi che impediscono un artefatto valido o leggibile:

- testo vuoto o oltre il limite tecnico;
- enum o tipi non riconosciuti;
- attribuzione senza etichetta quando il ruolo la richiede;
- a capo che non ricostruiscono il testo corrente;
- enfasi assente dal testo;
- formati, scale o dimensioni non validi;
- overflow, contrasto insufficiente, asset mancanti o SVG non valido;
- revisione concorrente o batch non applicabile in sicurezza.

## Classifica

Usare le etichette e la provenienza come contesto consultivo. Valutare:

- chiarezza autonoma: 0–25;
- rilevanza: 0–20;
- specificità e memorabilità: 0–20;
- concisione: 0–15;
- ritmo e potenziale tipografico: 0–10;
- potenziale visuale: 0–10.

Lo score massimo è 100. Motivare la raccomandazione in linguaggio naturale; non mostrare decimali o falsa precisione.
