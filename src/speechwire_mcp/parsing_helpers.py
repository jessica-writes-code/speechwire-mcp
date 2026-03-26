"""Shared HTML parsing helper functions used across parser modules.

Pure utility functions with no side effects, safe for reuse in all parsers.
"""

import logging
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, element

logger = logging.getLogger(__name__)


def make_soup(html: str) -> BeautifulSoup:
    """Parse an HTML string into a BeautifulSoup tree.

    Parameters
    ----------
    html : str
        Raw HTML string to parse.

    Returns
    -------
    BeautifulSoup
        Parsed document tree.
    """
    return BeautifulSoup(html, "html.parser")


def td_safe(tds: list[element.Tag], idx: int) -> element.Tag | None:
    """Safely index a list of table cell elements.

    Parameters
    ----------
    tds : list[element.Tag]
        List of ``<td>`` elements from a table row.
    idx : int
        Zero-based index of the cell to retrieve.

    Returns
    -------
    element.Tag | None
        The ``<td>`` element at the given index, or ``None`` if out of bounds.
    """
    return tds[idx] if idx < len(tds) else None


def extract_int_query_param(
    a_tag: element.Tag | None, param_name: str
) -> int | None:
    """Extract an integer query parameter from an anchor tag's href.

    Parameters
    ----------
    a_tag : element.Tag | None
        A BeautifulSoup ``<a>`` tag with an ``href`` attribute.
    param_name : str
        Name of the query parameter to extract (e.g., ``"judgeid"``).

    Returns
    -------
    int | None
        The integer value of the parameter, or ``None`` if not found or invalid.
    """
    if not a_tag:
        return None
    try:
        href = a_tag.get("href", "") or ""
        q = parse_qs(urlparse(href).query)
        val = q.get(param_name, [None])[0]
        if val and str(val).isdigit():
            return int(val)
    except Exception:
        return None
    return None
