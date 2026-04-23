# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Simple logging shim used by the package."""

import logging


class SimpleLogger:
    def __init__(self, name: str = "app"):
        self._log = logging.getLogger(name)

    def trace(self, *args, **kwargs):
        self._log.debug(" ".join(str(a) for a in args))

    def info(self, *args, **kwargs):
        self._log.info(" ".join(str(a) for a in args))

    def warning(self, *args, **kwargs):
        self._log.warning(" ".join(str(a) for a in args))

    def exception(self, *args, **kwargs):
        self._log.exception(" ".join(str(a) for a in args))


log = SimpleLogger()
