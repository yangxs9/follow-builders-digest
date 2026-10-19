# Digest template

Use this as the default layout; adapt it to explicit user preferences. Write summaries and localize headings in the language requested by the user (`manifest.json` records it; default: Chinese). Keep quotations in their source language and omit empty sections. For periods other than seven days, use “Digest” instead of “Weekly Digest”.

## Report

```markdown
# Follow Builders Weekly Digest | {{date range}}

## X: What builders are discussing

{{selected entries using the layout below}}

## Blogs: Articles worth reading

{{selected entries}}

## Podcasts: Discussions worth exploring

{{selected entries}}
```

## Entry

```markdown
### {{specific, accessible title; optionally include the podcast name}}

**{{one-sentence summary of the main point, with clear attribution}}**

{{one or two paragraphs in the requested language: context, concrete examples, and key tradeoffs}}

> {{accurate source excerpt, when available and wanted; retain useful context and respect quotation limits}}

{{optional further context or examples; important entries may include another attributed excerpt}}

[{{author or show name}}]({{source URL}})
```
