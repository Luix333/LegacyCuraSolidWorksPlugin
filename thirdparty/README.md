Third-party code bundled with this plugin, because Cura 5 ships neither comtypes nor pywin32.

| Package  | Version | License                                   | Source                               |
|----------|---------|-------------------------------------------|--------------------------------------|
| comtypes | 1.4.17  | MIT ([comtypes-LICENSE.txt](comtypes-LICENSE.txt)) | https://pypi.org/project/comtypes/1.4.17/ |

The copy is the wheel contents with the `comtypes/test` package removed and the patch below.
comtypes is pure Python (it only needs `ctypes`), so the same copy works on every
Cura 5.x build regardless of its Python version.

## Patch: no file names containing "cache"

Cura's Backups feature (`cura/Backups/Backup.py`, `IGNORED_FILES`, the same in Cura 5.4 to 5.13) leaves out every
file whose path matches the regular expression `cache`, both when it makes a backup and when it restores one. A
restored backup used to come back without two comtypes files, and the plugin then failed to load with
"No module named 'comtypes.client._code_cache'". So:

* `comtypes/client/_code_cache.py` is renamed to `comtypes/client/_gen_dir.py` (after `_find_gen_dir()`, the one
  function it provides), and the import in `comtypes/client/__init__.py` follows it. The module's code is unchanged.
* `comtypes/clear_cache.py` is removed. It is the `py -m comtypes.clear_cache` command-line helper and nothing
  imports it.

When updating comtypes, apply the patch again. `tools/build_package.py` refuses to build a package that contains a
path Cura's backups would drop.
