from enum import Enum
from typing import TypeVar, Callable
import logging
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ClientState(Enum):
    """Authentication state machine for the SpeechWire client."""

    UNAUTHENTICATED = "unauthenticated"
    LOGGED_IN = "logged_in"
    ACCOUNT_SELECTED = "account_selected"
    TOURNAMENT_ACTIVE = "tournament_active"


class SpeechWireAuthError(Exception):
    """Raised when authentication fails (bad credentials, missing pages, etc.)."""

    pass


class SpeechWireSelectionRequired(Exception):
    """Raised when multiple options are available and user must choose.

    Parameters
    ----------
    message : str
        Human-readable explanation.
    options : list[dict]
        Available choices the caller should present to the user.
    """

    def __init__(self, message: str, options: list[dict]):
        super().__init__(message)
        self.options = options


class SpeechWireClient:
    """Authenticated HTTP client for the SpeechWire tournament management system.

    Handles a phased authentication flow (login → account → tournament) with
    automatic session renewal on expiry.  Account, circuit, and tournament IDs
    are optional — when omitted the client enters discovery mode and can
    auto-select when exactly one option exists.

    Parameters
    ----------
    email : str
        SpeechWire account email.
    password : str
        SpeechWire account password.
    account_id : str | None
        Numeric account identifier.  Discovered if omitted.
    circuit_id : str | None
        Numeric circuit identifier.  Discovered if omitted.
    tournament_id : str | None
        Numeric tournament identifier.  Discovered if omitted.
    """

    def __init__(
        self,
        email: str,
        password: str,
        account_id: str | None = None,
        circuit_id: str | None = None,
        tournament_id: str | None = None,
    ):
        self.email = email
        self.password = password
        self.account_id = account_id
        self.circuit_id = circuit_id
        self.tournament_id = tournament_id
        self.session = requests.Session()
        self.state = ClientState.UNAUTHENTICATED
        self._reauthenticating = False

    # ------------------------------------------------------------------
    # Phased auth methods
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Phase A — POST credentials and establish a logged-in session.

        Transitions state to ``LOGGED_IN``.
        """
        try:
            self.session.cookies.clear()
            self.state = ClientState.UNAUTHENTICATED

            resp = self.session.post(
                "https://www.speechwire.com/c-login.php",
                data={
                    "teamemail": self.email,
                    "password": self.password,
                    "mode": "account",
                    "tournid": "",
                    "Submit": "Log in",
                },
            )
            resp.raise_for_status()
            body_lower = resp.text.lower()
            if "incorrect" in body_lower or "invalid" in body_lower:
                raise SpeechWireAuthError(
                    "Login rejected — SpeechWire reported invalid credentials"
                )
            self.state = ClientState.LOGGED_IN
            logger.info("Logged in as %s", self.email)
        except RequestException as e:
            raise SpeechWireAuthError(f"Login failed: {e}") from e

    def select_account(self, account_id: str | int) -> None:
        """Phase B — select an account by its numeric ID.

        Parameters
        ----------
        account_id : str | int
            The ``selectaccountid`` value from the account-select page.

        Transitions state to ``ACCOUNT_SELECTED`` and stores the chosen ID.
        """
        try:
            resp = self.session.get(
                f"https://www.speechwire.com/c-account-select.php?selectaccountid={account_id}"
            )
            resp.raise_for_status()
            self.account_id = str(account_id)
            self.state = ClientState.ACCOUNT_SELECTED
            logger.info("Selected account %s", account_id)
        except RequestException as e:
            raise SpeechWireAuthError(f"Account selection failed: {e}") from e

    def select_tournament(self, tournament_id: str | int, circuit_id: str | int) -> None:
        """Phase C — select a tournament and activate the session.

        Parameters
        ----------
        tournament_id : str | int
            Numeric tournament identifier.
        circuit_id : str | int
            Numeric circuit identifier.

        Transitions state to ``TOURNAMENT_ACTIVE`` and stores the chosen IDs.
        """
        try:
            resp = self.session.post(
                "https://www.speechwire.com/c-circuit-tournaments.php",
                data={
                    "tournid": str(tournament_id),
                    "Submit": "Log in",
                    "mode": "tournjump",
                    "circuitid": str(circuit_id),
                },
            )

            # Activate tournament session via the redirect link
            soup = BeautifulSoup(resp.text, "html.parser")
            link = soup.find(
                "a",
                href=lambda x: x and "njc=" in x and f"tournid={tournament_id}" in x,
            )
            if not link:
                raise SpeechWireAuthError("Could not find tournament activation link")

            self.session.get(
                link["href"],
                headers={"Referer": "https://www.speechwire.com/"},
            )
            self.tournament_id = str(tournament_id)
            self.circuit_id = str(circuit_id)
            self.state = ClientState.TOURNAMENT_ACTIVE
            logger.info(
                "Activated tournament %s (circuit %s)",
                tournament_id,
                circuit_id,
            )
        except RequestException as e:
            raise SpeechWireAuthError(f"Tournament selection failed: {e}") from e

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def discover_accounts(self) -> list[dict]:
        """Fetch the list of accounts available after login.

        Returns
        -------
        list[dict]
            Each dict has ``account_id`` (int) and ``name`` (str).
        """
        from speechwire_mcp.login.parsers import parse_account_list_html

        resp = self.get("https://www.speechwire.com/c-account-select.php")
        return parse_account_list_html(resp.text)

    def discover_tournaments(self) -> list[dict]:
        """Fetch the list of tournaments for the selected account.

        Returns
        -------
        list[dict]
            Each dict has ``tournament_id``, ``circuit_id``, ``name``,
            and optionally ``date``.
        """
        from speechwire_mcp.login.parsers import parse_tournament_list_html

        resp = self.get("https://www.speechwire.com/c-circuit-tournaments.php")
        return parse_tournament_list_html(resp.text)

    # ------------------------------------------------------------------
    # Auto-select private helpers
    # ------------------------------------------------------------------

    def _auto_select_account(self) -> None:
        """Discover accounts and auto-select if exactly one exists."""
        accounts = self.discover_accounts()
        if len(accounts) == 1:
            self.select_account(accounts[0]["account_id"])
            logger.info("Auto-selected sole account: %s", accounts[0].get("name"))
        elif len(accounts) == 0:
            raise SpeechWireAuthError("No accounts found for this login. Verify your credentials.")
        else:
            raise SpeechWireSelectionRequired(
                "Multiple accounts available — please select one.",
                options=accounts,
            )


    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def ensure_tournament_session(self) -> None:
        """Reach ``TOURNAMENT_ACTIVE`` state, auto-discovering where possible.

        If IDs were provided up front this behaves like the original
        ``_authenticate()``.  Otherwise it discovers and auto-selects when
        a single option exists, raising ``SpeechWireSelectionRequired``
        when the caller must choose.
        """
        if self.state == ClientState.TOURNAMENT_ACTIVE:
            return
        self._authenticate()

    def _authenticate(self) -> None:
        """Full authentication convenience wrapper.

        Logs in, selects account (by ID or auto-discover), then selects
        tournament (by ID or auto-discover).
        """
        self.login()

        if self.account_id:
            self.select_account(self.account_id)
        else:
            self._auto_select_account()

        if self.tournament_id and self.circuit_id:
            self.select_tournament(self.tournament_id, self.circuit_id)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _looks_like_expired_session(self, resp: requests.Response) -> bool:
        """Detect whether a response indicates the session has expired.

        Checks for two indicators:
        - Password input field (login page marker)
        - "Select the tournament" text, but only when the URL is NOT the
          tournament discovery page where that text appears legitimately
        """
        if 'type="password"' in resp.text or "type='password'" in resp.text:
            return True
        if "Select the tournament" in resp.text and "c-circuit-tournaments.php" not in resp.url:
            return True
        return False

    def get(self, url: str) -> requests.Response:
        """GET a manage.speechwire.com page with session-expiry handling.

        If the response looks like an expired session (login page redirect
        or unexpected tournament-selection text), the client re-authenticates
        and retries the request once.  A guard prevents infinite recursion
        when ``_authenticate`` itself issues GETs (e.g. account discovery).
        """
        resp = self.session.get(url)
        if self._looks_like_expired_session(resp) and not self._reauthenticating:
            self._reauthenticating = True
            try:
                self._authenticate()
            finally:
                self._reauthenticating = False
            resp = self.session.get(url)
        return resp

    def post(self, url: str, data: dict) -> requests.Response:
        """POST form data with session-expiry handling.

        If the response looks like an expired session, re-authenticates
        and retries the POST once.

        Parameters
        ----------
        url : str
            Target URL on manage.speechwire.com.
        data : dict
            Form data to submit.
        """
        resp = self.session.post(url, data=data)
        if self._looks_like_expired_session(resp):
            self._authenticate()
            resp = self.session.post(url, data=data)
        return resp


def _fetch_and_parse(
    client: SpeechWireClient | None,
    url: str,
    parser: Callable[[str], T],
    default: T,
    context: str = "",
) -> T:
    """Fetch a page and parse it, returning *default* on any failure.

    Parameters
    ----------
    client : SpeechWireClient | None
        The authenticated client instance.
    url : str
        URL to fetch.
    parser : Callable[[str], T]
        Pure function that converts HTML text into the desired data shape.
    default : T
        Value returned when fetching or parsing fails.
    context : str
        Human-readable label for log messages.
    """
    if not client:
        logger.error("No SpeechWire client provided")
        return default

    try:
        resp = client.get(url)
        resp.raise_for_status()
    except Exception:
        logger.exception("Failed to fetch %s", context)
        return default

    try:
        return parser(resp.text)
    except Exception:
        logger.exception("Failed to parse %s", context)
        return default


def _post_and_parse(
    client: SpeechWireClient | None,
    url: str,
    data: dict,
    parser: Callable[[str], T],
    default: T,
    context: str = "",
) -> T:
    """POST form data and parse the response, returning *default* on failure.

    Parameters
    ----------
    client : SpeechWireClient | None
        The authenticated client instance.
    url : str
        URL to POST to.
    data : dict
        Form data to submit.
    parser : Callable[[str], T]
        Pure function that converts HTML text into the desired data shape.
    default : T
        Value returned when posting or parsing fails.
    context : str
        Human-readable label for log messages.
    """
    if not client:
        logger.error("No SpeechWire client provided")
        return default

    try:
        resp = client.post(url, data=data)
        resp.raise_for_status()
    except Exception:
        logger.exception("Failed to post %s", context)
        return default

    try:
        return parser(resp.text)
    except Exception:
        logger.exception("Failed to parse %s response", context)
        return default
