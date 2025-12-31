class RSSFetchError(Exception):
    """Raised when an RSS/Atom feed cannot be fetched or parsed."""


class ParseError(Exception):
    """Raised when a feed entry cannot be parsed into expected fields."""
