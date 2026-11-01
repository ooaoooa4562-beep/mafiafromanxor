import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


def publish(channel, data):
    """Publish a server-validated event to Centrifugo; never expose the API key."""
    api_url = getattr(settings, "CENTRIFUGO_API_URL", "")
    api_key = getattr(settings, "CENTRIFUGO_API_KEY", "")
    if not api_url or not api_key:
        logger.warning("Centrifugo publish skipped: service is not configured")
        return False

    request = Request(
        api_url.rstrip("/") + "/publish",
        data=json.dumps({"channel": channel, "data": data}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=3) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        logger.exception("Centrifugo publish failed for channel %s", channel)
        return False
