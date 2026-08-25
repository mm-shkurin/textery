// What the browser is allowed to download, in gzipped kilobytes.
//
// Nothing measured this. `vite build` prints every chunk's size and then exits 0 whatever it
// printed, so the only thing standing between this app and a 2 MB entry chunk was somebody reading
// the build log — and a number that is only ever read is a number that only moves one way. One
// casually-added date library, one `import` that pulls a lazily-loaded route into the entry chunk,
// and the app gets slower for everyone on a slow connection with nothing red anywhere.
//
// GZIPPED, not raw: it is what actually crosses the wire, and a raw budget would be tightened and
// loosened by compression ratio changes that no visitor experiences.
//
// The budgets are a CEILING SET JUST ABOVE TODAY, in the same spirit as the coverage floors: their
// job is to fail when a change makes things meaningfully worse, not to describe an ideal. Raising
// one is a decision - make it deliberately, in its own commit, with the reason in the message.
export const BUDGETS = [
  {
    // The entry chunk: React, the router, the session layer, and every screen that is not the
    // editor. This is what a first-time visitor waits for before anything renders at all.
    pattern: /^index-.*\.js$/,
    // Raised from 125 for TanStack Query (~4 kB gzipped here), which is a deliberate architectural
    // addition rather than an accident: the lists it backs used to refetch in full on every visit,
    // so the bytes buy back more network than they cost on a session with any navigation in it.
    // Measured at 128.1 kB after the change; 132 keeps the same "just above today" margin the
    // other budgets have.
    //
    // Raised again from 132 for the MVP+ screens: «примеры готовых работ» on the landing, the
    // search + date filter and delete confirmation on «Мои работы», the style picker and the
    // topic suggestions on the composer. All of it is markup, copy and CSS for screens the entry
    // chunk already carries — no new runtime dependency rode in (the one library added, Tiptap's
    // table extension, lands in the lazily-loaded editor chunk below, which is what the split is
    // for). Measured at 132.9 kB after the change; 134 keeps the same narrow margin.
    //
    // Raised again from 134 for CSS modules. Component stylesheets are no longer global, which
    // is the point — a class name in one slice can no longer restyle another. The cost is a
    // class-name map per stylesheet compiled into JS, about 6 kB gzipped across ~50 of them.
    // Production ships hashed names only (`[hash:base64:6]`, see vite.config.ts), which already
    // took 1.5 kB back out; the rest is what scoping costs. Measured at 139.2 kB; 141 keeps the
    // same narrow margin.
    //
    // Raised again from 141 for the landing's redraw against the Figma frame: the export section
    // and the «нам доверяют» row are new components, and the feature cards gained their
    // illustrations. All of it is markup and copy for the first screen a visitor sees, so none of
    // it can be moved behind the lazy boundary — the split exists to keep the EDITOR out of this
    // chunk, and a landing that loads after the landing is not a landing. One section was deleted
    // in the same pass («примеры готовых работ», which the redrawn frame replaces), which is why
    // the net is under a kilobyte. Measured at 141.9 kB; 143 keeps the same narrow margin.
    maxGzipKb: 143,
    why: 'the entry chunk is what a first visit blocks on',
  },
  {
    // The Tiptap editor and ProseMirror, lazily loaded: it costs nothing until a document is
    // actually opened, which is why it gets a larger budget than the entry chunk rather than a
    // stricter one. What the budget guards here is that it stays SEPARATE - if this chunk
    // disappears because someone imported the editor eagerly, the entry budget above catches it.
    pattern: /^ManualEditor-.*\.js$/,
    maxGzipKb: 140,
    why: 'the editor chunk is lazily loaded, but only while it stays a chunk',
  },
  {
    pattern: /^index-.*\.css$/,
    // Raised from 12 with the same change: hashed module class names are longer than the
    // hand-written ones they replace, and there are more of them because a shared rule can no
    // longer be reused across slices by accident. Measured at 12.0 kB.
    //
    // Raised from 13 with the landing redraw above: three new stylesheets (export, trusted-by,
    // card artwork) against one deleted, plus the frame's positioning for art that used to be an
    // empty grey well. Measured at 13.5 kB; 14 keeps the margin.
    maxGzipKb: 14,
    why: 'the global stylesheet is render-blocking',
  },
  {
    // Ships inside the editor chunk, so it costs nothing until a document is opened.
    pattern: /^ManualEditor-.*\.css$/,
    maxGzipKb: 4,
    why: 'the editor stylesheet rides along with the lazily-loaded editor',
  },
]

// A chunk that matches no budget is reported rather than ignored. Silence about a new 400 KB file
// is exactly the hole this gate was added to close, and the fix - add a budget line for it - takes
// one line and forces the number to be looked at once.
export function budgetProblems(assets) {
  const problems = []
  const covered = new Set()

  for (const { pattern, maxGzipKb, why } of BUDGETS) {
    const matched = assets.filter(({ name }) => pattern.test(name))
    if (matched.length === 0) {
      problems.push(
        `  no asset matches ${pattern} — ${why}.\n` +
          '    Either the build stopped producing it (check the chunk split) or it was renamed; update the budget.',
      )
      continue
    }
    for (const asset of matched) {
      covered.add(asset.name)
      const kb = asset.gzipBytes / 1024
      if (kb > maxGzipKb) {
        problems.push(
          `  ${asset.name} is ${kb.toFixed(1)} kB gzipped, over its ${maxGzipKb} kB budget — ${why}.\n` +
            '    Find what was added before raising the number; a budget raised to make a build pass is not a budget.',
        )
      }
    }
  }

  for (const asset of assets) {
    if (!covered.has(asset.name)) {
      problems.push(
        `  ${asset.name} (${(asset.gzipBytes / 1024).toFixed(1)} kB gzipped) has no budget.\n` +
          '    Add one to scripts/bundleBudget.mjs; an unbudgeted chunk grows unwatched.',
      )
    }
  }

  return problems
}
