#!/usr/bin/env python3
"""
Walk a GitHub repo's nested .gitmodules and emit the graph in a chosen format.

The edge that matters is (parent_repo, submodule_path) -> (child_repo, commit_sha):
the pinned commit is read from the parent's git tree (gitlink entry), so the same
dependency shows up at a different SHA under each parent that vendors it.

Requires: python3, and the `gh` CLI authenticated (`gh auth status`).

Examples
--------
  ./nested-gitmodules-graph.py grpc/grpc --format flow
  ./nested-gitmodules-graph.py pytorch/pytorch --ref v2.4.0 --max-depth 2 --format er
  ./nested-gitmodules-graph.py PaddlePaddle/Paddle --format json,sql --out-dir ./out
  ./nested-gitmodules-graph.py grpc/grpc --format dot | dot -Tsvg -o grpc.svg
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field

FORMATS = ("er", "flow", "dot", "json", "sql")
# out-dir filename suffix per format (er/flow share the .mmd extension, so keep the tag)
SUFFIX = {"er": "er.mmd", "flow": "flow.mmd", "dot": "dot", "json": "json", "sql": "sql"}


# --------------------------------------------------------------------------- gh

class GhError(RuntimeError):
    pass


def gh_json(path: str):
    """GET a GitHub API path, return parsed JSON. Raises GhError on failure (incl. 404)."""
    proc = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github+json", path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise GhError(proc.stderr.strip() or f"gh api {path} failed")
    return json.loads(proc.stdout)


# ----------------------------------------------------------------- .gitmodules

def parse_gitmodules(text: str) -> list[tuple[str, str]]:
    """Return [(path, url), ...] from a .gitmodules file body."""
    out, cur = [], {}

    def flush():
        if cur.get("path") and cur.get("url"):
            out.append((cur["path"], cur["url"]))

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        if line.lower().startswith("[submodule"):
            flush()
            cur.clear()
        elif "=" in line:
            k, v = line.split("=", 1)
            cur[k.strip().lower()] = v.strip()
    flush()
    return out


def resolve_slug(url: str) -> tuple[str | None, str]:
    """(host, 'owner/name'). host is None for anything we can't parse."""
    u = re.sub(r"\.git$", "", url.strip())
    m = re.match(r"(?:https?://|git://|ssh://(?:git@)?|git@)([^/:]+)[/:]+(.+)", u)
    if not m:
        return None, url
    host, path = m.group(1).lower(), m.group(2).strip("/")
    return host, path


# --------------------------------------------------------------------- walking

@dataclass
class Pin:
    parent: str          # 'owner/name'
    path: str
    child: str            # display slug ('owner/name' or 'host/owner/name')
    child_url: str
    commit: str | None    # gitlink SHA, None if the path has no matching gitlink
    child_on_github: bool


@dataclass
class Graph:
    root: str
    root_ref: str
    root_commit: str
    root_stars: int | None = None
    pins: list[Pin] = field(default_factory=list)
    has_gitmodules: set[str] = field(default_factory=set)   # display slugs that declare submodules
    commit_of: dict[str, str] = field(default_factory=dict)  # slug -> commit we inspected it at
    depth_reached: int = 0                                   # deepest submodule hop actually visited


class Walker:
    def __init__(self, max_depth: int | None, verbose: bool):
        self.max_depth = max_depth          # None = follow the chain all the way down
        self.verbose = verbose
        self._gitmodules: dict[tuple[str, str], list[tuple[str, str]]] = {}
        self._gitlinks: dict[tuple[str, str], dict[str, str]] = {}
        self._visited: set[tuple[str, str]] = set()

    def log(self, *a):
        if self.verbose:
            print("  #", *a, file=sys.stderr)

    def gitmodules(self, repo: str, sha: str) -> list[tuple[str, str]]:
        key = (repo, sha)
        if key not in self._gitmodules:
            try:
                data = gh_json(f"repos/{repo}/contents/.gitmodules?ref={sha}")
                body = base64.b64decode(data["content"]).decode("utf-8", "replace")
                self._gitmodules[key] = parse_gitmodules(body)
            except GhError:
                self._gitmodules[key] = []
        return self._gitmodules[key]

    def gitlinks(self, repo: str, sha: str) -> dict[str, str]:
        """path -> pinned commit SHA, for every gitlink in the tree."""
        key = (repo, sha)
        if key not in self._gitlinks:
            tree = gh_json(f"repos/{repo}/git/trees/{sha}?recursive=1")
            self._gitlinks[key] = {
                e["path"]: e["sha"] for e in tree.get("tree", []) if e.get("type") == "commit"
            }
            if tree.get("truncated"):
                print(f"warning: tree for {repo}@{sha[:7]} was truncated by the API",
                      file=sys.stderr)
        return self._gitlinks[key]

    def walk(self, g: Graph, repo: str, sha: str, level: int):
        """level = number of submodule hops from the root (root is level 0)."""
        if (repo, sha) in self._visited:
            return
        self._visited.add((repo, sha))

        mods = self.gitmodules(repo, sha)
        if not mods:
            return
        g.has_gitmodules.add(repo)
        g.commit_of.setdefault(repo, sha)
        g.depth_reached = max(g.depth_reached, level)
        if self.max_depth is not None and level >= self.max_depth:
            return

        links = self.gitlinks(repo, sha)
        for path, url in mods:
            host, ownername = resolve_slug(url)
            on_gh = host == "github.com"
            display = ownername if on_gh else (f"{host}/{ownername}" if host else url)
            commit = links.get(path)
            g.pins.append(Pin(repo, path, display, url, commit, on_gh))
            g.depth_reached = max(g.depth_reached, level + 1)
            self.log(f"L{level + 1}  {repo}  {path}  ->  {display}  @{(commit or '????')[:7]}")
            if on_gh and commit:
                self.walk(g, ownername, commit, level + 1)


def build_graph(repo: str, ref: str | None, max_depth: int | None, want_stars: bool,
                verbose: bool) -> Graph:
    head = gh_json(f"repos/{repo}/commits/{ref or 'HEAD'}")["sha"]
    g = Graph(root=repo, root_ref=ref or "HEAD", root_commit=head)
    if want_stars:
        try:
            g.root_stars = gh_json(f"repos/{repo}")["stargazers_count"]
        except GhError:
            pass
    Walker(max_depth, verbose).walk(g, repo, head, 0)
    return g


# --------------------------------------------------------------------- renders

def _san(slug: str) -> str:
    return "R_" + re.sub(r"[^0-9A-Za-z]+", "_", slug).strip("_")


def _nodes(g: Graph) -> list[str]:
    seen = [g.root]
    for p in g.pins:
        if p.child not in seen:
            seen.append(p.child)
    return seen


INIT = ('%%{init: {"theme":"base","themeVariables":{"fontFamily":"IBM Plex Mono, monospace",'
        '"fontSize":"11px","primaryColor":"#ffffff","primaryBorderColor":"#c9c2b6",'
        '"lineColor":"#9a9186","primaryTextColor":"#211d18"}}}%%')


def render_er(g: Graph, plain: bool) -> str:
    L = [] if plain else [INIT]
    L.append("erDiagram")
    for p in g.pins:
        sha7 = (p.commit or "unknown")[:7]
        L.append(f'  {_san(p.parent)} ||--o{{ {_san(p.child)} : "{p.path} @{sha7}"')
    L.append("")
    for slug in _nodes(g):
        L.append(f"  {_san(slug)} {{")
        L.append(f'    string slug "{slug}"')
        declares = slug in g.has_gitmodules or slug == g.root
        L.append(f'    bool has_gitmodules "{"yes" if declares else "no"}"')
        if slug == g.root and g.root_stars is not None:
            L.append(f'    int stars "{g.root_stars}"')
        L.append("  }")
    return "\n".join(L) + "\n"


def render_flow(g: Graph, plain: bool) -> str:
    L = [] if plain else [INIT]
    L.append("flowchart LR")
    L.append("  classDef nested fill:#f6e2da,stroke:#bf4127,color:#8f2f1c;")
    L.append("  classDef leaf fill:#ffffff,stroke:#c9c2b6,color:#211d18;")
    for slug in _nodes(g):
        nested = slug in g.has_gitmodules or slug == g.root
        L.append(f'  {_san(slug)}["{slug}"]:::{"nested" if nested else "leaf"}')
    for p in g.pins:
        sha7 = (p.commit or "unknown")[:7]
        L.append(f'  {_san(p.parent)} -->|"{p.path}<br/>@{sha7}"| {_san(p.child)}')
    return "\n".join(L) + "\n"


def render_dot(g: Graph) -> str:
    L = [
        "digraph submodules {",
        "  rankdir=LR;",
        '  bgcolor="transparent";',
        '  node [shape=box, style="filled,rounded", fillcolor="#ffffff", color="#c9c2b6",',
        '        fontname="IBM Plex Mono", fontsize=10, fontcolor="#211d18", margin="0.12,0.06"];',
        '  edge [color="#9a9186", fontname="IBM Plex Mono", fontsize=8, fontcolor="#6f675d", arrowsize=0.7];',
        "",
    ]
    for slug in _nodes(g):
        nested = slug in g.has_gitmodules or slug == g.root
        if nested:
            L.append(f'  {_san(slug)} [label="{slug}", fillcolor="#f6e2da", '
                     f'color="#bf4127", fontcolor="#8f2f1c"];')
        else:
            L.append(f'  {_san(slug)} [label="{slug}"];')
    L.append("")
    for p in g.pins:
        sha7 = (p.commit or "unknown")[:7]
        L.append(f'  {_san(p.parent)} -> {_san(p.child)} [label=" {p.path}\\n @{sha7}"];')
    L.append("}")
    return "\n".join(L) + "\n"


def render_json(g: Graph) -> str:
    doc = {
        "root": {
            "repo": g.root, "ref": g.root_ref, "commit": g.root_commit,
            "stars": g.root_stars,
        },
        "note": "pin = (parent, path) -> (child_repo, commit). commit is the gitlink SHA "
                "in the parent's tree; the same child is pinned differently per parent.",
        "pins": [
            {
                "parent": p.parent, "path": p.path, "child_repo": p.child,
                "child_url": p.child_url, "commit": p.commit,
                "child_has_gitmodules": p.child in g.has_gitmodules,
            }
            for p in g.pins
        ],
    }
    return json.dumps(doc, indent=2) + "\n"


def render_sql(g: Graph) -> str:
    slugs = _nodes(g)
    urls = {g.root: f"https://github.com/{g.root}"}
    for p in g.pins:
        urls.setdefault(p.child, p.child_url)
    ids = {s: i for i, s in enumerate(sorted(slugs), 1)}

    def q(v: str | None) -> str:
        return "NULL" if v is None else "'" + v.replace("'", "''") + "'"

    L = [
        f"-- Nested .gitmodules graph for {g.root} @ {g.root_commit[:10]}",
        "-- (parent_repo, path) -> (child_repo, commit_sha); the commit_sha is the pin.",
        "PRAGMA foreign_keys = ON;",
        "",
        "CREATE TABLE repo (",
        "  id             INTEGER PRIMARY KEY,",
        "  slug           TEXT NOT NULL UNIQUE,",
        "  url            TEXT,",
        "  has_gitmodules INTEGER NOT NULL DEFAULT 0",
        ");",
        "",
        "CREATE TABLE submodule_pin (",
        "  parent_id  INTEGER NOT NULL REFERENCES repo(id),",
        "  path       TEXT    NOT NULL,",
        "  child_id   INTEGER NOT NULL REFERENCES repo(id),",
        "  commit_sha TEXT,",
        "  PRIMARY KEY (parent_id, path)",
        ");",
        "",
    ]
    for s in sorted(slugs):
        declares = 1 if (s in g.has_gitmodules or s == g.root) else 0
        url = urls.get(s)
        L.append(f"INSERT INTO repo (id, slug, url, has_gitmodules) VALUES "
                 f"({ids[s]}, {q(s)}, {q(url)}, {declares});")
    L.append("")
    for p in g.pins:
        L.append(f"INSERT INTO submodule_pin (parent_id, path, child_id, commit_sha) VALUES "
                 f"({ids[p.parent]}, {q(p.path)}, {ids[p.child]}, {q(p.commit)});")
    L += [
        "",
        "-- dependencies vendored at more than one commit:",
        "-- SELECT c.slug, COUNT(DISTINCT p.commit_sha) n,",
        "--        GROUP_CONCAT(DISTINCT substr(p.commit_sha,1,7)) commits",
        "-- FROM submodule_pin p JOIN repo c ON c.id = p.child_id",
        "-- GROUP BY c.slug HAVING n > 1 ORDER BY n DESC;",
    ]
    return "\n".join(L) + "\n"


RENDERERS = {
    "er": lambda g, a: render_er(g, a.plain),
    "flow": lambda g, a: render_flow(g, a.plain),
    "dot": lambda g, a: render_dot(g),
    "json": lambda g, a: render_json(g),
    "sql": lambda g, a: render_sql(g),
}


# --------------------------------------------------------------------- entry

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Render a repo's nested .gitmodules graph (with pinned commit SHAs).")
    ap.add_argument("repo", help="owner/name on github.com")
    ap.add_argument("--ref", help="branch, tag, or SHA to start from (default: default branch HEAD)")
    ap.add_argument("--format", default="flow",
                    help=f"comma-separated: {', '.join(FORMATS)}, or 'all' (default: flow)")
    ap.add_argument("--max-depth", type=int, default=None, metavar="N",
                    help="cap the walk at N submodule hops below the root "
                         "(default: unlimited — follow every nested .gitmodules; "
                         "cycles are still guarded)")
    ap.add_argument("--out-dir", help="write <owner>-<name>.<ext> here instead of stdout")
    ap.add_argument("-o", "--out", help="write the single chosen format to this file")
    ap.add_argument("--plain", action="store_true",
                    help="omit the Mermaid %%%%{init}%%%% theming directive")
    ap.add_argument("--no-stars", action="store_true", help="skip the root star-count lookup")
    ap.add_argument("-v", "--verbose", action="store_true", help="trace the walk on stderr")
    args = ap.parse_args(argv)

    if not re.match(r"^[^/\s]+/[^/\s]+$", args.repo):
        ap.error("repo must look like 'owner/name'")
    fmts = list(FORMATS) if args.format == "all" else [f.strip() for f in args.format.split(",")]
    bad = [f for f in fmts if f not in FORMATS]
    if bad:
        ap.error(f"unknown format(s): {', '.join(bad)}")
    if args.out and len(fmts) != 1:
        ap.error("-o/--out takes exactly one --format")

    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("error: the `gh` CLI must be installed and authenticated (`gh auth login`)",
              file=sys.stderr)
        return 2

    try:
        g = build_graph(args.repo, args.ref, args.max_depth,
                        want_stars=not args.no_stars, verbose=args.verbose)
    except GhError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    cap = "unlimited" if args.max_depth is None else str(args.max_depth)
    if not g.pins:
        print(f"note: {args.repo}@{g.root_commit[:7]} has no .gitmodules "
              f"(or none within max-depth {cap})", file=sys.stderr)

    multi = sum(1 for _ in _multi_pinned(g))
    print(f"# {args.repo}@{g.root_commit[:7]}: {len(g.pins)} pins, "
          f"{len(_nodes(g))} repos, {len(g.has_gitmodules)} declare .gitmodules, "
          f"{multi} deps pinned at >1 commit, deepest hop L{g.depth_reached} "
          f"(max-depth {cap})", file=sys.stderr)

    base = args.repo.replace("/", "-")
    for f in fmts:
        text = RENDERERS[f](g, args)
        if args.out_dir:
            import os
            os.makedirs(args.out_dir, exist_ok=True)
            dest = os.path.join(args.out_dir, f"{base}.{SUFFIX[f]}")
            with open(dest, "w") as fh:
                fh.write(text)
            print(f"wrote {dest}", file=sys.stderr)
        elif args.out:
            with open(args.out, "w") as fh:
                fh.write(text)
            print(f"wrote {args.out}", file=sys.stderr)
        else:
            if len(fmts) > 1:
                print(f"\n===== {f} =====")
            sys.stdout.write(text)
    return 0


def _multi_pinned(g: Graph):
    by_child: dict[str, set[str]] = {}
    for p in g.pins:
        if p.commit:
            by_child.setdefault(p.child, set()).add(p.commit)
    for child, shas in by_child.items():
        if len(shas) > 1:
            yield child, shas


if __name__ == "__main__":
    sys.exit(main())
