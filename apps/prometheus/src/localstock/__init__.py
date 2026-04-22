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


def configure_vnstock_api_key() -> None:
    """Set vnstock API key from VNSTOCK_API_KEY env var if configured.

    Writes the key to ~/.vnstock/api_key.json via vnstock's built-in
    auth mechanism. Skips silently if no key is set.
    """
    from localstock.config import get_settings

    api_key = get_settings().vnstock_api_key
    if not api_key:
        return

    from localstock.crawlers import suppress_vnstock_output

    with suppress_vnstock_output():
        try:
            from vnai.beam.auth import authenticator
            import json

            authenticator.vnstock_dir.mkdir(exist_ok=True)
            with open(authenticator.api_key_file, "w") as f:
                json.dump({"api_key": api_key.strip()}, f, indent=2)
        except Exception:
            pass
