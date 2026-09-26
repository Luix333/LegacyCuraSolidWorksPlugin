Third-party code bundled with this plugin, because Cura 5 ships neither comtypes nor pywin32.

| Package  | Version | License                                   | Source                               |
|----------|---------|-------------------------------------------|--------------------------------------|
| comtypes | 1.4.17  | MIT ([comtypes-LICENSE.txt](comtypes-LICENSE.txt)) | https://pypi.org/project/comtypes/1.4.17/ |

The copy is the unmodified wheel contents with the `comtypes/test` package removed.
comtypes is pure Python (it only needs `ctypes`), so the same copy works on every
Cura 5.x build regardless of its Python version.
