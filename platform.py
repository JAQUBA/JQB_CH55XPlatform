"""
JQB CH55x Platform — PlatformIO platform class.

Supports WCH CH551, CH552, CH554, CH559 MCS51 USB microcontrollers
using the ch55xduino Arduino-like framework and SDCC compiler.
"""

from platformio.public import PlatformBase


class Ch55xPlatform(PlatformBase):

    def configure_default_packages(self, variables, targets):
        # Packages are installed by setup.ps1, not from PlatformIO registry.
        # Ensure they are declared in self.packages so super() doesn't KeyError.
        for pkg_name, pkg_meta in {
            "toolchain-sdcc-ch55x": {"type": "toolchain", "optional": False},
            "framework-ch55xduino": {"type": "framework", "optional": True},
            "tool-ch55xtools":      {"type": "uploader",  "optional": True},
        }.items():
            if pkg_name not in self.packages:
                self.packages[pkg_name] = dict(pkg_meta)
        return super().configure_default_packages(variables, targets)

    def get_boards(self, id_=None):
        result = super().get_boards(id_)
        if not result:
            return result
        if id_:
            return self._add_default_options(result)
        else:
            for key in result:
                result[key] = self._add_default_options(result[key])
        return result

    def _add_default_options(self, board):
        return board
