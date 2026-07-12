from __future__ import annotations

import platform
import sys


def main() -> int:
    print(f"platform.machine: {platform.machine()}")
    print(f"python: {sys.version}")

    try:
        import cv2

        print(f"cv2: {cv2.__version__}")
    except Exception as exc:  # noqa: BLE001
        print(f"cv2: FAIL ({type(exc).__name__}: {exc})")
        return 1

    try:
        import paddle

        print(f"paddle: {paddle.__version__}")
    except Exception as exc:  # noqa: BLE001
        print(f"paddle: FAIL ({type(exc).__name__}: {exc})")
        return 1

    try:
        from paddleocr import TextRecognition

        model = TextRecognition(
            model_name="PP-OCRv5_server_rec",
            model_dir="./models/paddle/th_PP-OCRv5_mobile_rec",
        )
        print(f"paddleocr: PASS ({type(model).__name__})")
    except Exception as exc:  # noqa: BLE001
        print(f"paddleocr: FAIL ({type(exc).__name__}: {exc})")
        return 1

    print("runtime_check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
