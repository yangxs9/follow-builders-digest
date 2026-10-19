# Digest selection and writing

Read this file when writing or reviewing a digest. Use [the template](../assets/digest-template.md) for the default layout. Style, section order, length, and quotation choices below are defaults: follow explicit user preferences. Preserve source accuracy, attribution, and honest coverage reporting with any format.

## Selection and coverage

- Produce a curated digest by default. Prefer relevant content with concrete facts, examples, methods, reasoning, or engineering tradeoffs. Adapt to requested topics, authors, or comprehensive coverage.
- Skip thin promotion, repetitive reposts, and unsupported generalities. Product announcements can qualify when they explain useful changes, applications, or limitations. Popularity and author reputation are not substitutes for substance.
- Merge overlapping events or views while keeping source links and attribution. Retain unique facts, qualifications, and opposing views.
- Read candidate bodies before selection, using complete batches or segments for long content. Do not count unread candidates as reviewed. If the requested scope cannot be completed, state the actual coverage.
- Do not force an item count or fill every source category. If candidates exist but none qualify, explain the selection reason in the response; do not claim that the period contained no content.
- Report the manifest's candidate count and the number of distinct candidate `id` values represented in the digest. Count each candidate once, even if mentioned repeatedly; a merged entry may represent several candidates.
- Distinguish curation from complete coverage and acquisition success from upstream completeness. Disclose material gaps and label acceptance samples as samples. By default, keep counts and diagnostics in the task response or scheduler output, outside the digest.

## Default structure

- Write in the user's requested language, recorded as `language` in the manifest; the default is Chinese. Keep source quotations in their original language.
- Show the requested period in the title, interpreted in the manifest's `timezone`.
- Order sections as X, blogs, then podcasts, omitting empty sections. Use “Weekly Digest” for seven-day periods and “Digest” for other periods. Localize section headings to the requested language.
- Start directly with content. Omit an introduction, run times, SHAs, counts, diagnostics, acquisition errors, individual publication dates, and artifact links from the digest body.
- If acquisition has not failed and there are no candidates, use only a dated title and a short “No matching content was found for this period” message in the requested language. Report any acquisition gaps separately.

## Default detail and quotations

- For an entry with usable English source text, include at least one meaningful excerpt; important or merged entries may use two. Ordinary product updates can be shorter. A user's request for no quotations overrides this default.
- Do not impose a fixed total length, item count, or language ratio. Prefer informative source material over generic commentary that repeats it.
- Choose quotation length for understanding, within applicable quotation limits. A short statement can stand alone; reasoning, conditions, examples, or tradeoffs may need several continuous sentences or a paragraph when permitted. Link to the original for more context.
- Longer excerpts should convey a complete thought, such as context, explanation, and conclusion. Avoid irrelevant padding or repeating the same sentence in both a highlight and an extended quotation.
- Quote accurately from candidate bodies and preserve qualifications. Mark omissions; do not splice separate passages into a supposedly continuous quotation. Never back-translate a summary and present it as an original quote. Avoid unreliable transcript passages.
- By default, let readers read English excerpts directly. Use the requested summary language to explain context, facts, and views without line-by-line translation or vocabulary and grammar lessons.
- Attribute excerpts from different authors individually and explain disagreements rather than implying consensus.
- Use the source `url` from `items.json`. If a podcast URL points only to a channel or playlist, label the link accordingly rather than guessing an episode URL.
- Present only facts and views supported by the source. Clearly label your own interpretation.

## Final review

- Verify source URLs against `items.json`, and quotations against candidate bodies.
- Check that summaries preserve context, attribution, qualifications, and meaningful tradeoffs without unsupported facts.
- Follow the requested format or default template. Remove placeholders and empty sections. Under the default style, also omit language lessons and run diagnostics.
- Review empty-result digests too, including the requested language and period.
- Reconcile reported counts with the candidate set and cited items. Identify curation, incomplete reading, and unavailable content honestly.
