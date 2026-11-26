"""Drop HTTP library debug bodies; sanitize Werkzeug callback request lines."""
import logging
import re


class CallbackFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        record.msg = re.sub(r'(/auth/google/callback)\?[^\s\"]*', r'\1?[redacted]', message)
        record.args = ()
        return True


def install():
    logger = logging.getLogger('werkzeug')
    if not any(isinstance(item, CallbackFilter) for item in logger.filters):
        logger.addFilter(CallbackFilter())
    # OAuth libraries can log request bodies at DEBUG. Never enable them in Web mode.
    for name in ('requests_oauthlib','oauthlib','google.auth.transport','urllib3','googleapiclient.discovery','googleapiclient.http','google_auth_httplib2','httplib2'):
        logging.getLogger(name).setLevel(logging.WARNING)
