import tempfile

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={},
        INSTALLED_APPS=[],
        BASE_DIR=tempfile.gettempdir(),
    )
    django.setup()
