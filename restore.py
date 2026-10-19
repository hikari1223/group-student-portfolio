"""
restore.py - one-command recovery for the Group Student Portfolio.

Your instructor removes some code, the site breaks, and you want to see
what changed and get it back. This does both.

    .\\venv\\Scripts\\python.exe restore.py              show the damage, then ask before restoring
    .\\venv\\Scripts\\python.exe restore.py --diff       only show what was removed (changes nothing)
    .\\venv\\Scripts\\python.exe restore.py --yes        restore immediately, no questions
    .\\venv\\Scripts\\python.exe restore.py --purge      also delete files that were newly added
    .\\venv\\Scripts\\python.exe restore.py --no-check   skip the verification run at the end

It works even if your instructor already committed their change, because it
compares the working tree against a saved snapshot of the good code.

Before it restores anything it saves the broken state as a git tag called
'broken-state', so you can still look at exactly what was removed afterwards:

    git diff broken-state baseline-pre-removal
    git show broken-state
"""
import argparse
import os
import subprocess
import sys

# ------------------------------------------------------------------ config
BASELINE_TAG = "baseline-pre-removal"
FALLBACK_SHA = "846874e9c4ad1d0cd8f34cc99ef42d26da55f019"
BROKEN_TAG = "broken-state"

# Files that must never be touched by a restore.
PROTECTED = {
    "db.sqlite3",
    "venv/",
    ".git/",
    ".env",
}

GREEN, RED, YELLOW, CYAN, DIM, BOLD, RESET = (
    "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[90m", "\033[1m", "\033[0m"
)

# ------------------------------------------------------------------ helpers
def git(*args, check=True):
    """Run a git command and return its stdout as text."""
    p = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and p.returncode != 0:
        return ""
    return p.stdout


def git_lines(*args):
    out = git(*args)
    return [ln for ln in out.splitlines() if ln.strip()]


def die(msg):
    print("%s%s%s" % (RED, msg, RESET))
    sys.exit(1)


# ------------------------------------------------------------------ baseline
def find_baseline():
    """Return (sha, description) of the known-good snapshot."""
    if git("rev-parse", "--verify", BASELINE_TAG):
        sha = git("rev-parse", BASELINE_TAG).strip()
        return sha, BASELINE_TAG
    if git("rev-parse", "--verify", FALLBACK_SHA + "^{commit}"):
        return FALLBACK_SHA, "commit " + FALLBACK_SHA[:7]

    # The tag may simply not have been pushed to the remote yet.
    if git("remote"):
        print()
        print("%s  The baseline tag '%s' is not in this copy of the project.%s" % (YELLOW, BASELINE_TAG, RESET))
        print()
        print("  %sIt most likely was never pushed to GitHub. Fix it with one of these:%s" % (DIM, RESET))
        print()
        print("      %sgit fetch origin 'refs/tags/*:refs/tags/*'%s   (pull the tag from GitHub)" % (BOLD, RESET))
        print("      %sgit push origin %s%s   (send your local tag to GitHub)" % (BOLD, BASELINE_TAG, RESET))
        print()
        print("  %sOr, if you are on the same computer that made the tag, it may just need this:%s" % (DIM, RESET))
        print()
        print("      %sgit tag -f %s HEAD%s" % (BOLD, BASELINE_TAG, RESET))
        print()
        print("  %sUntil the tag exists, this tool cannot work - it has nothing to restore from.%s" % (DIM, RESET))
        sys.exit(1)

    # fall back to the very first commit in the repo
    first = git("rev-list", "--max-parents=0", "HEAD")
    if first:
        sha = first.strip().splitlines()[-1]
        print("%s  WARNING: no baseline tag found, falling back to the first commit.%s" % (YELLOW, RESET))
        print("%s  That is the ORIGINAL version of the project, not the reviewed one.%s" % (YELLOW, RESET))
        return sha, "first commit " + sha[:7]
    die("No baseline found. Expected a git tag called '%s'." % BASELINE_TAG)


# ------------------------------------------------------------------ analysis
def collect(sha):
    """Work out what changed compared with the baseline."""
    tracked_now = set(git_lines("ls-files"))
    in_baseline = set(git_lines("ls-tree", "-r", "--name-only", sha))
    untracked = set(git_lines("ls-files", "--others", "--exclude-standard"))

    # status of every tracked file: M / A / D
    status = {}
    for line in git_lines("diff", "--name-status", sha):
        parts = line.split("\t")
        if len(parts) >= 2:
            code = parts[0]
            path = parts[-1]
            status[path] = code

    modified, deleted, added = [], [], []
    for path, code in status.items():
        if code.startswith("M"):
            modified.append(path)
        elif code.startswith("D"):
            deleted.append(path)
        elif code.startswith("A"):
            added.append(path)
        elif code.startswith("R"):
            modified.append(path)

    # Ground truth: a file that is in the baseline but is no longer on disk
    # was deleted. Git keeps it in the index until the deletion is staged,
    # so 'git ls-files' alone cannot be trusted here.
    for p in in_baseline:
        if not os.path.exists(p) and p not in deleted:
            deleted.append(p)
    deleted = sorted(set(deleted))

    missing = sorted(p for p in in_baseline if p not in tracked_now)
    changed = sorted(p for p in modified if os.path.exists(p))
    extra = sorted(p for p in added if p not in in_baseline)

    # line counts for a quick sense of scale
    numstat = {}
    for line in git_lines("diff", "--numstat", sha):
        parts = line.split("\t")
        if len(parts) == 3:
            numstat[parts[2]] = (parts[0], parts[1])

    return {
        "modified": changed,
        "deleted": deleted,
        "added": extra,
        "untracked": sorted(untracked),
        "numstat": numstat,
        "in_baseline": in_baseline,
    }


def show_report(info, sha, label, show_diff=False):
    print()
    print("%s%s%s" % (BOLD, "=" * 74, RESET))
    print("%s  %s%s" % (BOLD, label, RESET))
    print("%s%s%s" % (BOLD, "=" * 74, RESET))

    if not (info["modified"] or info["deleted"] or info["added"]):
        print("\n  %sEverything matches the baseline. Nothing was removed.%s" % (GREEN, RESET))
        print("  The site is exactly as it was at commit %s." % sha[:7])
        return

    def stat(path):
        a, d = info["numstat"].get(path, ("?", "?"))
        return "  %-46s %s-%s lines" % (path, a, d)

    if info["modified"]:
        print("\n  %sMODIFIED - %d file(s)%s" % (YELLOW, len(info["modified"]), RESET))
        for p in info["modified"]:
            print(stat(p))
    if info["deleted"]:
        print("\n  %sDELETED - %d file(s)  (these will be restored)%s" % (RED, len(info["deleted"]), RESET))
        for p in info["deleted"]:
            print("  %-46s %sfull file missing%s" % (p, RED, RESET))
    if info["added"]:
        print("\n  %sADDED - %d file(s)  (not in the baseline)%s" % (CYAN, len(info["added"]), RESET))
        for p in info["added"]:
            print("  %-46s %snew file%s" % (p, CYAN, RESET))
    if info["untracked"]:
        print("\n  %sUNTRACKED - %d file(s)  (never committed)%s" % (DIM, len(info["untracked"]), RESET))
        for p in info["untracked"][:12]:
            print("  %-46s %s%s" % (p, DIM, "new file"))
        if len(info["untracked"]) > 12:
            print("  %s... and %d more%s" % (DIM, len(info["untracked"]) - 12, RESET))

    if show_diff:
        print()
        print("%s--- actual removed lines ---%s" % (BOLD, RESET))
        diff = git("diff", "-U2", sha, "--", "portfolio", "portfolio_site",
                   "templates", "static", "manage.py", "requirements.txt")
        if diff.strip():
            for i, line in enumerate(diff.splitlines()):
                if i > 400:
                    print("%s... diff truncated ...%s" % (DIM, RESET))
                    break
                if line.startswith("+") and not line.startswith("+++"):
                    print("%s%s%s" % (GREEN, line, RESET))
                elif line.startswith("-") and not line.startswith("---"):
                    print("%s%s%s" % (RED, line, RESET))
                elif line.startswith("@@"):
                    print("%s%s%s" % (CYAN, line, RESET))
                else:
                    print(DIM + line + RESET)
        else:
            print("  (no line-level diff to show)")


# ------------------------------------------------------------------ restore
def protect(path):
    for p in PROTECTED:
        if path == p or path.startswith(p):
            return True
    return False


def do_restore(sha, info, purge=False):
    print("\n%sSaving the current (broken) state as tag '%s' ...%s" % (DIM, BROKEN_TAG, RESET))
    # 'git stash create' builds a commit object of the working tree WITHOUT
    # touching the working tree or the stash list, so the broken code is kept
    # for inspection even after we restore the good version.
    broken_sha = git("stash", "create").strip()
    if broken_sha:
        git("tag", "-f", BROKEN_TAG, broken_sha)
        print("  %stag '%s' now holds the broken working tree (%s)%s"
              % (DIM, BROKEN_TAG, broken_sha[:7], RESET))
    else:
        git("tag", "-f", BROKEN_TAG, "HEAD")
        print("  %stag '%s' points at HEAD (%s)%s"
              % (DIM, BROKEN_TAG, git("rev-parse", "--short", "HEAD").strip(), RESET))
    print("  %sYou can still inspect the broken code with:%s" % (DIM, RESET))
    print("  %s    git diff HEAD %s%s" % (DIM, BROKEN_TAG, RESET))
    print("  %s    git show %s:portfolio/urls.py%s" % (DIM, BROKEN_TAG, RESET))

    print("\n%sRestoring files from %s ...%s" % (BOLD, sha[:7], RESET))
    restored = []
    for path in info["deleted"] + info["modified"]:
        if protect(path):
            print("  %sskipped (protected): %s%s" % (DIM, path, RESET))
            continue
        p = subprocess.run(
            ["git", "checkout", sha, "--", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if p.returncode == 0:
            restored.append(path)
            print("  %srestored%s  %s" % (GREEN, RESET, path))
        else:
            print("  %sFAILED%s    %s  %s" % (RED, RESET, path, p.stderr.strip()[:120]))

    if purge and info["added"]:
        print("\n%sRemoving added files (--purge) ...%s" % (BOLD, RESET))
        for path in info["added"]:
            if protect(path):
                continue
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print("  %sremoved%s    %s" % (CYAN, RESET, path))
                except OSError as e:
                    print("  %sFAILED%s    %s  %s" % (RED, RESET, path, e))

    # unstage everything so git shows plain "modified" files
    git("reset", "-q", "HEAD", "--", ".", check=False)

    return restored


# ------------------------------------------------------------------ verify
def run_check():
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "debug_check.py")
    if not os.path.exists(script):
        print("\n%sdebug_check.py not found - skipping verification.%s" % (DIM, RESET))
        return
    print("\n%sVerifying the restored site ...%s" % (BOLD, RESET))
    p = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=here,
    )
    out = p.stdout
    for line in out.splitlines():
        if "PASS" in line or "FAIL" in line or "Summary" in line or "Everything checks" in line \
                or "problem(s) found" in line:
            # strip the ANSI codes for a clean summary
            import re
            print("  " + re.sub(r"\033\[[0-9;]*m", "", line).rstrip())


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(add_help=True, description="Show and restore removed code.")
    ap.add_argument("--diff", action="store_true", help="only show what was removed")
    ap.add_argument("--yes", action="store_true", help="restore without asking")
    ap.add_argument("--purge", action="store_true", help="also delete newly added files")
    ap.add_argument("--no-check", action="store_true", help="skip the verification run")
    args = ap.parse_args()

    if not os.path.isdir(".git"):
        die("Run this from inside the project folder (the one with manage.py).")

    sha, label = find_baseline()
    info = collect(sha)

    print()
    print("%s  RESTORE TOOL%s" % (BOLD, RESET))
    print("  baseline : %s  (%s)" % (sha[:7], label))

    if args.diff:
        show_report(info, sha, "WHAT WAS REMOVED", show_diff=True)
        print()
        return

    show_report(info, sha, "CURRENT STATE")

    if not (info["modified"] or info["deleted"] or info["added"]):
        print("\n  %sNothing to restore. The site is already at the baseline.%s" % (GREEN, RESET))
        if not args.no_check:
            run_check()
        return

    if args.yes:
        answer = "y"
    else:
        print()
        print("%sRestore the code that was removed?%s" % (BOLD, RESET))
        print("  %sy%s = yes, restore now" % (GREEN, RESET))
        print("  %sn%s = no, leave it broken (I want to look at the error myself)" % (YELLOW, RESET))
        print("  %sd%s = show the raw diff first" % (CYAN, RESET))
        print()
        try:
            answer = input("  Your choice: ").strip().lower() or "n"
        except (EOFError, KeyboardInterrupt):
            print()
            return

    if answer.startswith("d"):
        show_report(info, sha, "WHAT WAS REMOVED", show_diff=True)
        try:
            answer = input("\n  Restore now? [y/n]: ").strip().lower() or "n"
        except (EOFError, KeyboardInterrupt):
            print()
            return

    if answer != "y":
        print("\n  %sNothing was changed. The site is still broken on purpose.%s" % (YELLOW, RESET))
        print("  %sWhen you are ready, run:%s" % (DIM, RESET))
        print("  %s    .\\venv\\Scripts\\python.exe restore.py --yes%s" % (DIM, RESET))
        return

    restored = do_restore(sha, info, purge=args.purge)

    print()
    print("%s%s%s" % (BOLD, "=" * 74, RESET))
    if restored:
        print("%sRESTORED %d file(s):%s" % (GREEN, len(restored), RESET))
        for p in restored:
            print("  %s" % p)
    else:
        print("%sNothing needed restoring.%s" % (YELLOW, RESET))
    print("%s%s%s" % (BOLD, "=" * 74, RESET))

    if not args.no_check:
        run_check()

    print()
    print("%sTip: the broken version is still saved as tag '%s'.%s" % (DIM, BROKEN_TAG, RESET))
    print("%s     git diff HEAD %s   -> shows exactly what was removed%s" % (DIM, BROKEN_TAG, RESET))


if __name__ == "__main__":
    main()
