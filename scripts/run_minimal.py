#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

# ensure project root is on sys.path so local imports work when script is run
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.ocr_pipeline import OCRPipeline


def main():
    p = argparse.ArgumentParser(description='Run OCR and print minimal appointment fields')
    p.add_argument('image', help='image path')
    p.add_argument('--date', help='override appointment_date')
    p.add_argument('--time', help='override appointment_time')
    p.add_argument('--prep', help='override preparation_instruction')
    args = p.parse_args()

    pipeline = OCRPipeline()
    result = pipeline.run(Path(args.image))

    sd = result.get('structured_data') or {}
    out = {
        'appointment_date': args.date if args.date is not None else sd.get('appointment_date') or 'ไม่พบ',
        'appointment_time': args.time if args.time is not None else sd.get('appointment_time') or 'ไม่พบ',
        'preparation_instruction': args.prep if args.prep is not None else sd.get('preparation_instruction') or 'ไม่พบ',
    }

    # normalize time: strip trailing Thai "น" and dots
    if out['appointment_time'] and out['appointment_time'] != 'ไม่พบ':
        t = out['appointment_time']
        t = t.replace('น.', '').replace('น', '').strip()
        out['appointment_time'] = t

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
