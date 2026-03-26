"""
Fictional test data for speechwire-mcp tests.

All person names are characters from The West Wing (NBC, 1999-2006).
All school and organization names are fictional.
No real PII appears anywhere in the test suite.

This module serves two purposes:
1. Provides importable constants for use in test assertions
2. Documents every fictional identity used in test fixtures
"""

# --- People ---------------------------------------------------------------
#
# West Wing characters used as test judges, coaches, students, and
# account holders.  Enough characters to cover all test files without
# reusing names within the same test module.

# Senior staff
JED_BARTLET = "Jed Bartlet"
LEO_MCGARRY = "Leo McGarry"
JOSH_LYMAN = "Josh Lyman"
SAM_SEABORN = "Sam Seaborn"
TOBY_ZIEGLER = "Toby Ziegler"
CJ_CREGG = "C.J. Cregg"
CHARLIE_YOUNG = "Charlie Young"
DONNA_MOSS = "Donna Moss"

# Cabinet, family & advisors
ABBEY_BARTLET = "Abbey Bartlet"
ZOEY_BARTLET = "Zoey Bartlet"
ELLIE_BARTLET = "Ellie Bartlet"
NANCY_MCNALLY = "Nancy McNally"
OLIVER_BABISH = "Oliver Babish"

# Staff & recurring
WILL_BAILEY = "Will Bailey"
KATE_HARPER = "Kate Harper"
AINSLEY_HAYES = "Ainsley Hayes"
DANNY_CONCANNON = "Danny Concannon"
AMY_GARDNER = "Amy Gardner"
JOEY_LUCAS = "Joey Lucas"
ANNABETH_SCHOTT = "Annabeth Schott"
MANDY_HAMPTON = "Mandy Hampton"
MARGARET_HOOPER = "Margaret Hooper"
DEBBIE_FIDERER = "Debbie Fiderer"
ANDREA_WYATT = "Andrea Wyatt"
MALLORY_OBRIEN = "Mallory O'Brien"
RON_BUTTERFIELD = "Ron Butterfield"
BRUNO_GIANELLI = "Bruno Gianelli"
LOU_THORNTON = "Lou Thornton"
RONNA_BECKMAN = "Ronna Beckman"
BRAM_HOWARD = "Bram Howard"
CLIFF_CALLEY = "Cliff Calley"
PERCY_FITZWALLACE = "Percy Fitzwallace"

# Politicians
MATT_SANTOS = "Matt Santos"
ARNOLD_VINICK = "Arnold Vinick"
BOB_RUSSELL = "Bob Russell"
GLEN_WALKEN = "Glen Walken"
ROBERT_RITCHIE = "Robert Ritchie"
JEFF_HAFFLEY = "Jeff Haffley"


# --- Schools --------------------------------------------------------------
#
# Fictional school names.  Some reference West Wing locations/episodes,
# others use character surnames (a common real-world naming convention).

# Full names
MANCHESTER_PREP = "Manchester Prep"
ROSSLYN_ACADEMY = "Rosslyn Academy"
HARTSFIELD_LANDING = "Hartsfield Landing School"
KENNISON_ACADEMY = "Kennison Academy"
CHESAPEAKE_PREP = "Chesapeake Prep"
POTOMAC_ACADEMY = "Potomac Academy"
NASHUA_PREP = "Nashua Prep"
HOLLIS_ACADEMY = "Hollis Academy"
SAGAMORE_PREP = "Sagamore Prep"
STACKHOUSE_ACADEMY = "Stackhouse Academy"
SANTOS_ACADEMY = "Santos Academy"
BARTLET_MIDDLE = "Bartlet Middle School"
VINICK_ACADEMY = "Vinick Academy"
DALTON_PREP = "Dalton Prep"
CONCORD_PREP = "Concord Prep"

# Abbreviated forms (used in team/hybrid entry tests)
SEABORN_HS = "Seaborn HS"
LYMAN_HS = "Lyman HS"
LYMAN_MS = "Lyman MS"
CREGG_MS = "Cregg MS"
BAILEY_HS = "Bailey HS"
HAFFLEY_HS = "Haffley HS"
RITCHIE_HS = "Ritchie HS"
WALKEN_HS = "Walken HS"
RUSSELL_HS = "Russell HS"
SANTOS_HS = "Santos HS"


# --- Organizations --------------------------------------------------------

CAPITOL_DEBATE_LEAGUE = "Capitol Debate League"
CAPITOL_DEBATE_ADMIN = "Capitol Debate League Administration"
CAPITOL_DEBATE_ELEMENTARY = "Capitol Debate League Elementary"


# --- Helpers --------------------------------------------------------------

def email_for(name: str) -> str:
    """Generate a test email from a character name.

    Examples
    --------
    >>> email_for("Josh Lyman")
    'josh.lyman@example.com'
    >>> email_for("C.J. Cregg")
    'cj.cregg@example.com'
    >>> email_for("Mallory O'Brien")
    'mallory.obrien@example.com'
    """
    clean = name.lower().replace(".", "").replace("'", "")
    parts = clean.split()
    return f"{parts[0]}.{parts[-1]}@example.com"
