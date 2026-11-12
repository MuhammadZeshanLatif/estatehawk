# Story ads, batch 3 (9 ads)

Same pipeline as `story-ad.md`. Flow: Omni 1.1 Flash, 16:9, 720p, 8 s, x1 (12 credits).
Every prompt ends with: `Cinematic, shot on 35mm, shallow depth of field, soft film grain, photorealistic, 16:9. No on-screen text, no captions, no logos, no readable writing. No dialogue, no speech.`

| Ad | Clips | Voice |
|---|---|---|
| A First deal (Ryan, daughter's bike) | A1-A5 | Charon, emotional |
| B Trucker (Mike leaves the road) | B1-B5 | Charon, emotional |
| C Father and son (Walt, Chris) | C1-C4 | Charon, warm |
| D Partner walked out (Nina) | D1-D4 | Charon, inspiring |
| E Two phone calls (split) | reuses batch 1 Tom/Marcus clips | Charon, premium |
| F Two weekends (split, Greg/Maria) | F-L1 F-R1 F-L2 F-R2 | Charon, premium |
| G Two years (split, Derek 2025/2026) | G-L1 G-R1 G-L2 G-R2 | Charon, premium |
| H Driving for dollars (Devon comedy) | H1 H2 | Orus, deadpan |
| I Day in the life (Maria vlog) | I1-I4 | female first person |

Voice scripts are in the AI Studio runs; sentence timing by `story/voice_times.py`.

### Built 2026-11-12
Specs: `story/trucker.json fatherson.json partner.json calls.json weekend.json years.json driving.json vlog.json` (CLIPS3 = clips3 folder, CLIPS = batch 1 clips, WORK = voices and cards).
- Two clips never downloaded, so: father-son uses `Man_reading_laptop_with_son` for C2 and C3; years uses `Man_driving_car_slowly` for the 2025 couch shots.
- A (first deal) waits for the A5 bicycle clip.
