# Quote Card Builder

Skill per Codex che trasforma frasi, testi, URL, documenti e idee in quote card verificabili e coerenti con un brand approvato.

Versione corrente: **0.7.0 — Cross-Format Consistency**

## Caratteristiche

- provenienza, trasformazione e stato della prova mantenuti separati;
- tre direzioni visuali autonome: Contorni, Manifesto Moduli × Poster e Campo;
- editor locale con a capo manuali, righe vuote, grassetto, corsivo, sottolineato, evidenziato e colore accento;
- testo, a capo manuali e formattazioni restano identici tra `4:5`, `1:1` e `9:16`: cambiare formato adatta solo la dimensione carattere, mai la composizione del testo;
- Arial come baseline neutra su macOS e Windows, con trattamenti iniziali distinti per Contorni, Moduli × Poster e Campo;
- pannello non editabile con i colori del profilo applicato alla card, con campioni, codici HEX e uso previsto;
- selezioni multilinea affidabili e riallineamento degli stili dopo le modifiche al testo;
- vero max-fit per formato, direzione e posizione, con scala utente dall'80% al 100% del massimo sicuro;
- composizioni indipendenti `4:5`, `1:1` e `9:16`;
- consegna di tutti i rapporti oppure di un singolo formato scelto dall’utente;
- un’unica CTA `Genera` per salvare, validare e consegnare gli output al chatbot Codex locale;
- PNG come output predefinito, con SVG conservato soltanto come fallback tecnico;
- controlli tecnici compatti e finalizzazione con hash degli artefatti.
- evidenziazione ST allineata alla baseline reale e limitata esattamente alle parole selezionate;
- testo evidenziato sempre bianco su fascia accentata, anche dopo un a capo o una riga vuota.

## Installazione

Scaricare `quote-card-builder.zip` dalla release più recente ed estrarlo nella cartella delle skill di Codex con nome `quote-card-builder`. Il file `SKILL.md` deve trovarsi direttamente nella radice della cartella installata.

## Uso

Invocare la skill con:

```text
$quote-card-builder
```

La conversione PNG usa Node.js e `sharp` quando sono già disponibili nella sessione. La skill non installa dipendenze automaticamente. Dopo il preflight, `Genera` attiva il chatbot Codex locale con un handoff vincolato al production manifest; l'interfaccia mostra lo stato del processo e i link ai PNG.

## Verifica

```bash
python3 -m unittest discover -s tests -v
```

L’editor locale si avvia soltanto su `127.0.0.1` con token di sessione e mantiene fonte, brand e dimensioni come campi protetti.

## Licenze dei font

I font incorporati nell’interfaccia sono accompagnati dai rispettivi file OFL nella cartella `assets/card-editor/fonts/`.
