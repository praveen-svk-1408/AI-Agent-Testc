"""Application constants."""

# Default timeouts (milliseconds)
DEFAULT_BROWSER_TIMEOUT = 30000
DEFAULT_NAVIGATION_TIMEOUT = 30000

# Selector types
SELECTOR_CSS = "css"
SELECTOR_XPATH = "xpath"

# Test action names
TEST_ACTIONS = [
    "navigate",
    "click",
    "fill",
    "assert",
    "screenshot",
    "wait",
    "select",
    "hover",
    "key_press",
    "scroll",
]

# HTTP status codes for API responses
SUCCESS = 200
CREATED = 201
BAD_REQUEST = 400
NOT_FOUND = 404
SERVER_ERROR = 500
