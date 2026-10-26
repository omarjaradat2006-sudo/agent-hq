# Omar's TikTok script format (from his content-scripts + VoicePrint skills)

Every TikTok idea the Copywriter writes MUST follow this. Omar films sitting down, talking to camera, in one take. His visual-hooks editor zooms at each [pause], so scene changes land on zooms.

## Voice
Regular guy giving advice, not a guru. A student who works, still building, not rich. Speak from the middle of the journey: "we", "guys our age", "here's what I'm trying", "something I noticed". Pass along lessons as someone who found them. Never flex. A calm hard truth beats hype. Casual, direct, short spoken sentences, about 2.5 words per second. If a line sounds like a blog post, rewrite it.

## Hard rules
- The first spoken line must stop a stranger in under 3 seconds and make the subject clear by second 3. No "Hey guys", no intro, no name before the hook.
- Never fabricate. No invented stats, studies, stories, quotes or names. Real, named sources only; if a line needs Omar's own story or number, write `[fill in: your real story]`.
- Faith content: never invent or paraphrase-as-quote an ayah or hadith; real reference only, plus `[verify source]`. No rulings.
- The hook may never promise more than the payoff delivers.
- One CTA max, preferably a comment-provoking question or a loop back to the hook.
- Put a re-hook line ("but here's the part nobody mentions...") around the middle, where attention dips.

## Structure (store in the idea as JSON)
```
"hookFamily": "Curiosity loop" | "Story / progressive reveal" | "Call-out" | "Calm hard truth" | "Debate line" | "Vulnerable admission" | ...,
"length": 35,                      // seconds
"onScreen": "short text shown in the first 3-5s that ADDS to the spoken hook, never repeats it",
"scenes": [
  {"label": "Hook", "time": "0-3s", "line": "exact spoken words", "delivery": "lean in, flat and serious"},
  {"label": "Context lean", "time": "3-8s", "line": "...", "delivery": "..."},
  {"label": "Re-hook", "time": "~15s", "line": "...", "delivery": "..."},
  {"label": "Value", "time": "...", "line": "...", "delivery": "..."},
  {"label": "Payoff", "time": "...", "line": "...", "delivery": "..."},
  {"label": "Last line / loop", "time": "...", "line": "...", "delivery": "how it loops into the hook, if it does"}
],
"hooksToTest": ["3 alternative first lines, each from a different hook family, so he can film 2-3 openings in one sitting"],
"caption": "one specific line + exactly 5 hashtags: #fyppppppppppppppppppppppp #viral #fyp + 2 for this video"
```
Also keep `script` as the full spoken script with `[pause]` between scenes (for copying).

## `formatted` — REQUIRED. This is what Omar sees on the site.
Each idea is ONE version, written EXACTLY in his content-scripts output format (the same thing his skill prints in chat), as markdown, AFTER the VoicePrint pass. Copy this layout character for character; only the words change:

```
**VERSION A - Curiosity loop (~35s)**
- **Why this one:** one sentence on the mechanism (what tension it creates).
- **On-screen text (first 3-5s):** a short line that adds to the spoken hook, never repeats it.

**Scene 1 - Hook (0-3s)**
> exact spoken line(s)

*Delivery:* lean in, flat and serious.

[pause]

**Scene 2 - Context lean (~5s)**
> exact spoken lines

*Delivery:* ...

[pause]

...every scene the same way (Scene N - <job> (~Xs), quoted line, *Delivery:*, [pause])...

**Last line:** "the last spoken line" (and how it loops into Scene 1, if it does)

- **Hooks to test:**
  - alternative first line 1 (hook family)
  - alternative first line 2 (hook family)
  - alternative first line 3 (hook family)
- **Caption:** one line + exactly 5 hashtags
```
Use VERSION A / B / C across the 3 ideas of a run (one per idea). Spoken lines in `formatted` must be word-for-word the same as `scenes[].line` and `script`. Never output paragraphs instead of scenes. If `formatted` doesn't match this layout, rewrite it before saving.

Typical scene jobs: hook, context lean, re-hook / tension, value or clues, reveal, payoff, loop/close. 4-7 scenes. Version lengths: curiosity loop 25-40s, story 40-60s, hard truth / call-out 20-35s. The 3 daily ideas must use 3 different hook families AND structures, not just different wording.

## VoicePrint pass (always, after drafting, before writing `formatted`)
Load the content-scripts skill (Skill tool) for hooks and structure, then run each script through the voiceprint skill (register: Casual → Social post; freedom: "Keep the structure too, sentences only"), so it sounds like Omar, not AI. If the skill isn't available, do it by hand:
- Vary sentence length hard: some 2-4 word lines, some longer ones. No even rhythm.
- Cut AI tells: "Here's the thing", "Let's dive in", "game-changer", "unlock", "navigate", "journey", "It's not X, it's Y" framing, rule-of-three lists, em-dashes, tidy summaries at the end.
- Use contractions, plain words, the odd fragment, and the way a 20-year-old actually talks.
- Keep every scene, every fact and every [pause] where it is.

## Self-check before saving
1. Read only the first line: would a stranger need the next 3 seconds?
2. Is the subject clear by second 3?
3. Does every line add something new? Cut any that don't.
4. Does the payoff fully pay off the hook?
5. Is anything invented? Replace with [fill in].
6. Are the 3 ideas different in structure, not just reworded?
7. Could Omar say every line honestly as a regular guy still figuring it out?
