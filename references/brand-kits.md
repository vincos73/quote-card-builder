# Brand kit portabile

Sorgenti candidati 1.10.0. Un kit ha `schema: qcb-brand-kit`, `schema_version: 1`, `name`, `colors` e, facoltativamente, `font` e `logo`.

`colors` contiene esattamente `primary`, `accent`, `background`, `text` in formato `#RRGGBB`. `font` contiene `family` e gli asset facoltativi `regular`, `bold`, `italic`, `bold_italic`. Ogni asset usa `{mime_type,data_base64}`. I font ammessi sono TTF, OTF, WOFF e WOFF2; il logo può essere PNG, JPEG, WebP o SVG con elementi vettoriali consentiti. Il kit non contiene percorsi locali né URL remoti.

Il web permette di caricare font e logo, applicarli alla card, mostrare/nascondere il logo, importare o scaricare il kit. Palette e asset restano distinti: cambiare colore conserva font e logo; cancellare gli asset conserva la palette. Basi e progetti esportati incorporano il kit scelto. Il locale incorpora gli asset referenziati quando esporta e materializza quelli importati nella directory della sessione.

Ogni asset può avere fino a 4 MiB; il JSON del kit fino a 8 MiB. Il server verifica base64, firma e struttura dei font, decodifica le immagini raster e controlla gli SVG contro elementi attivi, risorse esterne ed entità XML. Le risorse del rendering web vengono create in una directory temporanea e rimosse al termine della richiesta.

I file del brand restano nello stato completo dell’editor e nei JSON. Il contesto del modello contiene soltanto `brand_kit_attached` e una descrizione compatta del kit. Una modifica dalla chat che conserva gli asset viene validata dal server e applicata alla bozza corrente nell’editor, che genera la nuova preview con quei file. Non viene prodotta una preview con un font sostitutivo. Un editor appena aperto deve recuperare il progetto completo per applicare questo tipo di aggiornamento.

Quando manca un kit, Nastri e Urban usano Barlow incorporato; il trasferimento verso il locale risolve lo stesso font dal pacchetto. Gli stili precedenti conservano Arial. Il caricamento web offre un logo; l’export locale conserva anche varianti distinte chiara/scura attraverso il campo facoltativo `logo_variants`. Sostituire il logo nel web sostituisce la coppia con il nuovo asset. Una famiglia personalizzata richiede il file del font regolare per una resa portabile.
