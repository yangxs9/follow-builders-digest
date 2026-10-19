# Follow Builders Digest

English | [简体中文](README.zh-CN.md)

An [Agent Skill](https://agentskills.io) for turning content collected by [Follow Builders](https://github.com/zarazhangrui/follow-builders) into a sourced Markdown digest of X posts, blogs, and podcasts.

Generates local files on demand: the script prepares source material, and your agent selects and summarizes it.

## Requirements

- An agent that can read skills, run local scripts, and write files.
- Python 3.10+ with timezone data; no third-party Python packages required.
- Access to GitHub API and `raw.githubusercontent.com`. Optional: `GITHUB_TOKEN` for a higher API quota.

## Use

Install this folder as `follow-builders-digest` using your agent's skill mechanism, or ask it to read [SKILL.md](SKILL.md) directly. Then request:

> Use follow-builders-digest to summarize the past seven days in English, focusing on agent development.

Defaults: past 168 hours, Chinese (`zh-CN`), `Asia/Shanghai`, and `./output`. Override the period, language, timezone, topics, or writing style in your request.

Each run creates a separate directory with `digest.md` (the digest), `items.json` (source material), and `manifest.json` (provenance and acquisition status).

Digests are curated by default. Coverage depends on upstream data; items without valid publication dates are excluded. See the [writing rules](references/digest-writing.md) and [template](assets/digest-template.md) to adjust the defaults.

## License

[MIT](LICENSE). Source content remains subject to its respective rights and terms.
