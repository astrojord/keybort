import json

from django.contrib.messages import get_messages

HTMX_NAVIGATION_HEADERS = ('HX-Redirect', 'HX-Refresh', 'HX-Location')


class HtmxMessagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if 'HX-Request' not in request.headers or 300 <= response.status_code < 400:
            return response
        if any(header in response for header in HTMX_NAVIGATION_HEADERS):
            return response

        storage = get_messages(request)
        if storage.used:
            return response

        messages = [
            {'level': message.level_tag, 'message': str(message)} for message in storage
        ]
        if not messages:
            return response

        response['HX-Trigger'] = json.dumps(
            {**self._existing_triggers(response), 'messages': messages}
        )
        return response

    @staticmethod
    def _existing_triggers(response):
        header = response.get('HX-Trigger', '').strip()
        if not header:
            return {}
        if header.startswith('{'):
            return json.loads(header)
        return {name.strip(): '' for name in header.split(',') if name.strip()}
