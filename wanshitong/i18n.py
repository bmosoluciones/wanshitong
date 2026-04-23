# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Internationalisation helpers.

Import ``_`` from this module throughout the application so that all
translatable strings go through Flask-Babel's lazy_gettext and are
properly extracted by pybabel.
"""

from flask_babel import lazy_gettext as _

__all__ = ["_"]
