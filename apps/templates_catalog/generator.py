import json
import re
from html import escape
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath


STARTER_FILES_ROOT = Path(__file__).parent / 'starter_files'
MAX_STARTER_FILES = 100
MAX_STARTER_FILE_SIZE = 1_000_000
MAX_STARTER_TOTAL_SIZE = 10_000_000
TEMPLATE_SLUG_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
TEMPLATE_VERSION_PATTERN = re.compile(r'[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*\Z')


class StarterKitUnavailable(Exception):
    pass


def _starter_directory(template):
    if (
        not TEMPLATE_SLUG_PATTERN.fullmatch(template.slug)
        or not TEMPLATE_VERSION_PATTERN.fullmatch(template.version)
    ):
        raise StarterKitUnavailable(
            f'No starter kit is available for {template.slug} {template.version}.'
        )
    root = STARTER_FILES_ROOT.resolve()
    directory = (root / template.slug / template.version).resolve()
    if not directory.is_relative_to(root):
        raise StarterKitUnavailable(
            f'No starter kit is available for {template.slug} {template.version}.'
        )
    return directory


def has_starter_kit(template):
    if template is None:
        return False
    try:
        directory = _starter_directory(template)
    except StarterKitUnavailable:
        return False
    manifest = directory / 'manifest.json'
    return manifest.is_file() and not manifest.is_symlink()


def _safe_archive_path(value):
    if not isinstance(value, str) or '\\' in value:
        raise ValueError('Starter kit manifest contains an invalid archive path.')
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(
        part in {'', '.', '..'} for part in path.parts
    ):
        raise ValueError('Starter kit manifest contains an invalid archive path.')
    return path


def build_project_archive(*, template, project, configuration):
    directory = _starter_directory(template)
    manifest_path = directory / 'manifest.json'
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise StarterKitUnavailable(
            f'No starter kit is available for {template.slug} {template.version}.'
        )
    if manifest_path.stat().st_size > 64_000:
        raise ValueError('Starter kit manifest is too large.')

    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise ValueError('Starter kit manifest must be a JSON object.')
    files = manifest.get('files')
    if (
        not isinstance(files, list)
        or not files
        or len(files) > MAX_STARTER_FILES
        or any(not isinstance(path, str) for path in files)
        or len(set(files)) != len(files)
    ):
        raise ValueError('Starter kit manifest must contain unique file paths.')

    rendered_files = manifest.get('rendered_files', [])
    if (
        not isinstance(rendered_files, list)
        or any(path not in files for path in rendered_files)
    ):
        raise ValueError('Starter kit manifest contains invalid rendered file paths.')

    archive_paths = [_safe_archive_path(file_name) for file_name in files]
    normalized_paths = [str(path) for path in archive_paths]
    if (
        len(set(normalized_paths)) != len(normalized_paths)
        or 'atlascloud-project.json' in normalized_paths
    ):
        raise ValueError('Starter kit manifest contains duplicate or reserved paths.')

    total_size = 0
    archive = BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for file_name, archive_path in zip(files, archive_paths):
            unresolved_source = directory
            for part in archive_path.parts:
                unresolved_source = unresolved_source / part
                if unresolved_source.is_symlink():
                    raise ValueError(
                        f'Starter kit file "{file_name}" must not be a symbolic link.'
                    )
            source = unresolved_source.resolve()
            if (
                not source.is_relative_to(directory)
                or source.is_symlink()
                or not source.is_file()
                or source.stat().st_size > MAX_STARTER_FILE_SIZE
            ):
                raise ValueError(
                    f'Starter kit file "{file_name}" is missing or invalid.'
                )
            total_size += source.stat().st_size
            if total_size > MAX_STARTER_TOTAL_SIZE:
                raise ValueError('Starter kit files exceed the maximum total size.')
            content = source.read_text(encoding='utf-8')
            if file_name in rendered_files:
                context = {
                    '{{PROJECT_NAME}}': escape(project.name, quote=True),
                    '{{PROJECT_SLUG}}': escape(project.slug, quote=True),
                    '{{PROJECT_DESCRIPTION}}': escape(
                        project.description,
                        quote=True,
                    ),
                }
                pattern = re.compile('|'.join(re.escape(key) for key in context))
                content = pattern.sub(
                    lambda match: context[match.group(0)],
                    content,
                )
            bundle.writestr(str(archive_path), content)

        metadata = {
            'project': {
                'name': project.name,
                'slug': project.slug,
                'description': project.description,
            },
            'template': {
                'name': template.name,
                'slug': template.slug,
                'version': template.version,
            },
            'configuration': configuration,
        }
        bundle.writestr(
            'atlascloud-project.json',
            json.dumps(metadata, indent=2, ensure_ascii=False),
        )

    return archive.getvalue()
