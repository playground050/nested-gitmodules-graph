# nested-gitmodules-graph

Walk a GitHub repository's **nested `.gitmodules`** and emit the dependency graph in
whichever format you ask for — an indented tree, a Mermaid ER diagram, a Mermaid
flowchart, Graphviz DOT, raw JSON, or a SQLite schema + seed.

A repo's `.gitmodules` points at submodule repositories; some of *those* repos have their
own `.gitmodules`; and so on. This script follows that chain and records, for every hop,
the exact commit the submodule is pinned to.

```
$ ./nested-gitmodules-graph.py grpc/grpc
grpc/grpc @6e5ac36  ★45296
├─ third_party/abseil-cpp → abseil/abseil-cpp @76bb243
├─ third_party/bloaty → google/bloaty @60209eb
│  ├─ third_party/protobuf → protocolbuffers/protobuf @bc1773c
│  │  ├─ third_party/benchmark → google/benchmark @5b7683f
│  │  └─ third_party/googletest → google/googletest @5ec7f0c
│  └─ third_party/re2 → google/re2 @5bd6137
├─ third_party/opentelemetry-cpp → open-telemetry/opentelemetry-cpp @ced7986
│  └─ third_party/prometheus-cpp → jupp0r/prometheus-cpp @e5fada4
│     ├─ 3rdparty/googletest → google/googletest @e2239ee
│     └─ 3rdparty/civetweb → civetweb/civetweb @d7ba35b
└─ … (google/googletest also appears at 52eb810, 565f1b8, f8d7d77 elsewhere)
```

## Why the commit hash is the point

A submodule edge is **not** `repo → repo`. It is:

```
(parent_repo, submodule_path) → (child_repo, commit_sha)
```

The pinned `commit_sha` is read from the parent repo's git tree (the *gitlink* entry —
what `git submodule status` prints). The same dependency is pinned to a **different**
commit under each parent that vendors it, so a plain repo-to-repo graph silently drops
information that matters for builds and CVEs.

Example — one full run over `grpc/grpc`, dependencies pinned at more than one commit:

| dependency | distinct pins |
| --- | --- |
| `google/googletest` | `52eb810` · `565f1b8` · `5ec7f0c` · `e2239ee` · `f8d7d77` |
| `google/benchmark` | `12235e2` · `3441176` · `5b7683f` |
| `abseil/abseil-cpp` | `76bb243` · `5dd2407` |
| `protocolbuffers/protobuf` | `35cd01f` · `bc1773c` |
| `google/re2` | `0c5616d` · `5bd6137` |

Every output format carries the SHA: `tree` / `er` / `flow` / `dot` show `@<sha7>`,
`json` stores the full `commit`, `sql` stores `submodule_pin.commit_sha`.

## Requirements

- Python 3.9+
- The [`gh` CLI](https://cli.github.com/), authenticated (`gh auth status`). All GitHub
  API calls go through `gh api`, so it uses your existing auth and rate limit.

## Usage

```
./nested-gitmodules-graph.py <owner>/<repo> [options]
```

| option | meaning |
| --- | --- |
| `repo` (positional) | `owner/name` on github.com |
| `--format` | comma-separated `tree,er,flow,dot,json,sql`, or `all` (default: `tree`) |
| `--ref` | branch, tag, or SHA to start from (default: the default branch's HEAD) |
| `--max-depth N` | cap the walk at `N` submodule hops below the root (default: **unlimited** — follow every nested `.gitmodules`; `(repo, commit)` cycles are still guarded) |
| `--out-dir DIR` | write `<owner>-<repo>.<format>.<ext>` into `DIR` instead of stdout |
| `-o FILE` | write the single chosen `--format` to `FILE` |
| `--plain` | omit the Mermaid `%%{init}%%` theming directive |
| `--no-stars` | skip the root repo's star-count lookup (one fewer API call) |
| `-v` | trace the walk on stderr |

A one-line summary always goes to stderr:

```
# grpc/grpc@6e5ac36: 37 pins, 27 repos, 5 declare .gitmodules, 7 deps pinned at >1 commit, deepest hop L3 (max-depth unlimited)
```

The default walk is unbounded — it follows the `.gitmodules` chain as deep as it goes.
Pass `--max-depth 1` for just the root's direct submodules, `--max-depth 2` for two hops,
and so on. `--max-depth` only ever *reduces* work; the `(repo, commit)` cache and
visited-set mean a bounded walk terminates even on a cyclic graph.

### Examples

```bash
# flowchart to stdout (default format)
./nested-gitmodules-graph.py grpc/grpc

# all five formats into ./out/
./nested-gitmodules-graph.py grpc/grpc --format all --out-dir out

# ER diagram at a specific tag
./nested-gitmodules-graph.py pytorch/pytorch --ref v2.4.0 --format er

# pipe DOT straight into Graphviz
./nested-gitmodules-graph.py grpc/grpc --format dot | dot -Tsvg -o grpc.svg

# load the relational model
./nested-gitmodules-graph.py grpc/grpc --format sql | sqlite3 grpc.db
```

### The SQLite model

Two tables — a self-referential many-to-many on `repo` through a pin row:

```sql
CREATE TABLE repo (
  id             INTEGER PRIMARY KEY,
  slug           TEXT NOT NULL UNIQUE,          -- "owner/name"
  url            TEXT,
  has_gitmodules INTEGER NOT NULL DEFAULT 0     -- does this repo declare submodules
);

CREATE TABLE submodule_pin (
  parent_id  INTEGER NOT NULL REFERENCES repo(id),
  path       TEXT    NOT NULL,                  -- path from .gitmodules
  child_id   INTEGER NOT NULL REFERENCES repo(id),
  commit_sha TEXT,                              -- the pin (gitlink SHA in parent's tree)
  PRIMARY KEY (parent_id, path)
);

-- which dependencies are vendored at more than one commit?
SELECT c.slug,
       COUNT(DISTINCT p.commit_sha)                     AS n,
       GROUP_CONCAT(DISTINCT substr(p.commit_sha,1,7))  AS commits
FROM   submodule_pin p
JOIN   repo c ON c.id = p.child_id
GROUP  BY c.slug
HAVING n > 1
ORDER  BY n DESC;
```

## How it works

For each `(repo, commit)` node:

1. `gh api repos/<repo>/contents/.gitmodules?ref=<commit>` — the `path → url` map.
   Empty / 404 ⇒ leaf node, stop.
2. `gh api "repos/<repo>/git/trees/<commit>?recursive=1"` — tree entries of
   `type == "commit"` are gitlinks; each carries the pinned `sha`.
3. Join by path, emit one pin per submodule, recurse into children that are on github.com
   and themselves declare `.gitmodules`. By default this continues to the bottom of the
   chain; `--max-depth N` stops it at `N` hops.

`(repo, commit)` pairs are cached and de-duplicated, so a diamond in the graph is fetched
once and a cycle cannot loop forever. Cost is ~2 `gh api` calls per distinct
`(repo, commit)` that declares `.gitmodules`, plus one per leaf.

## Limitations

- **github.com only.** Submodules hosted elsewhere (e.g. `gitlab.com/libeigen/eigen`) are
  recorded as leaf nodes labelled `<host>/<owner>/<name>` — the walk can't follow them
  because it goes through `gh api`.
- **In the graph formats (`er`/`flow`/`dot`) `has_gitmodules` is per repo, not per
  commit.** If a repo nests at one pinned commit but not another, its node still shows as
  "declares .gitmodules". The `tree` format is exact — it knows the commit at each spot
  and only expands / annotates where that commit actually has submodules.
- Very large trees can be truncated by the GitHub API; the script warns on stderr when
  that happens.
- Wide graphs overwhelm `er` and `flow`; use `tree` or `dot` past ~25 edges.

## Format comparison

| | renders on GitHub | shows per-commit truth | best for |
| --- | --- | --- | --- |
| `tree` (indented outline) | yes (fenced) | **yes** | "what's in here" — reads anywhere, no rendering |
| `er` (Mermaid `erDiagram`) | yes | no | the schema + a small slice; has `\|\|--o{` cardinality |
| `flow` (Mermaid `flowchart`) | yes | no | the real shape as a picture, in a README |
| `dot` (Graphviz) | no (commit the SVG) | no | the full multi-repo graph, every level |
| `json` | — | yes (`parent_commit`) | feeding another tool |
| `sql` | — | yes | pivot tables / `HAVING COUNT(DISTINCT commit) > 1` |

For "which dependency diverges", the query over `sql` (or a pivot of `json`) beats every
diagram: rows = dependency, and every distinct pinned commit is one `GROUP_CONCAT` cell.

## Examples in this repo

`examples/grpc-grpc.*` — every format for `grpc/grpc` at the time of generation
(default unlimited depth). Regenerate with
`./nested-gitmodules-graph.py grpc/grpc --format all --out-dir examples`.

Three real repos with nested `.gitmodules`, for testing:

- `pytorch/pytorch` — `third_party/ideep` → `intel/ideep` → `mkl-dnn`; also `tensorpipe`, `kineto`, `fbgemm`
- `grpc/grpc` — `third_party/bloaty` → `google/bloaty` → protobuf, abseil, re2, …; also `opentelemetry-cpp`
- `PaddlePaddle/Paddle` — `third_party/openvino` → `openvinotoolkit/openvino` (~30 submodules)
