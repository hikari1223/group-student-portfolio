"""
debug_check.py - diagnostic helper for the Group Student Portfolio.

Run this any time something breaks, to find out WHERE it broke:
    .\\venv\\Scripts\\python.exe debug_check.py

It performs 4 checks:
  1. Django system check (settings, apps, middleware)
  2. URL routing - does every named URL still resolve?
  3. Page rendering - does every view still return HTTP 200?
  4. Template/static integrity - do the templates and static files exist?

It is a standalone helper. It does NOT change any project code.
You can delete this file before you submit your project.
"""
import os
import sys
import traceback

try:
    import django
except ImportError:
    print()
    print("Django is not installed in this Python.")
    print()
    print("  On Windows, run this first:   setup.bat")
    print("  On macOS or Linux:            ./setup.sh")
    print()
    print("  Or, if you already have a virtual environment:")
    print("     .\\venv\\Scripts\\python.exe debug_check.py")
    print()
    sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portfolio_site.settings")
django.setup()

from django.conf import settings          # noqa: E402
from django.template.loader import get_template  # noqa: E402
from django.test import Client            # noqa: E402
from django.test.utils import override_settings  # noqa: E402
from django.urls import NoReverseMatch, reverse  # noqa: E402

EXPECTED_PAGES = ["home", "about", "members", "skills", "projects", "gallery", "contact"]

BASE_DIR = settings.BASE_DIR

GREEN, RED, YELLOW, CYAN, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[0m"

failures = []


def ok(msg):
    print(f"  {GREEN}PASS{RESET}  {msg}")


def bad(msg, detail=""):
    print(f"  {RED}FAIL{RESET}  {msg}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"        {line}")
    failures.append(msg)


def warn(msg):
    print(f"  {YELLOW}WARN{RESET}  {msg}")


def section(title):
    print(f"\n{CYAN}=== {title} ==={RESET}")


# ---------------------------------------------------------------- 1. system
section("1. Django system check")
try:
    from django.core.management import call_command
    call_command("check", verbosity=1)
    ok("No issues reported by manage.py check")
except Exception:
    bad("Django system check failed", traceback.format_exc())


# ------------------------------------------------------------------ 2. urls
section("2. URL routing")
urls = {}
for name in EXPECTED_PAGES:
    try:
        urls[name] = reverse(name)
        ok(f"url '{name}' -> {urls[name]}")
    except NoReverseMatch:
        bad(f"url '{name}' cannot be reversed",
            "NoReverseMatch: no URL pattern with name='%s' was found.\n"
            "Check portfolio/urls.py for a missing path(...) entry." % name)

# is the app's urlconf even wired into the project urlconf?
try:
    from django.urls import get_resolver
    included = False
    for pattern in get_resolver().url_patterns:
        # an included app shows up as a URLResolver; its module tells us which app
        module = getattr(pattern, "urlconf_name", None)
        if module and "portfolio" in str(module):
            included = True
    if included:
        ok("portfolio urls are included in portfolio_site/urls.py")
    else:
        bad("portfolio.urls is not included in portfolio_site/urls.py",
            "Expected path('', include('portfolio.urls')) in portfolio_site/urls.py")
except Exception:
    bad("Could not read the root URLconf", traceback.format_exc())


# ---------------------------------------------------------------- 3. pages
section("3. Page rendering (HTTP status)")
# The test client sends Host: testserver, which is not in ALLOWED_HOSTS.
# We add it here only for this check so the script can test every page.
# The real site is unaffected by this.
allowed = list(settings.ALLOWED_HOSTS) + ["testserver"]
client = Client()
with override_settings(ALLOWED_HOSTS=allowed):
    for name in EXPECTED_PAGES:
        if name not in urls:
            continue
        try:
            response = client.get(urls[name])
            if response.status_code == 200:
                ok(f"GET {urls[name]:<12} -> 200 ({len(response.content)} bytes)")
            elif response.status_code == 400:
                bad(f"GET {urls[name]:<12} -> 400 DisallowedHost",
                    "ALLOWED_HOSTS does not allow this host.\n"
                    "In portfolio_site/settings.py set ALLOWED_HOSTS = ['localhost', '127.0.0.1']")
            else:
                bad(f"GET {urls[name]:<12} -> {response.status_code}",
                    "The view raised an error. The traceback above shows where.")
        except Exception:
            bad(f"GET {urls[name]} raised an exception", traceback.format_exc())


# ------------------------------------------------------- 4. templates/static
section("4. Template and static file integrity")
TEMPLATES = [
    "portfolio/base.html",
    "portfolio/home.html",
    "portfolio/about.html",
    "portfolio/members.html",
    "portfolio/skills.html",
    "portfolio/projects.html",
    "portfolio/gallery.html",
    "portfolio/contact.html",
    "portfolio/includes/navbar.html",
    "portfolio/includes/footer.html",
]
for tpl in TEMPLATES:
    try:
        get_template(tpl)
        ok(f"template {tpl}")
    except Exception:
        bad(f"template {tpl} could not be loaded", traceback.format_exc())

STATIC = [
    "portfolio/css/style.css",
    "portfolio/images/ephraim.jpg",
    "portfolio/images/ephraim_hobby.jpg",
    "portfolio/images/arjay.jpg",
    "portfolio/images/arjay_hobby.jpg",
    "portfolio/images/victor.jpg",
    "portfolio/images/victor_hobby.jpg",
    "portfolio/images/lorenz.jpg",
    "portfolio/images/lorenz_hobby.jpg",
    "portfolio/images/justine.jpg",
    "portfolio/images/justine_hobby.jpg",
]
for rel in STATIC:
    path = BASE_DIR / "static" / rel
    if path.exists():
        ok(f"static {rel} ({path.stat().st_size} bytes)")
    else:
        bad(f"static file missing: static/{rel}",
            "The {% static %} tag points at a file that does not exist.")


# --------------------------------------------------------------- 5. summary
section("Summary")
if failures:
    print(f"{RED}{len(failures)} problem(s) found:{RESET}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print(f"{GREEN}Everything checks out. The project is in a working state.{RESET}")
    sys.exit(0)
