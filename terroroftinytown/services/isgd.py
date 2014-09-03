# encoding=utf-8
import re
from terroroftinytown.six.moves import html_parser

from terroroftinytown.services import *
from terroroftinytown.client.errors import PleaseRetry

__all__ = ['IsgdService']

class IsgdService(BaseService):
    # unavailable status code: 200 410
    # banned status code: 502

    def process_unavailable(self, response):
        if not response.text:
            raise PleaseRetry()
        if '<div id="main"><p>Rate limit exceeded - please wait 1 minute before accessing more shortened URLs</p></div>' in response.text:
            raise PleaseRetry()
        if "<div id=\"disabled\"><h2>Link Disabled</h2>" in data:
            return self.parse_blocked(response)
        if "<p>The full original link is shown below. <b>Click the link</b> if you'd like to proceed to the destination shown:" in data:
            return self.parse_preview(response)

    def parse_blocked(self, response):
        match = re.search("<p>For reference and to help those fighting spam the original destination of this URL is given below \(we strongly recommend you don't visit it since it may damage your PC\): -<br />(.*)</p><h2>is\.gd</h2><p>is\.gd is a free service used to shorten long URLs\.", response.text)
        if not match:
            raise exceptions.ServiceException("Could not find target URL in 'Link Disabled' page")

        url = match.group(1).decode("utf-8")
        url = html_parser.HTMLParser().unescape(url).encode("utf-8")
        if url == "":
            raise PleaseRetry()
        return url

    def parse_preview(self, response):
        match = re.search("<b>Click the link</b> if you'd like to proceed to the destination shown: -<br /><a href=\"(.*)\" class=\"biglink\">", response.text)
        if not match:
            raise exceptions.ServiceException("Could not find target URL in 'Preview' page")

        url = match.group(1).decode("utf-8")
        return html_parser.HTMLParser().unescape(url).encode("utf-8")

registry[u'isgd'] = IsgdService