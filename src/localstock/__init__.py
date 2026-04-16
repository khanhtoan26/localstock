"""LocalStock — AI Stock Agent for Vietnamese Market (HOSE)."""

__version__ = "0.1.0"


def configure_ssl() -> None:
    """Disable SSL verification for requests when SSL_VERIFY=false.

    Useful behind corporate proxies with self-signed certificates.
    Must be called before any vnstock/requests calls.
    """
    from localstock.config import get_settings

    if not get_settings().ssl_verify:
        import requests
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        _original_send = requests.Session.send

        def _patched_send(self, request, **kwargs):
            kwargs["verify"] = False
            return _original_send(self, request, **kwargs)

        requests.Session.send = _patched_send
