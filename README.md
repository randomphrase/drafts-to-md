# drafts-to-md

A basic converter for [Drafts](https://getdrafts.com/) to Markdown files.

This script parses the contents of a Drafts backup/export file, and produces a Markdown file for each note contained therein. The resulting Markdown files are enhanced with frontmatter and are intended for use with Obsidian.

There are several important features of this script:

 * Filename generation. For each note, this script determines a suitable filename based on the initial line/sentance of the note itself.
 * Filename de-duplication. In the likely event of notes with duplicate filenames, this script attempts to construct unique filenames by adding unique information such as date/time and sequence numbers.
 * Metadata preservation. Some Drafts metadata - such as location information - is not currently convertible to Obsidian, but this script attempts to at least preserve it for future use.

### Installation

Clone this repo to a suitable directory, and use [pipenv](https://pipenv.pypa.io/en/latest/) to install dependencies.

    $ pipenv install

### Use

Use the [Backup feature](https://docs.getdrafts.com/docs/settings/backups) of Drafts to create an export file.

Convert the drafts export file by providing your Drafts export file and a destination directory. It may be useful to use a temporary directory so that you can inspect the contents manually before moving the notes into an Obsidian vault.

    $ ./drafts-to-md.py DraftsExport.json tmp
    518 notes read from DraftsExport.json
    writing out 518 notes to tmp

