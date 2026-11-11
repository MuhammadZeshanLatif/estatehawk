# EstateHawk story ads (English, for US wholesalers and investors)

Two ads, same idea as the Rag-e-Hayat video: real-life problem first, then EstateHawk, then a happy ending.
- Cinematic shots: AI video tool (Google Flow / Veo, Kling or Meta AI), 16:9, one clip per shot.
- Product shots: `shorts/story-ad.js` (Playwright, already recorded, used by both ads).
- Voice: Google AI Studio > Generate speech.
- Name the clips `dan1.mp4 ... dan7.mp4` and `L1.mp4 ... L5.mp4`, `R1.mp4 ... R5.mp4`.

Add this ending to EVERY clip prompt:
`Cinematic, shot on 35mm, shallow depth of field, soft film grain, photorealistic, 16:9. No on-screen text, no captions, no logos, no readable writing.`

---

## Ad 1: "When is the first deal?" (Dan the wholesaler, about 55 s)

Characters (paste the same words in every prompt so they look the same):
- DAN: a white American man in his early 30s, short dark blond hair, light beard, grey hoodie.
- EMILY: his wife, early 30s, shoulder-length auburn hair, cream knit sweater.
- Home: a small, modest kitchen in an Ohio house.

| Clip | Shot | Voice over it |
|---|---|---|
| dan1 | Evening. EMILY stands by the kitchen counter holding a stack of bills, turns to DAN at the table, worried, not angry. He looks up from his laptop, tries to smile. Medium shot, warm tungsten light. | Emily: Six months, Dan... when is the first deal? / Dan: Soon. I promise. |
| dan2 | Late night, the same kitchen, only a pendant light on. DAN alone at the table, laptop glowing blue on his tired face, many browser windows, cold coffee, he rubs his eyes. Slow push-in. | Every night I dug through county websites... |
| dan3 | Close-up, night. DAN on the phone, hopeful, then his face drops. He lowers the phone slowly and stares at the table. Handheld, moody low light. | But the lists were old... someone else already had the deal. |
| dan4 | DAN stands in the dark hallway, looks through a half-open bedroom door at EMILY asleep, then looks down, guilty and tired. Blue night light. | Six months. Zero deals. |
| dan5 | Night, kitchen. DAN looks at his laptop; the light on his face turns from cold blue to warm. He leans in, eyes widen, a small smile. Slow push-in. | Then a friend showed me EstateHawk. |
| (product) | Playwright recording | Every morning it pulls... I know the same day. |
| dan6 | Bright sunny morning. DAN, smiling and respectful, shakes hands with an older homeowner in a cardigan on the porch of a modest American house. She looks relieved. Warm golden light. | Two weeks later, I was the first call... |
| dan7 | Daytime kitchen. DAN puts an envelope with a check on the table in front of EMILY. She opens it, covers her mouth, laughs and hugs him. Warm, happy light. | Emily: You did it! |
| (end card) | EstateHawk logo + getestatehawk.com | Your next deal is already waiting... |

### Voice (Multi-speaker mode: Speaker 1 = Dan, voice Charon; Speaker 2 = Emily, voice Aoede)
Style: An American couple in a small Ohio town. Dan is a tired but honest young wholesaler, telling his story in a low, warm, emotional voice; he becomes hopeful and confident after "Then a friend showed me EstateHawk". Emily is soft and worried at the start, overjoyed at the end. General American accent, natural pauses, not rushed.

```
Emily: [sigh] Six months, Dan... When is the first deal?
Dan: Soon. [short pause] I promise.
Dan: I'm a wholesaler. Every night, I dug through county websites, looking for owners who were behind on their taxes.
Dan: But the lists were old. [short pause] Every time I called... someone else already had the deal.
Dan: Six months. [short pause] Zero deals.
Dan: [long pause] Then a friend showed me EstateHawk.
Dan: Every morning, it pulls tax-delinquent properties straight from county records, in Ohio and Texas.
Dan: The owner, how many years behind, how much is owed, and a score that tells me exactly who to call first.
Dan: A new lead in my county? [short pause] I know the same day.
Dan: Two weeks later, I was the first call, not the last. [short pause] And I helped an owner get out before the tax sale.
Emily: [laughs] You did it!
Dan: [short pause] EstateHawk. Your next deal is already waiting. Start your free trial at getestatehawk dot com.
```

---

## Ad 2: "Same market. Different morning." (split screen, about 40 s)

Screen is split in two. LEFT = the old way, RIGHT = the EstateHawk way. Each side is its own clip;
I put them side by side, so keep the person in the CENTER of the frame in every prompt.

Characters:
- TOM (left): a white American man in his 50s, glasses, grey hair, wrinkled blue button-up shirt, cluttered home office.
- MARCUS (right): a Black American man in his 30s, short hair, navy polo shirt, bright clean modern kitchen.

| Beat | LEFT clip | RIGHT clip | Voice |
|---|---|---|---|
| 1 | L1: Night. TOM at a cluttered desk, centered, squinting at a laptop full of browser tabs, stacks of paper, a desk lamp. | R1: Night. MARCUS, centered, closes his laptop calmly, turns off the kitchen light and walks to bed, relaxed. | Two investors. Same market. |
| 2 | L2: 2 AM. TOM, centered, copies numbers from the screen into a notebook, drinks cold coffee, yawns. | R2: Night. MARCUS, centered, sleeping peacefully in bed, soft blue moonlight. | One spends his nights on county websites... |
| 3 | L3: Early morning. TOM asleep, slumped over his desk, centered, laptop still on, grey dawn light. | R3: Bright morning. MARCUS, centered, in the kitchen with a cup of coffee, opens his laptop and smiles. | The other opens EstateHawk with his morning coffee. |
| (product) | full screen Playwright recording | | Fresh tax-delinquent leads... who to call first. |
| 4 | L4: TOM, centered, on the phone, hopeful, then disappointed, hangs up and rubs his forehead. | R4: MARCUS, centered, on the phone, smiling, writing notes, nods. | By nine, one is still searching. The other is already on the phone. |
| 5 | L5: TOM, centered, stares at his screen, alone and frustrated, dim light. | R5: MARCUS, centered, shakes hands with an older homeowner on a sunny porch. | Same market. [pause] Different morning. |
| (end card) | EstateHawk logo + getestatehawk.com | | Start your free trial... |

### Voice (Single speaker, voice Charon or Orus)
Style: A calm, confident American narrator, like a premium brand commercial. Slow and steady, a little dry humor on the left side, warm and confident on the right side. General American accent, natural pauses.

```
Two investors. [short pause] Same market.
One spends his nights on county websites... copying lists that are already out of date.
The other? [short pause] He opens EstateHawk with his morning coffee.
Fresh tax-delinquent leads, straight from county records, every morning. The owner, what's owed, and a score that tells him who to call first.
By nine, one is still searching. [short pause] The other is already on the phone.
Same market. [long pause] Different morning.
EstateHawk. Start your free trial at getestatehawk dot com.
```

---

## Assemble (Claude does this)
1. Voice WAVs: sentence start times by STT.
2. Product part: `bash tools/video/run.sh --file shorts/story-ad.js --no-captions --out tools/video/out/story`
3. Ad 1: clips + product part in order, cut to the sentence times, voice on top, music ducked.
4. Ad 2: L and R clips cropped to the center half and placed side by side, thin divider line, small "THE OLD WAY" / "WITH ESTATEHAWK" labels, product part full screen in the middle.

### How the two finished ads were made (2026-11-11)
- Clips: Google Flow (Omni 1.1 Flash, 16:9, 720p, 8 s, 12 credits each), prompts above. Voices: AI Studio Gemini 3.8 Flash TTS (Dan = Charon, Emily = Aoede, narrator = Charon).
- `story/cards.js WORK` renders the end cards and split-screen labels.
- `story/voice_times.py VOICE.wav` prints when each sentence starts; put those times in the spec.
- `story/build.py story/dan.json` and `story/split.json` (replace WORK and CLIPS with real folders) build the ads.
