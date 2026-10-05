"""Read a .blend in background Blender without saving or running embedded scripts."""
import argparse
import collections
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    source = Path(args.input).expanduser().resolve(strict=True)
    output = Path(args.output).expanduser().resolve()
    if source.suffix.lower() != '.blend':
        parser.error('input must be a .blend file')
    if output == source or output.suffix.lower() != '.json':
        parser.error('output must be a separate JSON file')
    if output.exists():
        parser.error('output exists; choose a unique review filename')

    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    warnings = []
    file_version = list(bpy.data.version)
    if tuple(file_version[:2]) > tuple(bpy.app.version[:2]):
        warnings.append('File was written by a newer Blender version; data may be lost on read.')
    images = []
    for img in bpy.data.images:
        packed = bool(img.packed_file) or bool(getattr(img, 'packed_files', []))
        entry = {'name': img.name, 'source': img.source, 'users': img.users,
                 'packed': packed, 'size': list(img.size), 'filepath': img.filepath}
        if img.source == 'FILE' and not packed:
            path = Path(bpy.path.abspath(img.filepath, library=img.library)) if img.filepath else None
            entry['file_exists'] = bool(path and path.is_file())
            if img.users > 0 and not entry['file_exists']:
                warnings.append('Missing image: ' + img.name)
        if img.users > 0 and img.source in {'MOVIE', 'SEQUENCE'}:
            warnings.append('Movie/sequence dependency not fully evaluated: ' + img.name)
        images.append(entry)
    libraries = [lib.filepath for lib in bpy.data.libraries]
    if libraries:
        warnings.append('External linked libraries remain; portability is not verified.')
    cameras = []
    for obj in bpy.data.objects:
        if obj.type != 'CAMERA':
            continue
        camera = {'name': obj.name, 'active': obj == scene.camera,
                  'type': obj.data.type, 'lens_mm': obj.data.lens,
                  'position_world': list(obj.matrix_world.translation),
                  'matrix_world': [list(row) for row in obj.matrix_world]}
        for prop in ('panorama_type', 'fisheye_fov', 'fisheye_lens', 'ortho_scale'):
            if hasattr(obj.data, prop):
                camera[prop] = getattr(obj.data, prop)
        cameras.append(camera)
    if scene.camera is None:
        warnings.append('No active render camera.')
    report = {
        'schema_version': 1, 'status': 'warn' if warnings else 'inspection_complete',
        'semantic_review_required': True,
        'source': str(source), 'reader_version': bpy.app.version_string,
        'file_version': file_version, 'warnings': warnings,
        'scope': 'configuration and dependency snapshot; no render or scene save',
        'not_evaluated': ['full topology', 'collision', 'animation', 'render fidelity',
                          'runtime performance', 'unsupported-data fidelity'],
        'scene': scene.name, 'frame': scene.frame_current,
        'engine': scene.render.engine,
        'resolution': [scene.render.resolution_x, scene.render.resolution_y,
                       scene.render.resolution_percentage],
        'view_transform': scene.view_settings.view_transform,
        'look': scene.view_settings.look, 'exposure': scene.view_settings.exposure,
        'gamma': scene.view_settings.gamma,
        'render_border': {'enabled': scene.render.use_border,
                          'crop': scene.render.use_crop_to_border,
                          'bounds': [scene.render.border_min_x, scene.render.border_min_y,
                                     scene.render.border_max_x, scene.render.border_max_y]},
        'cycles_samples': scene.cycles.samples if hasattr(scene, 'cycles') else None,
        'objects': len(bpy.data.objects),
        'object_types': dict(collections.Counter(obj.type for obj in bpy.data.objects)),
        'base_polygons': sum(len(mesh.polygons) for mesh in bpy.data.meshes),
        'modifiers': dict(collections.Counter(mod.type for obj in bpy.data.objects for mod in obj.modifiers)),
        'materials': len(bpy.data.materials), 'images': images,
        'external_libraries': libraries, 'cameras': cameras,
        'embedded_text_names': [text.name for text in bpy.data.texts],
        'capabilities': {name: hasattr(bpy.types, name) for name in
                         ['ShaderNodeRaycast', 'ShaderNodeShaderToRGB', 'GeometryNodeSimulationInput']},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'status': report['status'], 'output': str(output),
                      'warnings': warnings}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
