#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import sys
import unittest
from . import BaseTest

_plat = sys.platform.lower()
is_macos = 'darwin' in _plat


class TestGLFW(BaseTest):

    @unittest.skipIf(is_macos, 'Skipping test on macOS because glfw-cocoa.so is not built with backend_utils')
    def test_utf_8_strndup(self):
        import os
        import ctypes

        base = os.path.dirname(os.path.abspath(__file__))
        backend_utils = os.path.join(base, '..', 'kitty', 'glfw-x11.so')
        if not os.path.exists(backend_utils):
            raise Exception('Module x11 not found')
        lib = ctypes.CDLL(backend_utils)
        utf_8_strndup = lib.utf_8_strndup
        utf_8_strndup.restype = ctypes.c_char_p
        utf_8_strndup.argtypes = (ctypes.c_char_p, ctypes.c_size_t)

        def test(string):
            string_bytes = bytes(string, 'utf-8')
            prev_part_bytes = b''
            prev_length_bytes = -1
            for length in range(len(string) + 1):
                part = string[:length]
                part_bytes = bytes(part, 'utf-8')
                length_bytes = len(part_bytes)
                for length_bytes_2 in range(prev_length_bytes + 1, length_bytes):
                    self.ae(utf_8_strndup(string_bytes, length_bytes_2), prev_part_bytes)
                self.ae(utf_8_strndup(string_bytes, length_bytes), part_bytes)
                prev_part_bytes = part_bytes
                prev_length_bytes = length_bytes
            self.ae(utf_8_strndup(string_bytes, len(string_bytes) + 1), string_bytes)  # Try to go one character after the end of the string

        self.ae(utf_8_strndup(None, 2), None)
        self.ae(utf_8_strndup(b'', 2), b'')

        test('Ã¶')
        test('>a<')
        test('>Ã¤<')
        test('>áº¿<')
        test('>ð<')
        test('â® Eâda = Q,  n â â, ðâ f(i) = â g(i)')
