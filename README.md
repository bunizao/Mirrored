# Mirrored

> 🪞 **Script & module mirror — for personal use only**
>
> A single raw host that keeps open-source modules and scripts in sync and serves them in formats ready for **Surge / Egern / Loon / Stash / Quantumult X / Shadowrocket**.
>
> 📖 [中文索引 · Browse all modules](README.zh-CN.md)

---

## Why Mirrored

Many modules and scripts that were once openly hosted on GitHub are moving to private deployments. They no longer offer free access: requests are logged in detail, and some legitimate users are blocked outright. Configurations that depend on them can break at any time, and usage traces may be exposed without anyone noticing.

The open ecosystem is closing in. A community born to route around censorship is putting up walls of its own.

Mirrored exists to keep these tools available. Like an internet archive, it continuously mirrors and syncs them so that scripts no longer depend on a single origin or a sudden change of policy.

This is not easy. Censorship, blocked origins, anti-scraping measures and the spread of private hosting all make an open mirror harder to keep alive. That is exactly why it is worth doing.

Mirrored is not a fight; it is preservation. However the ecosystem tightens, we want to leave developers and enthusiasts a place they can still trust, still reach, and still build on.

---

## Quick start

In Surge / Stash / Loon, choose **Install module from URL** and paste the recommended ad-blocking bundle:

```text
https://raw.githubusercontent.com/bunizao/Mirrored/main/Chores/sgmodule/All-in-One-2.x.sgmodule
```

Every other module, with a description and link, is listed in the [index](README.zh-CN.md).

## What's mirrored

| Directory | Contents | Upstream |
| --- | --- | --- |
| [`Chores/`](Chores) | Ad-blocking and utility modules, a reject ruleset, mirrored scripts | Community authors |
| [`BiliUniverse/`](BiliUniverse) | Bilibili enhancements | [BiliUniverse](https://github.com/BiliUniverse) |
| [`DualSubs/`](DualSubs) | Dual-language subtitles for streaming services | [DualSubs](https://github.com/DualSubs) |
| [`iRingo/`](iRingo) | Apple service enhancements | [NSRingo](https://github.com/NSRingo) |

Every mirrored file starts with a `# 🪞 Mirrored` line naming its upstream source.

---

## Acknowledgements

Huge thanks to the authors of BiliUniverse, DualSubs, iRingo, and every independent script contributor.

## Disclaimer 📜

1. For educational and personal backup purposes only. You assume all legal and financial responsibilities arising from use.
2. Copyright for every mirrored module and script belongs to the original authors.
3. If any content infringes your rights, please open an issue or email me; it will be removed promptly.

<sub>Maintainer notes: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)</sub>
