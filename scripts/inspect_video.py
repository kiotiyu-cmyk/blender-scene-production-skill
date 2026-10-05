"""Inspect a rendered video without modifying it; technical checks are not visual approval."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


def positive_int(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return n


def positive_float(value):
    n = float(value)
    if not math.isfinite(n) or n <= 0:
        raise argparse.ArgumentTypeError('must be finite and positive')
    return n


def positive_rate(value):
    try:
        rate = Fraction(value)
        if rate <= 0:
            raise ValueError()
        return rate
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError('use a positive rate, e.g. 24 or 24000/1001')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True, help='new JSON report; existing files are refused')
    parser.add_argument('--expect-width', type=positive_int)
    parser.add_argument('--expect-height', type=positive_int)
    parser.add_argument('--expect-fps', type=positive_rate)
    parser.add_argument('--expect-frames', type=positive_int)
    parser.add_argument('--expect-duration', type=positive_float)
    parser.add_argument('--decode', action='store_true', help='decode the entire first video stream with FFmpeg')
    parser.add_argument('--ffprobe', default='ffprobe')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_file():
        parser.error('input must be an existing file')
    if output == source or output.suffix.lower() != '.json':
        parser.error('output must be a separate JSON file')
    if output.exists():
        parser.error('output exists; choose a unique report filename')
    probe = shutil.which(args.ffprobe)
    decoder = shutil.which(args.ffmpeg) if args.decode else None
    if not probe or (args.decode and not decoder):
        parser.error('required ffprobe/ffmpeg executable was not found')

    report = {
        'schema_version': 1,
        'source': str(source),
        'status': 'technical_checks_failed',
        'visual_review_required': True,
        'checks': [],
        'errors': [],
        'decode': 'not_requested',
        'not_evaluated': ['composition', 'camera collision', 'motion smoothness',
                          'flicker', 'audio quality', 'equivalence to the Blender scene'],
    }
    command = [probe, '-v', 'error', '-select_streams', 'v:0']
    if args.expect_frames:
        command.append('-count_frames')
    command += ['-show_entries',
                'stream=codec_name,width,height,avg_frame_rate,nb_frames,nb_read_frames,duration:format=duration,size',
                '-of', 'json', str(source)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode or result.stderr.strip():
            raise ValueError('ffprobe: ' + (result.stderr.strip()[-4000:] or f'exit {result.returncode}'))
        data = json.loads(result.stdout)
        streams = data.get('streams', [])
        if not streams:
            raise ValueError('no video stream found')
        stream = streams[0]
        report['metadata'] = data
        fps = Fraction(stream.get('avg_frame_rate', '0/1'))
        if fps <= 0:
            raise ValueError('missing or invalid average frame rate')
        duration = float(stream.get('duration', data.get('format', {}).get('duration', 'nan')))
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('missing or invalid duration')

        def check(name, actual, expected, passed):
            report['checks'].append({'name': name, 'actual': actual,
                                     'expected': expected, 'passed': passed})
            if not passed:
                report['errors'].append(f'{name}: expected {expected}, got {actual}')

        for key, expected in [('width', args.expect_width), ('height', args.expect_height)]:
            actual = stream.get(key)
            if not isinstance(actual, int) or actual <= 0:
                raise ValueError(f'invalid {key}')
            if expected is not None:
                check(key, actual, expected, actual == expected)
        if args.expect_fps is not None:
            check('average_fps', str(fps), str(args.expect_fps), fps == args.expect_fps)
        if args.expect_frames is not None:
            actual = stream.get('nb_read_frames')
            check('decoded_frame_count', actual, args.expect_frames,
                  actual not in (None, 'N/A') and int(actual) == args.expect_frames)
        if args.expect_duration is not None:
            tolerance = max(0.001, 1 / float(fps))
            report['duration_tolerance_seconds'] = tolerance
            check('duration_seconds', duration, args.expect_duration,
                  abs(duration - args.expect_duration) <= tolerance)
        if args.decode:
            decoded = subprocess.run([decoder, '-hide_banner', '-v', 'error', '-xerror',
                                      '-err_detect', 'explode', '-i', str(source),
                                      '-map', '0:v:0', '-an', '-f', 'null', '-'],
                                     capture_output=True, text=True, check=False)
            if decoded.returncode or decoded.stderr.strip():
                report['decode'] = 'failed'
                report['errors'].append('FFmpeg decode: ' +
                                        (decoded.stderr.strip()[-4000:] or f'exit {decoded.returncode}'))
            else:
                report['decode'] = 'passed'
        if not report['errors']:
            report['status'] = 'technical_checks_passed'
    except (OSError, ValueError, ZeroDivisionError, TypeError) as exc:
        report['errors'].append(str(exc))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'status': report['status'], 'output': str(output),
                      'visual_review_required': True, 'errors': report['errors']}, ensure_ascii=False))
    return 0 if report['status'] == 'technical_checks_passed' else 1


if __name__ == '__main__':
    sys.exit(main())
