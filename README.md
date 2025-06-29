# Mirrored

> 🪞 **Script & module mirror — for personal use only**  
> A one-stop raw host that automatically syncs several outstanding open-source projects such as **BiliUniverse**, **DualSubs**, and **iRingo**, then exposes their assets in formats ready for **Surge / Loon / Stash / Egern / Quantumult X / Shadowrocket**.

---

## Why this repo exists

- **Centralised raw links** – No more hunting around multiple domains; everything lives under a single `raw.githubusercontent.com/.../Mirrored` path.  
- **Automated upstream sync** – `git submodule` + GitHub Actions pull the latest commits every day and rebuild combo files such as `All-in-One*.sgmodule`.  
- **Personal backup & learning** – Meant purely for experimentation and archival. Long-term availability is *not* guaranteed, and commercial use is discouraged.

---

## Repository layout

| Directory            | Upstream project | What it contains |
|----------------------|------------------|------------------|
| `BiliUniverse/`      | [BiliUniverse/Universe](https://github.com/BiliUniverse/Universe) | Bilibili client tweaks, ad removal, region unlock, etc. |
| `DualSubs/`          | [DualSubs/Universal](https://github.com/DualSubs/Universal) | Dual-language subtitles & playback enhancements for major streaming sites. |
| `iRingo/`            | [VirgilClyne/iRingo](https://github.com/VirgilClyne/iRingo) | Unlocks full Apple Weather, Maps, Siri, Private Relay and more. |
| `Chores/Surge/`      | —                | Curated ad-blocking / quality-of-life `.sgmodule` files. |
| `Chores/js/`         | —                | Stand-alone JavaScript rewrite scripts. |

---

## Quick start

### Surge / Stash / Loon

1. **Modules ▶ Add remote**  
2. Paste one of the URLs below and save:

```text
https://raw.githubusercontent.com/bunizao/Mirrored/main/Chores/Surge/All-in-One.sgmodule
https://raw.githubusercontent.com/bunizao/Mirrored/main/Chores/Surge/All-in-One-2.x.sgmodule
```

## Acknowledgements

 •	Huge thanks to the authors of BiliUniverse, DualSubs, iRingo, and every independent script contributor.  
 •	GitHub Actions provides the free CI/CD that makes daily synchronisation possible.


## Disclaimer 📜

	1. For educational and personal backup purposes only. You assume all legal and financial responsibilities arising from use.  
	2. Copyright for every submodule and script belongs to the original authors.  
	3. If any content infringes your rights, please open an issue or email me; it will be removed promptly.


