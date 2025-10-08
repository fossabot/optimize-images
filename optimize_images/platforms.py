# encoding: utf-8
import concurrent.futures
import platform
import shutil
from functools import lru_cache
from multiprocessing import cpu_count
from typing import Tuple, Union

from optimize_images.constants import IOS_FONT, IPHONE_FONT_SIZE, IPAD_FONT_SIZE
from optimize_images.constants import IOS_WORKERS
from optimize_images.data_structures import PPoolExType, TPoolExType

import platform


class IconGenerator:
    """Provides icons for file status output, with Unicode or ASCII fallback."""

    def __init__(self) -> None:
        system = platform.system()
        self.use_unicode = system not in ("Windows", "Haiku")
        self.arrow = "->"

        if self.use_unicode:
            self.info = "ℹ️"
            self.downsized = "⤵ "
            self.optimized = "✅"
            self.skipped = "🔴"
            self.size_is_smaller = "🔻"
            self.legend_text = (
                "\n\nUsing these symbols:\n\n"
                "  ✅ Optimized file     ℹ️  EXIF info present\n"
                "  🔴 Skipped file       ⤵  Image was downsized     🔻 Size reduction (%)\n"
            )
        else:
            self.info = "i"
            self.downsized = "V"
            self.optimized = "OK"
            self.skipped = "--"
            self.size_is_smaller = "v"
            self.legend_text = (
                "\n\nUsing these symbols:\n\n"
                "  OK Optimized file      i EXIF info present\n"
                "  -- Skipped file        V Image was downsized      v Size reduction\n"
            )

    def print_legend(self) -> None:
        """Print a legend explaining the icons in use."""
        print(self.legend_text)


@lru_cache(maxsize=None)
def adjust_for_platform() -> Tuple[int, Union[TPoolExType, PPoolExType], int]:
    if platform.system() == 'Darwin':
        if platform.machine().startswith('iPad'):
            device = "iPad"
        elif platform.machine().startswith('iP'):
            device = "iPhone"
        else:
            device = "mac"
    else:
        device = "other"

    if device in ("iPad", "iPhone"):
        # Adapt for smaller screen sizes in iPhone and iPod touch
        import ui
        import console
        console.clear()
        if device == 'iPad':
            font_size = IPAD_FONT_SIZE
        else:
            font_size = IPHONE_FONT_SIZE
        console.set_font(IOS_FONT, font_size)
        screen_width = ui.get_screen_size().width
        char_width = ui.measure_string('.', font=(IOS_FONT, font_size)).width
        line_width = int(screen_width / char_width - 1.5) - 1
        t_pool_ex = concurrent.futures.ThreadPoolExecutor
        default_workers = IOS_WORKERS
        return line_width, t_pool_ex, default_workers
    else:
        line_width = shutil.get_terminal_size((80, 24)).columns
        p_pool_ex = concurrent.futures.ProcessPoolExecutor
        default_workers = cpu_count() + 1
        return line_width, p_pool_ex, default_workers
