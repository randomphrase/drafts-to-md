#!/usr/bin/env python3

import argparse
import json
import os
import re

from pathlib import Path
from datetime import datetime
from typing import NamedTuple, Iterable, Sequence, Tuple, Dict, Mapping
from collections import defaultdict

import frontmatter

from dateutil import parser


# Controls how titles are extracted from an individual note
RE_SEP = r"[.\n]"
MAX_TITLE_LEN = 40

# Convert bad chars in a title to a legal filename with this translation
TITLE_TO_FILENAME = str.maketrans({
    '/': '_',
    ':': '-',
})

# these keys are copied into the frontmatter of each note. Currently there are no standard
# frontmatter variables for this information, but hopefully there will be one day. In the meantime
# we want to preserve this information.
METADATA_KEYS = frozenset(['created_latitude', 'created_longitude',
                           'modified_latitude', 'modified_longitude'])


class Note(NamedTuple):
    """Note and associated metadata."""

    metadata: dict[str, str]
    created: datetime
    modified: datetime
    content: str


def parse_infile(infile) -> Iterable[Tuple[str, Note]]:
    """Parse exported json file and return (path, note) tuples."""
    for entry in json.load(infile):
        res = re.split(RE_SEP, entry['content'], maxsplit=1)
        if len(res) == 2 and len(res[0]) < MAX_TITLE_LEN:
            title, entry['content'] = res
        else:
            # no obvious title, let the dedup function assign one
            title = ''

        yield title.translate(TITLE_TO_FILENAME), Note(
            {k: v for k, v in entry.items() if k in METADATA_KEYS},
            parser.isoparse(entry['created_at']),
            parser.isoparse(entry['modified_at']),
            entry['content'])


def dedup_paths(notes: Mapping[str, Sequence[Note]],
                dedup_scheme: str) -> Dict[str, Note]:
    """Create unique keys for notes by applying successive transformations."""
    # build up working dict with uniquified keys from notes:
    working: Dict[str, list[Note]] = defaultdict(list)

    def _prepend_date(path: str, note: Note) -> str:
        return f"{note.created:%Y-%m-%d} {path}"

    def _prepend_datetime(path: str, note: Note) -> str:
        # if the date was added previously we'll remove it and add the datetime
        path = path.removeprefix(f'{note.created:%Y-%m-%d}')
        return f"{note.created:%Y-%m-%d %H-%M-%S} {path}"

    def _append_seqno(path: str, _: Note) -> str:
        for seqno in range(1, 1000):
            newpath = f"{path} {seqno}"
            if newpath not in working:
                return newpath
        raise RuntimeError(f"could not dedup path: {path}")

    dedup_schemes = {
        'datetime': (_prepend_date, _prepend_datetime, _append_seqno),
        'seqno':  (_prepend_date, _append_seqno)
    }

    for uniquify_fn in dedup_schemes[dedup_scheme]:
        for path, dups in notes.items():
            if len(dups) > 1:
                for dup in dups:
                    newpath = uniquify_fn(path, dup).rstrip()
                    working[newpath].append(dup)
            else:
                working[path].extend(dups)

        # check to see if working dict is fully uniquified by attempting to build a result dict
        result: Dict[str, Note] = {}
        for path, dups in working.items():
            if len(dups) > 1:
                result.clear()
                break
            result[path] = dups[0]

        if result:
            # success, we built the result dict, so return it
            return result

        # still some dups, so reset and try the next uniquify function:
        notes, working = working, notes
        working.clear()

    raise RuntimeError("Could not dedup notes successfully, aborting")


def write_note(path: Path, note: Note):
    # Note there is currently no way to set the creation date of a file, hence as a temporary
    # measure we set a frontmatter variable. This is not currently supported by Obsidian, but
    # hopefully it could be some day. For completeness, we also set the modified time in
    # frontmatter. Further discussion here:
    # https://forum.obsidian.md/t/store-a-creation-timestamp-as-metadata-of-a-note-and-use-it-for-sorting/19363
    note.metadata.update({
        'created': note.created.isoformat(),
        'modified': note.modified.isoformat()
    })
    with open(path, 'wb') as f:
        frontmatter.dump(note, f)
    # we can at least set the modification date so let's do that
    os.utime(path, (note.created.timestamp(), note.created.timestamp()))


def parse_cmdline():
    parser = argparse.ArgumentParser(description="Convert Drafts notes into Obsidian-compatible Markdown with frontmatter")
    parser.add_argument("infile", type=argparse.FileType(), nargs='?',
                        default="DraftsExport.json", help="path to DraftsExport.json file")
    parser.add_argument("outdir", type=Path, nargs='?', default=Path.cwd(),
                        help="directory to write export files")
    parser.add_argument("--overwrite", action='store_true',
                        help="Allow overwriting existing files")
    parser.add_argument("--dedup", type=str, default="datetime", choices=('datetime', 'seqno'),
                        help="Filename deduplication scheme")
    return parser.parse_args()


def main():
    args = parse_cmdline()

    notes_dups: Dict[str, Sequence[Note]] = defaultdict(list)
    n_notes = 0
    for path, note in parse_infile(args.infile):
        n_notes += 1
        notes_dups[path].append(note)
    print(f'{n_notes} notes read from {getattr(args.infile, "name", "<stdin>")}')
    if not n_notes:
        raise RuntimeError('Aborting, no notes read from input')

    notes: Dict[Path, Note] = {(args.outdir / p).with_suffix('.md'): n
                               for p, n in dedup_paths(notes_dups, args.dedup).items()}

    if not args.overwrite:
        existing = [p for p in notes if p.exists()]
        if existing:
            raise RuntimeError(f"Aborting, use '--overwrite' to overwrite existing file {existing[0]}")

    print(f'writing out {len(notes)} notes to {args.outdir}')
    for path, note in notes.items():
        write_note(path, note)


if __name__ == '__main__':
    main()
