---
name: styleframe-first
description: Approve representative frames before any full render. Use whenever a pipeline is about to produce a large visual artifact — a multi-page PDF, a full video, a slide deck, a batch of images — and a human will judge the result. Also use when a user keeps rejecting finished renders and each rejection forces a full rebuild, or when someone asks how to stop burning full renders on taste feedback.
---

# Styleframe First

**Never full-render before a human has approved representative frames.**

## The failure this kills

Mechanical gates (fonts, colors, page breaks, metadata) pass automatically. Taste does not.
So taste rejections always arrive *after* the expensive artifact exists — and each one costs
a full rebuild.

Measured in one print pipeline (52 revision rounds audited):

- Before this rule: every taste rejection consumed a full 89–112 page re-composition plus
  full print QA. Even a 2-page visual fix triggered a full rebind. One deliverable burned
  20 rounds this way.
- After: four consecutive taste rejections were absorbed at the styleframe stage —
  4–14 PNGs each, **zero** full PDFs. One rejected cover direction was explored and
  discarded for the cost of 4 PNGs. The full render ran exactly once, after direction
  was locked, and passed fresh QA with zero defects on the first try.

Full-render cost moved from *per rejection* to *once per approved direction*.

## Protocol

1. Pick representative frames: the cover, the densest interior page, the page most likely
   to be contested, the CTA/closing frame. For books: 3–7 pages. For video: hook frame,
   most complex evidence frame, CTA frame.
2. Render **only those**, at final quality, as stills (PNG). Declare the forbidden scope
   out loud in the round doc: no full PDF, no full raster, no contact sheet, no manifest.
3. Set status `PASS_STYLEFRAMES_ONLY` → `WAITING_USER_STYLEFRAME_APPROVAL`, and stop.
4. Human approves → full render once, binding the approved frame hashes as inputs.
5. Human rejects → iterate at the styleframe level. The rejection cost stays at a handful
   of PNGs.

## Two companion rules

- **Ask "clone or redesign?" before frame one.** If an approved golden master exists for
  the series, get an explicit decision — inherit it verbatim with new content, or redesign.
  One follow-up volume burned 5 design rounds because that question was asked at round 9
  instead of round 4.
- **A one-sentence instruction gets one interpretation question.** "Make it like X" can
  mean pixel-clone or style-inherit; a wrong guess discards whole rounds. Ask once, then build.
