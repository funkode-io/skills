# Release notes template

Structure, in order. Drop a section only when the release genuinely has nothing for
it (a maintenance release has no Breaking changes and no Migration).

````markdown
## Highlights

One paragraph. What the release lets a consumer do that 0.<prev> did not, in domain
language (aggregate, stream, watermark, policy, dead letter), with the new type and
method names in code ticks.

---

## Breaking changes

<N> signatures changed. Numbered subsection per changed item, each headed with the
item's path:

### 1. `Compactable::compacted_events` now returns `Compaction<E>`

The new shape, as a code block a reader can match against their own code:

```rust
pub enum Compaction<E> {
    Rewrite(Vec<E>),   // replace the live stream with this minimal sequence
    AlreadyCompacted,  // stream already minimal — the store writes NOTHING
}
```

Then why it is shaped that way, when two variants could be confused for one another.

---

## New API

One subsection per new public item, each with sample code that could be pasted into
a consumer's crate and compile: the `use`, the call, and what comes back.

```rust
if store.needs_compaction(&stream_id).await? {
    store.compact(&aggregate, metadata).await?;
}
```

---

## Migration

One subsection per breaking item, in the order of the Breaking changes section, each
a **diff** block showing the before and after of realistic consumer code:

```diff
-let archive_version = store.compact(&aggregate, metadata).await?;
+match store.compact(&aggregate, metadata).await? {
+    CompactionOutcome::Compacted { archive_version } => { /* archived */ }
+    CompactionOutcome::Skipped => { /* already minimal */ }
+}
```

Close with the blast radius measured in this repo ("~4 impls + ~3 callers, all
mechanical") so a reader can size the upgrade before starting it.

Any contract the new API imposes goes in a blockquote here — a consumer who migrates
mechanically must still learn the rule they are now bound by.

The code blocks above are illustrative, lifted from a real release; write yours
against the actual items from the API inventory.

---

## Changes since <prev>

- `feat(persistence)!`: AlreadyCompacted domain guard for compaction (#143) — **breaking**
- `feat(persistence)`: `needs_compaction` watermark pre-check (#142)

One line per merged PR, conventional-commit subject plus PR number, breaking ones
marked. Internal-only commits (perf, refactor, docs) belong here too — this list is
the complete inventory from step 3.

**Full diff:** https://github.com/<slug>/compare/v<prev>...vX.Y.Z
````

## The snippet bar

Sample code and migration diffs are the reason the page exists, so hold them to
compiling standard:

- Write them against the **real** signatures, read from the source at the tagged
  commit — not from the PR description, which may predate review changes.
- Use the repo's own example domain — the types the README already uses — so the
  snippets read like the documentation a consumer has open.
- Compile-check anything non-trivial: paste it into a scratch test or example in the
  workspace, run `cargo check --workspace --all-targets`, then delete the scratch file.
- Show the `use`/path of every named item — a consumer's first error after upgrading
  is an unresolved import.
- When a `Vec` or `impl Into` conversion makes the migration a one-liner, say so and
  show the one line (`.map(Into::into)`); that is what most readers will apply.
