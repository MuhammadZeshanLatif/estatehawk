# EstateHawk story ad (English, for US investors, about 65 s)

Format (same as the Rag-e-Hayat video): a short cinematic story of the problem first, no names or brand,
then the product, then a happy ending and the website.
Cinematic shots: generate with an AI video tool (Google Flow / Veo, Kling, Meta AI), 16:9, 8 s each.
Product shots: `shorts/story-ad.js` (Playwright, same recorder as every other video).
Voice: `shorts/story-ad-voice.txt` (Google AI Studio, Generate speech).

## Character (paste into every prompt so he looks the same)
Mike, a white American man in his early 40s, short brown hair, light stubble, navy quarter-zip sweater over a grey t-shirt.

## Shots

| # | Voice line | Shot | Source |
|---|---|---|---|
| 1 | It's eleven at night... fifteen different formats. | Kitchen table at night, laptop with many tabs, cold coffee, tired | AI clip |
| 2 | He finally finds a homeowner... "Sorry, we already sold." | On the phone, his face drops, he puts the phone down | AI clip |
| 3 | Old lists. Wrong owners... returned to sender. | Pile of returned envelopes on a desk, he drops another on top | AI clip |
| 4 | The deals were out there... one step behind. | Across the street, another investor shakes hands with a homeowner; Mike watches from his car | AI clip |
| 5 | Then he found EstateHawk. | Laptop screen light on his face, he leans in, a small smile | AI clip |
| 6-8 | Every morning... He knows the same day. | Dashboard, lead details, map, alerts | story-ad.js |
| 9 | Now Mike is the first call... before the tax sale does. | Sunny porch, older homeowner shakes his hand, relieved | AI clip |
| 10 | EstateHawk. Find them first... | End card | story-ad.js |

## Prompts (one per clip)

Common ending for every prompt:
`Cinematic, shot on 35mm, shallow depth of field, natural film grain, realistic, 16:9. No on-screen text, no captions, no logos, no readable writing.`

1. Night. A suburban Ohio kitchen, only a warm pendant light on. Mike sits at the kitchen table in front of an open laptop, a cold cup of coffee beside him, rubbing his eyes. The laptop screen glows blue on his tired face. Slow push-in from the side. Quiet, lonely mood, cool blue and warm amber tones.
2. Same kitchen at night. Mike holds a phone to his ear, hopeful at first, then his expression drops in disappointment. He lowers the phone slowly and stares at the table. Close-up on his face, handheld camera, moody low light.
3. Close-up of a home office desk covered with a pile of returned mail envelopes stamped with red marks. Mike's hand drops one more envelope on top of the pile. Camera slowly tilts up to Mike leaning back in his chair, frustrated, hand over his mouth. Overcast daylight from a window.
4. A quiet American suburban street in the afternoon. In the background, a confident man in a fleece vest shakes hands with an older homeowner on the front lawn of a white two-story house. In the foreground, Mike sits in his parked car, watching through the windshield, jaw tight. Shallow focus shifts from the handshake to Mike's face.
5. Night, the same kitchen. Mike looks at his laptop, the screen light on his face changes from blue to warm. He leans forward, his eyes widen, and a small smile appears. Slow push-in, hopeful music mood.
9. Bright sunny morning, a modest American house with a front porch. An older woman in a cardigan opens the screen door; Mike, smiling and respectful, shakes her hand. She looks relieved and grateful, holds a folder of papers. Warm golden light, gentle handheld camera, hopeful mood.

Tools: Google Flow or Gemini (Veo) if the account has video credits; Kling or Meta AI have free daily credits.
Download each clip as mp4 and name it `s1.mp4`, `s2.mp4`, ... `s9.mp4`.

## Assemble
1. Voice: put the WAV next to the clips. Sentence start times come from STT (English works).
2. Product part: `bash tools/video/run.sh --file shorts/story-ad.js --no-captions --out tools/video/out/story`
3. Join clips + product part at the sentence times, voice on top, music ducked (same approach as `fit.py`).
