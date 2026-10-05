"""Create review images without treating pixel similarity as visual approval."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True)
    parser.add_argument('--after', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    before_path = Path(args.before).expanduser().resolve(strict=True)
    after_path = Path(args.after).expanduser().resolve(strict=True)
    out = Path(args.output_dir).expanduser().resolve()
    if out.exists():
        parser.error('output directory exists; use a unique review directory')
    from PIL import Image, ImageChops, ImageDraw, ImageOps
    with Image.open(before_path) as image:
        before = ImageOps.exif_transpose(image).convert('RGBA')
    with Image.open(after_path) as image:
        after = ImageOps.exif_transpose(image).convert('RGBA')
    sizes = [list(before.size), list(after.size)]
    aspect_delta = abs(before.width / before.height - after.width / after.height)
    same_aspect = aspect_delta < 1e-6
    # Composite transparency on the same declared neutral ground, never silently drop alpha.
    def flatten(image):
        bg = Image.new('RGBA', image.size, (32, 32, 32, 255))
        return Image.alpha_composite(bg, image).convert('RGB')
    before, after = flatten(before), flatten(after)
    thumbs = []
    for image in (before, after):
        thumb = image.copy()
        thumb.thumbnail((1000, 900), Image.Resampling.LANCZOS)
        thumbs.append(thumb)
    panel_width = max(image.width for image in thumbs)
    panel_height = max(image.height for image in thumbs)
    sheet = Image.new('RGB', (panel_width * 2 + 24, panel_height + 50), (32, 32, 32))
    draw = ImageDraw.Draw(sheet)
    for idx, image in enumerate(thumbs):
        x = idx * (panel_width + 24)
        sheet.paste(image, (x + (panel_width - image.width) // 2, 30))
        draw.text((x + 8, 8), 'BEFORE' if idx == 0 else 'AFTER', fill='white')
    out.mkdir(parents=True, exist_ok=False)
    sheet.save(out / 'side-by-side.png')
    artifacts = ['side-by-side.png']
    comparison_size = None
    warnings = ['Camera, crop, lighting, exposure and render settings require separate verification.']
    if same_aspect:
        target = before.size if before.width <= after.width else after.size
        a = before.resize(target, Image.Resampling.LANCZOS)
        b = after.resize(target, Image.Resampling.LANCZOS)
        comparison_size = list(target)
        Image.blend(a, b, 0.5).save(out / 'overlay.png')
        ImageChops.difference(a, b).save(out / 'difference.png')
        artifacts += ['overlay.png', 'difference.png']
        if sizes[0] != sizes[1]:
            warnings.append('Images resampled to smaller input size without changing aspect ratio.')
        if ImageChops.difference(a, b).getbbox() is None:
            warnings.append('Compared pixels are identical; this is not evidence of improvement.')
    else:
        warnings.append('Aspect ratios differ; overlay and difference omitted to avoid distortion.')
    hashes = []
    for path in (before_path, after_path):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        hashes.append(digest.hexdigest())
    report = {'schema_version': 1, 'status': 'review_required',
              'before': str(before_path), 'after': str(after_path),
              'input_sizes': sizes, 'input_sha256': hashes,
              'alpha_background_rgb': [32, 32, 32],
              'comparison_size': comparison_size,
              'warnings': warnings, 'artifacts': artifacts,
              'semantic_review_required': True}
    with (out / 'comparison.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'status': report['status'], 'output_dir': str(out),
                      'warnings': warnings}, ensure_ascii=False))


if __name__ == '__main__':
    main()
