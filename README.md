# SolidWorks Integration for Cura 5

Open SolidWorks parts (`*.SLDPRT`) and assemblies (`*.SLDASM`) straight from UltiMaker Cura. The plugin asks your
own SolidWorks installation to convert the file and loads the result, so what you print is exactly what SolidWorks
modelled — and when you save the part again, Cura offers to reload it.

This is a fork of Ultimaker's [LegacyCuraSolidWorksPlugin](https://github.com/Ultimaker/LegacyCuraSolidWorksPlugin),
which stopped working with Cura 5 (Qt 6, Python 3.10/3.12, no bundled COM library). See [what changed](#what-changed).

## Requirements

* Windows, with SolidWorks installed and licensed (2016 or newer; 3MF transfer needs 2017 or newer).
* UltiMaker Cura 5.0 or newer.

Tested with SolidWorks 2023 on Cura 5.4 (Python 3.10) and Cura 5.13 (Python 3.12); other versions use the same APIs
but haven't been tried.

## Installing

**From a package:** drag `CuraSolidWorksPlugin-<version>.curapackage` onto Cura's window, then restart Cura.
Build the package yourself with `python tools/build_package.py` (any Python 3); it lands in `dist/`.

**From source:** copy (or clone) this repository into Cura's plugin folder as `CuraSolidWorksPlugin`, for example
`%APPDATA%\cura\5.13\plugins\CuraSolidWorksPlugin`, and restart Cura.

Remove any other SolidWorks plugin with the same ID first (for example thopiekar's *CuraSolidWorksPlugin*); Cura loads
only one plugin per folder name.

## Using it

* **File > Open** now lists SolidWorks part and assembly files. Cura asks which mesh resolution SolidWorks should use:
  *Fine*, *Coarse*, or *As set in SolidWorks* (your own settings under *Options > Export > STL*). Tick
  *Remember my choice* to stop being asked.
* **Extensions > SolidWorks Integration > Configure** changes that choice and the transfer format:
  * **3MF** (default): keeps separate bodies and the parts of an assembly as separate objects (an assembly arrives as a group).
  * **STL**: one mesh for the whole file.

  The other format is used as a fallback when the preferred one fails.
* **Reload**: the loaded objects stay linked to the SolidWorks file. Cura notices when you save it again and offers to
  reload; *File > Reload All* works too.

Models arrive standing the way they stand in SolidWorks (SolidWorks' Y axis points up in Cura) and are dropped onto
the build plate.

### When SolidWorks is already running

SolidWorks hands every automation client the instance that is already running, so the plugin uses your open SolidWorks
and treats it with care:

* a document you already have open is converted as it is in SolidWorks, **including unsaved changes**, and stays open;
* other documents are opened read-only, converted and closed again, and your active document is switched back;
* the export options the conversion needs are global SolidWorks settings: they are changed for the moment of the save
  and then put back (including *Custom* STL tolerances);
* a file that doesn't look like a SolidWorks file is refused instead of being opened, because a broken file can crash
  SolidWorks and take unsaved work with it.

When SolidWorks isn't running, the plugin starts an invisible instance for the conversion and closes it afterwards.

### The "Export to Cura" button for SolidWorks

`macro/Export_to_Cura.swb` opens the active part or assembly in Cura. Add it as a toolbar button in SolidWorks
(*Tools > Customize > Commands > Macro > New Macro Button*); **Extensions > SolidWorks Integration > How to install the
SolidWorks macro** walks through it and opens the folder with the macro and its icon.

The macro starts the Cura that Windows opens Cura models with (or the newest one in *Program Files*) with
`--single-instance`, so a running Cura with *Use a single instance of Cura* enabled receives the file. Documents that
were never saved have to be saved once first.

## What changed

Compared with the legacy plugin:

* Ported to Cura 5: `supported_sdk_versions` 8.0.0, PyQt6, and all dialogs rewritten with Qt Quick Controls 2 and Cura 5's
  `UM 1.5` / `Cura` components.
* Bundles [comtypes](thirdparty/README.md) (pure Python, MIT), since Cura 5 ships neither comtypes nor pywin32.
  COM is called through explicit late binding, because SolidWorks' dispatch interfaces have no type information.
* Exports the **active** document: SolidWorks' mesh export writes out whichever document is active, so a file opened in
  the background used to produce the geometry of whatever else was open.
* No longer hides the user's running SolidWorks or closes their open documents without saving (the legacy plugin did
  both, because SolidWorks hands automation clients the running instance), and closes the SolidWorks instance it
  started itself (the legacy plugin never did).
* The chosen mesh quality is actually applied (it was ignored), and a *Custom* STL resolution in SolidWorks survives a
  conversion (restoring it by its quality value is silently ignored by SolidWorks; the tolerances have to be restored).
* Turns off SolidWorks' "show info on save" options for the export, whose dialogs could block an invisible SolidWorks.
* The model orientation fix is baked into the mesh: of a plain node returned by a mesh reader, Cura 5 keeps only the
  mesh, so the legacy plugin's node rotation was lost.
* 3MF imports are no longer pinned below the build plate by Cura's 3MF reader.
* Meshes stay linked to the SolidWorks file (reload, file-change prompt) and are named after it.
* Readable errors when SolidWorks can't open or save a file, or crashes.
* The macro is now a plain-text `.swb` that finds Cura 5 (the old `.swp` looked for `Cura.exe` in a registry location
  that Cura 5 no longer uses).

## Development

`tests/convert_standalone.py` runs the SolidWorks side of a conversion without Cura, using any Python 3.9+ on Windows:

    python tests/convert_standalone.py part.SLDPRT --format 3mf --quality fine --check-preferences --expect-extent 40,5,20

It prints the mesh statistics and fails if the export has the wrong size or SolidWorks' preferences weren't restored.

## License

LGPLv3 or later, see [LICENSE](LICENSE). The bundled comtypes is MIT licensed.
