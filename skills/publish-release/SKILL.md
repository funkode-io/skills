---
name: publish-release
description: 'Cut a release of a Rust workspace: bump the version, tag it, publish the crates to crates.io, and write GitHub release notes carrying sample code for new API and a migration for every breaking change. Use when the user wants to release, cut a version, bump to X.Y.Z, or publish to crates.io.'
---

# Publish a release

A release is three artefacts that must agree: a **tag** on the upstream repo, the
**crates** on crates.io, and **release notes** that a consumer can upgrade from
without reading the diff.

The notes are the product. A user on the previous version lands on the release page
and must find, for every API that changed, either runnable sample code (new API) or a
copy-pasteable diff (breaking API). Everything else here is bookkeeping around that.

## 0. Load the repo's release configuration

Read `docs/agents/release.md` for: the upstream repo slug, the crates published and
in what order, every file carrying a version, the pre-flight gate commands, and the
version policy.

If that file does not exist, derive the same facts from the tree — `cargo metadata`
for the workspace members and their inter-crate version pins, `git remote -v` for
upstream, `cargo search <crate>` for what is actually published, the last few
`chore: bump version` commits for which files moved — then offer to write
`docs/agents/release.md` so the next release does not repeat the archaeology.

Done when you can name the upstream slug, the ordered publish set, and the version
files.

## 1. Establish the baseline

```sh
git fetch upstream --tags
git log --oneline $(git describe --tags --abbrev=0)..upstream/main
gh release view $(git describe --tags --abbrev=0) --repo <slug>
```

Work from `upstream/main` with a clean tree. Read the previous release's notes — it
is the house style you are matching.

Done when you have the commit list since the last tag, each one a merged PR with its
number.

## 2. Pick the version

Apply the version policy from the configuration. Read the diff of every
`feat`/`fix`/`perf` commit's public surface rather than trusting the commit subject;
a commit without `!` can still have moved a signature.

Done when you can name the version and justify it from a specific change.

## 3. Inventory the API delta

For each commit since the last tag, classify its effect on the public surface:

- **new API** — a public item that did not exist in the last release;
- **breaking API** — a public item whose signature, variants or semantics changed;
- **internal** — no consumer-visible surface (perf, refactor, tests, docs).

```sh
git diff $(git describe --tags --abbrev=0)..upstream/main -- '*/src/*' \
  | grep -nE '^[-+].*(pub fn|pub struct|pub enum|pub trait|pub type|pub use|pub async fn)'
```

Done when **every** commit is in exactly one of the three buckets and both API
buckets have the concrete item names — not "the compaction changes", but
`Compactable::compacted_events`, `Store::compact`, `replay::Compaction`.

## 4. Draft the notes

Follow [`release-notes-template.md`](release-notes-template.md). It carries the
required sections, the sample-code and migration bar, and the checks that keep the
snippets honest.

Done when every item from step 3's new-API bucket has sample code and every item
from the breaking bucket has a migration diff, and the snippets have been
compile-checked.

## 5. Open the bump PR

Every file the configuration lists carries the version, and the inter-crate pins must
move with the workspace version — otherwise publishing a downstream crate resolves
against the previous release.

```sh
git checkout -b chore/bump-X.Y.Z upstream/main
# edit each version file
# run the pre-flight gate from the configuration
git commit -am "chore: bump version to X.Y.Z"
git push upstream chore/bump-X.Y.Z
gh pr create --repo <slug> --base main \
  --title "chore: bump version to X.Y.Z" --body-file <(...)
```

The PR body is the changes list plus, when the release breaks, a `Breaking:`
paragraph naming the changed signatures.

Done when the PR is green and its link is in front of the user. **Stop here and ask
for the go-ahead to merge.** Merging is the user's call.

## 6. Tag the merged commit

```sh
git checkout main && git pull upstream main
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push upstream vX.Y.Z
```

Tag the bump commit itself, annotated, from a clean tree.

Done when `git describe --tags` on `upstream/main` reports `vX.Y.Z`.

## 7. Publish to crates.io

Publish exactly the crates the configuration lists, in the order it lists them —
dependency order, so each crate's dependencies already exist on crates.io at the new
version. Workspace members absent from that list are internal and stay unpublished.

```sh
cargo publish -p <first> --dry-run          # then without --dry-run
cargo publish -p <next>
```

`cargo publish` waits for the index by default; if a downstream publish still fails
to resolve the just-published version, re-run it after a minute.

Done when `cargo search <crate>` shows `X.Y.Z` for every published crate.

## 8. Publish the release page

```sh
gh release create vX.Y.Z --repo <slug> \
  --title "vX.Y.Z — <headline>" --notes-file notes.md
```

The headline is the one capability the release is about, in the previous releases'
voice.

Done when the release URL is in front of the user, alongside the crates.io versions
confirmed in step 7.
