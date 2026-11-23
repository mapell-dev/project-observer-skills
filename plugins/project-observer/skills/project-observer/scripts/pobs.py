#!/usr/bin/env python3
"""pobs.py: the mechanics behind the project-observer and project-review skills.

Usage: python3 pobs.py [--log DIR] <command> [options]

  root              print the log directory for the git project in the current directory
  init              create the log directory, ignore it locally, seed the denylist
  next-id KIND      KIND is observations or proposals; print the next id, raise the floor
  lint              check every record's frontmatter; exit 1 on errors
  leakcheck [PATH]  check generalized entries (default) or the given files against the
                    denylist; record the result in each generalized entry; exit 1 on a hit
  list [KIND]       one line per record; KIND is observations (default), generalized
                    or proposals
  archive           move observations resolved before today into observations/archive/
  counts            print counts for a period (lessons, changes, held, leaks, recurrences,
                    review minutes, project-review proposals)
                    --start YYYY-MM-DD  first day of week 1 (without it: ISO weeks, all dates)
                    --weeks N           run length in weeks (default 8)
                    --verify-commits    check each resolution_commit exists and touches
                                        the listed resolution_files
  selftest          run every command on the bundled fixture (fake project terms)

The log directory defaults to <main checkout>/.project-observer, found through
`git rev-parse --git-common-dir`, so every worktree of a project shares one log.
Python 3.9+, standard library only.
"""
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LOG_NAME = ".project-observer"
CATEGORIES = ["test-design", "fixtures-data", "flaky-tests", "tooling", "agent-behavior", "other"]
STATUS = {"open", "actioned", "declined", "superseded", "parked"}
RESOLVED = {"actioned", "declined", "superseded"}
HELD = {"", "held", "not-held", "ambiguous"}
HUMAN = {"pending", "ok", "leak"}
OUTCOME = {"pending", "accepted", "declined"}
KIND = {"observer", "diff"}
REQUIRED = {
    "observations": ["id", "title", "status", "category", "area", "date", "session_context"],
    "generalized": ["id", "source", "title", "date", "human_read"],
    "proposals": ["id", "title", "date", "run", "lessons", "outcome"],
    "reviews": ["date", "kind"],
}
BUILTIN = [("url", re.compile(r"https?://\S+")),
           ("email", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"))]
PUBLIC_DOMAINS = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com",
                  "icloud.com", "me.com", "proton.me", "protonmail.com",
                  "users.noreply.github.com", "noreply.github.com", "github.com",
                  "gitlab.com", "bitbucket.org"}
FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)


# ---------- frontmatter ----------

def _unquote(s):
    s = s.strip()
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'" else s


def parse(text):
    """Flat `key: value` frontmatter; `[a, b]` is a list. None if there is no header."""
    m = FM_RE.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line[0] in " \t":
            continue
        key, sep, val = line.partition(":")
        if not sep:
            continue
        val = re.sub(r"\s{2,}#.*$", "", val).strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key.strip()] = [_unquote(x) for x in val[1:-1].split(",") if x.strip()]
        else:
            fm[key.strip()] = _unquote(val)
    return fm


def set_field(path, key, value):
    """Rewrite one frontmatter field of one file; nothing else in the file changes."""
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    lines = m.group(1).splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"{re.escape(key)}\s*:", line):
            lines[i] = f"{key}: {value}"
            break
    else:
        lines.append(f"{key}: {value}")
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + text[m.end():], encoding="utf-8")


def as_int(v):
    try:
        return int(str(v).strip())
    except ValueError:
        return None


def as_date(v):
    try:
        return dt.date.fromisoformat(str(v).strip())
    except ValueError:
        return None


def load(log, kind, archive=False):
    """[(path, frontmatter or None)] for one record directory, sorted by name."""
    dirs = [log / kind] + ([log / kind / "archive"] if archive else [])
    out = []
    for d in dirs:
        if d.is_dir():
            out += [(p, parse(p.read_text(encoding="utf-8"))) for p in sorted(d.glob("*.md"))]
    return out


# ---------- log location ----------

def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def project_root(cwd="."):
    common = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)
    if not common or Path(common).name != ".git":
        sys.exit("pobs: not inside a git checkout with a .git directory; pass --log DIR")
    return Path(common).parent


def cmd_root(log, args):
    print(log)


def seed_terms(root):
    terms = {root.name}
    for url in (git(["remote", "-v"], root) or "").split():
        if "/" not in url and "@" not in url:
            continue
        parts = re.split(r"[/:@]+", re.sub(r"^\w+://", "", url).removesuffix(".git"))
        terms.update(p for p in parts if p and p not in PUBLIC_DOMAINS and p != "git")
    for email in (git(["log", "-n", "500", "--format=%ae%n%ce"], root) or "").split():
        domain = email.rpartition("@")[2].lower()
        if domain and domain not in PUBLIC_DOMAINS:
            terms.add(domain)
    return sorted(t for t in terms if len(t) > 1)


def cmd_init(log, args):
    root = log.parent
    for d in ["observations/archive", "generalized", "proposals", "reviews"]:
        (log / d).mkdir(parents=True, exist_ok=True)
    for floor in [log / "observations/archive/.id-floor", log / "proposals/.id-floor"]:
        if not floor.exists():
            floor.write_text("0\n")
    deny = log / "denylist.txt"
    if not deny.exists():
        terms = seed_terms(root)
        deny.write_text(
            "# Project terms that must never appear in a generalized entry.\n"
            "# One term per line, case-insensitive. Add client, product, service, team,\n"
            "# people, domain and ticket-prefix names (e.g. ABC-). Lines starting with # are ignored.\n"
            "# Seeded by `pobs.py init` from the repo name, remotes and commit e-mail domains;\n"
            "# delete seeded terms that are ordinary words.\n" + "".join(t + "\n" for t in terms))
    exclude = Path(git(["rev-parse", "--path-format=absolute", "--git-common-dir"], root)) / "info/exclude"
    exclude.parent.mkdir(exist_ok=True)
    rule = f"/{LOG_NAME}/"
    lines = exclude.read_text().splitlines() if exclude.exists() else []
    if rule not in lines:
        with exclude.open("a") as f:
            f.write(f"\n# project-observer log: local only, never committed\n{rule}\n")
    ignored = subprocess.run(["git", "check-ignore", "-q", f"{LOG_NAME}/denylist.txt"], cwd=root).returncode == 0
    tracked = git(["ls-files", LOG_NAME], root)
    print(f"log: {log}")
    print(f"ignored by git: {'yes' if ignored else 'NO'}; tracked files inside: {tracked or 'none'}")
    print(f"denylist: {deny} ({len(denylist(log))} terms)")
    if not ignored or tracked:
        sys.exit("pobs: the log is not safely ignored; fix before writing any observation")


# ---------- ids ----------

def cmd_next_id(log, args):
    if not args or args[0] not in ("observations", "proposals"):
        sys.exit("pobs: next-id observations|proposals")
    base = log / args[0]
    floor = base / "archive/.id-floor" if args[0] == "observations" else base / ".id-floor"
    if not floor.exists():
        sys.exit(f"pobs: {floor} missing; run init first")
    names = [p.name for d in (base, base / "archive") if d.is_dir() for p in d.glob("*.md")]
    ids = [int(m.group()) for n in names if (m := re.match(r"\d+", n))]
    if names and not ids:
        sys.exit("pobs: ID COMMAND BROKEN: records exist but no numeric prefix was read")
    nxt = max(ids + [as_int(floor.read_text()) or 0]) + 1
    floor.write_text(f"{nxt}\n")
    print(f"{nxt:04d}")


# ---------- lint ----------

def lint(log):
    errors, warnings = [], []
    obs = load(log, "observations", archive=True)
    by_id = {}
    for p, fm in obs:
        if fm and as_int(fm.get("id")) is not None:
            by_id.setdefault(as_int(fm["id"]), []).append((p, fm))

    def check_required(kind, p, fm):
        if fm is None:
            errors.append(f"{p}: no frontmatter")
            return False
        for k in REQUIRED[kind]:
            if fm.get(k) in (None, "", []):
                errors.append(f"{p}: missing {k}")
        if fm.get("pilot", "") not in ("", "true", "false"):
            errors.append(f"{p}: pilot must be true, false or empty")
        return True

    for i, entries in by_id.items():
        if len(entries) > 1:
            warnings.append(f"observation id {i} used by {len(entries)} files; renumber one")
    for p, fm in obs:
        if not check_required("observations", p, fm):
            continue
        if as_int(fm.get("id")) != as_int(p.name.split("-")[0]):
            errors.append(f"{p}: id does not match the filename prefix")
        st = fm.get("status", "")
        if st not in STATUS:
            errors.append(f"{p}: status {st!r} not in {sorted(STATUS)}")
        if fm.get("category") not in CATEGORIES:
            errors.append(f"{p}: category {fm.get('category')!r} not in {CATEGORIES}")
        if not as_date(fm.get("date")):
            errors.append(f"{p}: date is not YYYY-MM-DD")
        if fm.get("already_held", "") not in HELD:
            errors.append(f"{p}: already_held must be held, not-held or ambiguous")
        if st == "parked" and not fm.get("parked_until"):
            errors.append(f"{p}: parked without parked_until")
        if st in RESOLVED and not (as_date(fm.get("resolved")) and fm.get("resolution")):
            errors.append(f"{p}: {st} needs resolved (date) and resolution")
        if fm.get("resolution_files") and not fm.get("resolution_commit"):
            warnings.append(f"{p}: project file changed, commit not recorded yet (not counted as a change yet)")
        if fm.get("recurs"):
            t = as_int(fm["recurs"])
            if t not in by_id or t == as_int(fm["id"]):
                errors.append(f"{p}: recurs points at {fm['recurs']}, which is not another observation")
            elif by_id[t][0][1].get("recurs"):
                errors.append(f"{p}: recurs must name the first observation of the lesson, not {t}")

    for p, fm in load(log, "generalized"):
        if not check_required("generalized", p, fm):
            continue
        if as_int(fm.get("source")) not in by_id:
            errors.append(f"{p}: source {fm.get('source')} is not an observation")
        if fm.get("leak_check") not in ("pass", "fail"):
            errors.append(f"{p}: no leak_check result; run `pobs.py leakcheck`")
        if fm.get("human_read") not in HUMAN:
            errors.append(f"{p}: human_read must be pending, ok or leak")
        if fm.get("human_read") in ("ok", "leak") and fm.get("human_read_first") not in ("ok", "leak"):
            errors.append(f"{p}: human_read is set but human_read_first is not")
        if fm.get("exported_to") and not (fm.get("leak_check") == "pass" and fm.get("human_read") == "ok"):
            errors.append(f"{p}: exported before passing both the leak check and the human read")

    for p, fm in load(log, "proposals"):
        if not check_required("proposals", p, fm):
            continue
        lessons = fm.get("lessons") if isinstance(fm.get("lessons"), list) else []
        for lesson in lessons:
            if as_int(lesson) not in by_id:
                errors.append(f"{p}: lesson {lesson} is not an observation in the log")
        oc = fm.get("outcome")
        if oc not in OUTCOME:
            errors.append(f"{p}: outcome must be pending, accepted or declined")
        if oc in ("accepted", "declined") and not as_date(fm.get("outcome_date")):
            errors.append(f"{p}: {oc} needs outcome_date")
        if oc == "declined" and not fm.get("reason"):
            warnings.append(f"{p}: declined without a reason")
        if not (log / "reviews" / f"{fm.get('run')}.md").exists():
            warnings.append(f"{p}: run {fm.get('run')} has no record in reviews/")

    for p, fm in load(log, "reviews"):
        if not check_required("reviews", p, fm):
            continue
        if fm.get("kind") not in KIND:
            errors.append(f"{p}: kind must be observer or diff")
        if fm.get("minutes", "") == "":
            warnings.append(f"{p}: minutes not recorded yet (review still open)")
        elif as_int(fm.get("minutes")) is None:
            errors.append(f"{p}: minutes must be a whole number")
    return errors, warnings


def cmd_lint(log, args):
    errors, warnings = lint(log)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("error:", e)
    print(f"lint: {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


# ---------- leak check ----------

def denylist(log):
    f = log / "denylist.txt"
    if not f.exists():
        return []
    return [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def _norm(s):
    return re.sub(r"[^0-9a-z]", "", s.lower())


def leak_hits(text, terms):
    """Denylist terms and built-in patterns found in text.

    Terms of 5+ letters/digits match after removing case, spaces and punctuation from
    both sides, so "Acme Pay" also catches "acme-pay" and "AcmePay". Shorter terms
    match as words (a trailing '-' or '.' leaves the right side open: "ABC-" hits
    "ABC-123").
    """
    hits, ntext = [], _norm(text)
    for t in terms:
        n = _norm(t)
        if len(n) >= 5:
            found = n in ntext
        elif n:
            left = r"(?<![0-9A-Za-z])" if t[0].isalnum() else ""
            right = r"(?![0-9A-Za-z])" if t[-1].isalnum() else ""
            found = re.search(left + re.escape(t) + right, text, re.I) is not None
        else:
            found = False
        if found:
            hits.append(t)
    for name, rx in BUILTIN:
        hits += [f"{name}:{m.group()}" for m in rx.finditer(text)]
    return hits


def cmd_leakcheck(log, args):
    terms = denylist(log)
    if not terms:
        print(f"pobs: {log / 'denylist.txt'} has no terms; a check against nothing passes everything")
        sys.exit(2)
    files = [Path(a) for a in args] or sorted((log / "generalized").glob("*.md"))
    gen_dir = (log / "generalized").resolve()
    today = dt.date.today().isoformat()
    failed = 0
    for f in files:
        hits = leak_hits(f.name + "\n" + f.read_text(encoding="utf-8"), terms)
        result = "fail" if hits else "pass"
        failed += bool(hits)
        print(f"{result.upper()} {f}" + (f": {', '.join(hits)}" if hits else ""))
        if f.resolve().parent == gen_dir:
            fm = parse(f.read_text(encoding="utf-8")) or {}
            if not fm.get("leak_check_first"):
                set_field(f, "leak_check_first", result)
            set_field(f, "leak_check", result)
            set_field(f, "leak_checked", today)
    print(f"leakcheck: {len(files)} files, {failed} with hits, {len(terms)} denylist terms")
    sys.exit(1 if failed else 0)


# ---------- list ----------

def cmd_list(log, args):
    kind = args[0] if args else "observations"
    if kind not in ("observations", "generalized", "proposals"):
        sys.exit("pobs: list observations|generalized|proposals")
    gen = {as_int(fm.get("source")) for _, fm in load(log, "generalized") if fm}
    rows = load(log, kind, archive=kind == "observations")
    for p, fm in rows:
        if fm is None:
            print(f"???? no frontmatter: {p.name}")
            continue
        i = f"{as_int(fm.get('id')) or 0:04d}"
        if kind == "observations":
            print(f"{i} {fm.get('status') or 'open'} {fm.get('category')} recurs:{fm.get('recurs') or '-'} "
                  f"generalized:{'yes' if as_int(fm.get('id')) in gen else 'no'} | {fm.get('title')}")
        elif kind == "generalized":
            print(f"{i} leak:{fm.get('leak_check') or '-'} human:{fm.get('human_read')} "
                  f"exported:{','.join(fm.get('exported_to') or []) or '-'} | {fm.get('title')}")
        else:
            print(f"{i} {fm.get('outcome')} lessons:{','.join(fm.get('lessons') or [])} "
                  f"run:{fm.get('run')} | {fm.get('title')}")
    print(f"list: {len(rows)} {kind}")


# ---------- archive ----------

def cmd_archive(log, args):
    today = dt.date.today()
    moved = 0
    for p, fm in load(log, "observations"):
        if not fm or fm.get("status") not in RESOLVED:
            continue
        when = as_date(fm.get("resolved"))
        if when is None:
            set_field(p, "resolved", today.isoformat())
        elif when < today:
            p.rename(log / "observations/archive" / p.name)
            moved += 1
    print(f"archive: moved {moved}")


# ---------- counts ----------

def pct(a, b):
    return f"{a} of {b} ({round(100 * a / b)}%)" if b else f"{a} of 0"


def cmd_counts(log, args):
    start, weeks, verify = None, 8, False
    it = iter(args)
    for a in it:
        if a == "--start":
            start = as_date(next(it, ""))
            if not start:
                sys.exit("pobs: --start needs YYYY-MM-DD")
        elif a == "--weeks":
            weeks = as_int(next(it, "")) or sys.exit("pobs: --weeks needs a number")
        elif a == "--verify-commits":
            verify = True
        else:
            sys.exit(f"pobs: unknown option {a}")
    end = start + dt.timedelta(weeks=weeks) if start else None

    def week(d):
        if start:
            return f"{(d - start).days // 7 + 1}"
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"

    def in_window(d):
        return d is not None and (start is None or start <= d < end)

    def pilot(fm):
        return fm.get("pilot") == "true"

    obs_all = [fm for _, fm in load(log, "observations", archive=True) if fm and as_date(fm.get("date"))]
    by_id = {as_int(fm["id"]): fm for fm in obs_all}
    obs = [fm for fm in obs_all if not pilot(fm)]
    window = [fm for fm in obs if in_window(as_date(fm["date"]))]
    lessons = [fm for fm in window if not fm.get("recurs")]
    recurs = [fm for fm in window if fm.get("recurs")]

    print("# Project observer counts")
    print(f"log: {log}")
    print(f"window: {start} to {end - dt.timedelta(days=1)} ({weeks} weeks)" if start
          else "window: all dates, ISO weeks (pass --start to count weeks from a start date)")
    print(f"lessons: {len(lessons)} distinct, {len(recurs)} recurrences, "
          f"{len(obs) - len(window)} outside the window")
    n_pilot = {k: sum(1 for _, fm in load(log, k, archive=k == "observations") if fm and pilot(fm))
               for k in ("observations", "proposals", "reviews")}
    print("pilot entries left out of every count: " + ", ".join(f"{v} {k}" for k, v in n_pilot.items()))

    print("\n## lessons per week by category")
    print("| week | " + " | ".join(CATEGORIES) + " | recurrences |")
    print("|---" * (len(CATEGORIES) + 2) + "|")
    rows = sorted({week(as_date(fm["date"])) for fm in window}, key=lambda w: (len(w), w))
    for w in rows:
        cells = [sum(1 for fm in lessons if week(as_date(fm["date"])) == w and fm.get("category") == c)
                 for c in CATEGORIES]
        rec = sum(1 for fm in recurs if week(as_date(fm["date"])) == w)
        print(f"| {w} | " + " | ".join(map(str, cells)) + f" | {rec} |")

    print("\n## lessons turned into a committed change in a project file")
    done = [fm for fm in lessons if fm.get("status") == "actioned" and fm.get("resolution_commit")
            and in_window(as_date(fm.get("resolved")))]
    waiting = [fm for fm in lessons if fm.get("resolution_files") and not fm.get("resolution_commit")]
    print(f"changed a project file, with commit: {pct(len(done), len(lessons))}")
    print(f"change made, commit not recorded yet: {len(waiting)}")
    if verify:
        problems = []
        for fm in done:
            sha = fm["resolution_commit"]
            changed = git(["show", "--name-only", "--format=", sha], log.parent)
            if changed is None:
                problems.append(f"{fm['id']}: commit {sha} not found")
                continue
            files = fm.get("resolution_files") or []
            files = files if isinstance(files, list) else [files]
            missing = [f for f in files if f not in changed.splitlines()]
            if not files or missing:
                problems.append(f"{fm['id']}: commit {sha} does not touch {missing or 'any listed file'}")
        print(f"commit check: {len(done) - len(problems)} ok, {len(problems)} problems")
        for line in problems:
            print("  -", line)

    print("\n## lessons CLAUDE.md or auto-memory already held (the user's end-of-period label)")
    held = {v: sum(1 for fm in lessons if fm.get("already_held", "") == v) for v in HELD}
    print(f"already held: held {held['held']}, not-held {held['not-held']}, "
          f"ambiguous {held['ambiguous']}, unlabeled {held['']}")

    print("\n## leaks in generalized entries")
    terms = denylist(log)
    gens = [(p, fm) for p, fm in load(log, "generalized") if fm]
    lesson_ids = {as_int(fm["id"]) for fm in lessons}
    gens = [(p, fm) for p, fm in gens if as_int(fm.get("source")) in lesson_ids]
    covered = {as_int(fm.get("source")) for _, fm in gens}
    first_fail = sum(1 for _, fm in gens if fm.get("leak_check_first") == "fail")
    now_fail = sum(1 for p, _ in gens if leak_hits(p.name + "\n" + p.read_text(encoding="utf-8"), terms))
    human = {v: sum(1 for _, fm in gens if fm.get("human_read") == v) for v in HUMAN}
    missed = sum(1 for _, fm in gens if fm.get("human_read_first") == "leak"
                 and fm.get("leak_check_first") == "pass")
    print(f"generalized: {len(covered)} of {len(lessons)} lessons (missing: {len(lesson_ids - covered)})")
    print(f"leak check, first run failed: {first_fail}")
    print(f"leak check, failing now: {now_fail} (re-run against {len(terms)} denylist terms)")
    print(f"human read: ok {human['ok']}, leak {human['leak']}, pending {human['pending']}")
    print(f"leaks the script missed (first human read: leak, first leak check: pass): {missed}")

    print("\n## recurrence")
    after, before, after_ids = 0, 0, set()
    for fm in recurs:
        target = by_id.get(as_int(fm["recurs"]), {})
        fixed = as_date(target.get("resolved"))
        if target.get("resolution_commit") and fixed and fixed <= as_date(fm["date"]):
            after += 1
            after_ids.add(as_int(fm["recurs"]))
        else:
            before += 1
    print(f"recurrences after the fix landed: {after} (lessons: {', '.join(map(str, sorted(after_ids))) or 'none'})")
    print(f"repeats before a fix: {before}")

    print("\n## review minutes")
    revs = [fm for _, fm in load(log, "reviews") if fm and not pilot(fm) and in_window(as_date(fm.get("date")))]
    print("| week | observer reviews | observer minutes | diff reviews | diff minutes |")
    print("|---|---|---|---|---|")
    for w in sorted({week(as_date(fm["date"])) for fm in revs}, key=lambda w: (len(w), w)):
        cell = []
        for k in ("observer", "diff"):
            rs = [fm for fm in revs if fm.get("kind") == k and week(as_date(fm["date"])) == w]
            cell += [len(rs), sum(as_int(fm.get("minutes")) or 0 for fm in rs)]
        print(f"| {w} | " + " | ".join(map(str, cell)) + " |")
    for k in ("observer", "diff"):
        rs = [fm for fm in revs if fm.get("kind") == k]
        print(f"{k}: {sum(as_int(fm.get('minutes')) or 0 for fm in rs)} min in {len(rs)} reviews")

    print("\n## project-review proposals")
    props = [fm for _, fm in load(log, "proposals") if fm and not pilot(fm) and in_window(as_date(fm.get("date")))]
    oc = {v: sum(1 for fm in props if fm.get("outcome") == v) for v in OUTCOME}
    print(f"proposals: {len(props)} (accepted {oc['accepted']}, declined {oc['declined']}, pending {oc['pending']})")
    print(f"proposals accepted, of decided: {pct(oc['accepted'], oc['accepted'] + oc['declined'])}")
    cited = {}
    for fm in props:
        for lesson in fm.get("lessons") or []:
            cited[as_int(lesson)] = cited.get(as_int(lesson), 0) + 1
    print("proposals per lesson: " + (", ".join(f"{k}: {v}" for k, v in sorted(cited.items())) or "none"))


# ---------- selftest ----------

def cmd_selftest(log_unused, args):
    here = Path(__file__).resolve().parent
    fixture = here / "fixture"
    me = [sys.executable, str(Path(__file__).resolve())]
    tmp = Path(tempfile.mkdtemp(prefix="pobs-selftest-"))
    repo = tmp / "quokka-ledger"
    checks = 0

    def run(*a, code=0):
        r = subprocess.run([*me, *a], cwd=repo, capture_output=True, text=True)
        out = r.stdout + r.stderr
        assert r.returncode == code, f"{a}: exit {r.returncode}, expected {code}\n{out}"
        return out

    def expect(out, *lines):
        nonlocal checks
        for line in lines:
            assert line in out, f"expected line not found: {line!r}\n--- output ---\n{out}"
            checks += 1

    try:
        repo.mkdir()
        for c in (["init", "-q"], ["config", "user.email", "dev@bramblecorp.example"],
                  ["config", "user.name", "Dev"]):
            subprocess.run(["git", *c], cwd=repo, check=True)
        (repo / "CLAUDE.md").write_text("# rules\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "rules"], cwd=repo, check=True)
        sha = git(["rev-parse", "--short", "HEAD"], repo)

        # root and init: log lives in the checkout, ignored locally, denylist seeded
        expect(run("root"), str(repo.resolve() / LOG_NAME))
        expect(run("init"), "ignored by git: yes; tracked files inside: none")
        log = repo / LOG_NAME
        deny = (log / "denylist.txt").read_text()
        expect(deny, "bramblecorp.example\n", "quokka-ledger\n")
        assert git(["status", "--porcelain"], repo) == "", "init left files git can see"
        checks += 1
        expect(run("leakcheck"), "leakcheck: 0 files")  # no entries yet is not an error

        # load the fixture log: fake project terms, records across three weeks
        for kind in ("observations", "generalized", "proposals", "reviews"):
            for f in (fixture / kind).glob("*.md"):
                (log / kind / f.name).write_text(f.read_text().replace("__SHA__", sha))
        with (log / "denylist.txt").open("a") as f:
            f.write((fixture / "denylist.txt").read_text())

        # next-id: max of files, archive and floor, plus one; floor follows
        expect(run("next-id", "observations"), "0010")
        expect(run("next-id", "observations"), "0011")
        expect(run("next-id", "proposals"), "0004")

        # leakcheck: normalized term match, built-in e-mail pattern, result recorded
        out = run("leakcheck", code=1)
        expect(out, "PASS ", "FAIL ", "Quokka Ledger", "email:qa@bramblecorp.example",
               "leakcheck: 3 files, 1 with hits")
        g2 = log / "generalized/0002-shared-seed-data.md"
        assert parse(g2.read_text())["leak_check_first"] == "fail"
        checks += 1
        g2.write_text(g2.read_text().replace("the quokka-ledger seed set", "the shared seed set")
                      .replace("Ask qa@bramblecorp.example first.", "Ask the data owner first."))
        expect(run("leakcheck"), "leakcheck: 3 files, 0 with hits")
        fm = parse(g2.read_text())
        assert (fm["leak_check_first"], fm["leak_check"]) == ("fail", "pass")
        checks += 1
        draft = tmp / "article-draft.md"
        draft.write_text("We ran it on QKL-482 at Bramblecorp.\n")
        expect(run("leakcheck", str(draft), code=1), "QKL-", "Bramblecorp")
        named = tmp / "bramblecorp-notes.md"
        named.write_text("Nothing specific in the text.\n")
        expect(run("leakcheck", str(named), code=1), "FAIL", "Bramblecorp")

        # lint: the fixture is clean apart from known warnings; a bad record is caught
        out = run("lint")
        expect(out, "commit not recorded yet", "lint: 0 errors")
        bad = log / "proposals/0099-bad.md"
        bad.write_text("---\nid: 99\ntitle: x\ndate: 2025-03-18\nrun: 2025-03-18-1030-diff\n"
                       "lessons: [99]\noutcome: maybe\n---\n")
        expect(run("lint", code=1), "lesson 99 is not an observation", "outcome must be")
        bad.unlink()
        open_run = log / "reviews/2025-03-20-0900-diff.md"
        open_run.write_text("---\ndate: 2025-03-20\nkind: diff\nminutes:\n---\n")
        expect(run("lint"), "minutes not recorded yet")
        open_run.write_text("---\ndate: 2025-03-20\nkind: diff\nminutes: soon\n---\n")
        expect(run("lint", code=1), "minutes must be a whole number")
        open_run.unlink()

        # list: one line per record, archive included
        expect(run("list"), "0005 open test-design recurs:1 generalized:no | Fixed sleep",
               "0001 actioned test-design recurs:- generalized:yes", "list: 9 observations")
        expect(run("list", "proposals"), "0003 pending lessons:1,5 run:2025-03-18-1030-diff")

        # counts: every metric on the fixture, weeks from --start
        out = run("counts", "--start", "2025-03-03", "--verify-commits")
        expect(out,
               "lessons: 4 distinct, 3 recurrences, 1 outside the window",
               "pilot entries left out of every count: 1 observations, 0 proposals, 0 reviews",
               "| 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |",
               "| 2 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |",
               "| 3 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |",
               "changed a project file, with commit: 1 of 4 (25%)",
               "change made, commit not recorded yet: 1",
               "commit check: 1 ok, 0 problems",
               "already held: held 1, not-held 1, ambiguous 1, unlabeled 1",
               "generalized: 3 of 4 lessons (missing: 1)",
               "leak check, first run failed: 1",
               "leak check, failing now: 0",
               "human read: ok 1, leak 1, pending 1",
               "leaks the script missed (first human read: leak, first leak check: pass): 1",
               "recurrences after the fix landed: 1 (lessons: 1)",
               "repeats before a fix: 2",
               "| 1 | 1 | 25 | 0 | 0 |",
               "observer: 55 min in 2 reviews",
               "diff: 10 min in 1 reviews",
               "proposals: 3 (accepted 1, declined 1, pending 1)",
               "proposals accepted, of decided: 1 of 2 (50%)",
               "proposals per lesson: 1: 2, 2: 1, 5: 1")

        # archive: resolved before today moves; counts read the archive too
        expect(run("archive"), "archive: moved 2")
        assert (log / "observations/archive/0001-wait-for-ui-not-timers.md").exists()
        checks += 1
        expect(run("counts", "--start", "2025-03-03"), "lessons: 4 distinct, 3 recurrences")
        expect(run("next-id", "observations"), "0012")

        # an empty denylist is refused, never read as "no leaks"
        (log / "denylist.txt").write_text("# nothing yet\n")
        expect(run("leakcheck", code=2), "has no terms")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"selftest: {checks} checks passed")


COMMANDS = {"root": cmd_root, "init": cmd_init, "next-id": cmd_next_id, "lint": cmd_lint,
            "leakcheck": cmd_leakcheck, "list": cmd_list, "archive": cmd_archive, "counts": cmd_counts,
            "selftest": cmd_selftest}


def main(argv):
    log = None
    if argv[:1] == ["--log"]:
        if len(argv) < 2:
            sys.exit("pobs: --log needs a directory")
        log, argv = Path(argv[1]).resolve(), argv[2:]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    if argv[0] != "selftest":
        log = log or project_root() / LOG_NAME
        if argv[0] not in ("root", "init") and not log.is_dir():
            sys.exit(f"pobs: no log at {log}; run `pobs.py init` first")
    COMMANDS[argv[0]](log, argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
