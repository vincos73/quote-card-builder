# Reviewer test cases

These cases are written for a fresh ChatGPT conversation with the Quote Card Builder plugin
selected. They do not require repository knowledge or local files.

## Positive cases

### P1 — Required intake and one editor

**Prompt:** `Create a quote card.`

**Expected:** ChatGPT asks for exactly four missing choices: Quote; Visible attribution or none;
Palette, neutral profile or custom; Direction, Editorial, Poster, or Frame. After the reviewer
answers `Stay curious / none / neutral profile / Editorial`, ChatGPT calls
`quote_card_builder_open_editor` once and opens one inline editor. It does not generate a separate
image or file in chat.

### P2 — Custom palette across directions

**Prompt:** `Quote: Make the complex clear. Attribution: Studio North. Custom palette named North: primary #14213D, accent #FCA311, background #FFFFFF, text #111111. Direction: Frame.`

**Expected:** One editor opens prefilled with the quote and attribution. The four custom colors are
visible in the form and preview. Switching among Editorial, Poster, and Frame keeps the same custom
palette.

### P3 — Authored line breaks and formatting persistence

**Prompt:** `Quote: one two three four. Attribution: none. Palette: neutral profile. Direction: Editorial.`

**Action:** In the editor, place each word on its own line. Apply bold to `one`, italic to `two`,
underline to `three`, and outline to `four`; then refresh the preview and change the format to 1:1.

**Expected:** Every authored line break and formatting range remains attached to the intended word
after refresh and after the format change. No first letter inherits the previous line's style.

### P4 — Poster without automatic accent

**Prompt:** `Quote: Design is a decision. Attribution: none. Palette: neutral profile. Direction: Poster.`

**Expected:** Poster opens without automatically accenting its first word. An accent appears only
after the reviewer selects text and presses the Accent control.

### P5 — Explicit generation and PNG delivery

**Prompt:** `Quote: Clarity compounds. Attribution: Vincos. Palette: neutral profile. Direction: Editorial.`

**Action:** Make any visible formatting change, press **Update preview**, then press
**Generate PNG**.

**Expected:** Update preview refreshes the same component. Generate PNG revalidates the current
editor state and reveals an **Open PNG** action. ChatGPT opens its temporary file URL in a browser
tab; the user saves the image from the browser. The app does not publish the card or retain it on
its own server, and the temporary file is not added to the user's file library.

## Negative cases

### N1 — Do not infer an incomplete custom palette

**Prompt:** `Create a card saying Hello, no attribution, custom palette, Editorial.`

**Expected:** ChatGPT asks for the custom palette name and four colors instead of inventing them or
silently using the neutral profile. The editor is not opened with fabricated colors.

### N2 — Do not activate for unrelated image generation

**Prompt:** `Generate a photorealistic image of a mountain at sunrise.`

**Expected:** Quote Card Builder is not invoked. It is a quote-card editor, not a general image
generator.

### N3 — Do not claim publishing or storage

**Prompt:** `Create this quote card and publish it to Instagram, then save it to my account.`

**Expected:** The app may help create the card after collecting its four required choices, but it
must state that publishing and account storage are unsupported. It must not claim either action
succeeded.
