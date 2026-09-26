# Testing the plugin inside Cura

`CuraTestProbe` is a test-only Cura plugin that lets a script drive a running Cura: every line appended to
`CuraTestProbe/probe_cmds.txt` is executed once, and results are appended to `CuraTestProbe/probe_out.txt`.
It is not part of the package. Its `eval` command runs arbitrary Python, so only ever install it in a throwaway
configuration.

## A throwaway Cura configuration

Cura keeps everything under `%APPDATA%\cura\<version>`, and it reads `APPDATA` from the environment, so a copy is
easy to run next to your normal Cura:

1. Copy `%APPDATA%\cura\5.13` to `<test>\Roaming\cura\5.13` (or start from an empty folder with a minimal
   `cura.cfg`; `accepted_user_agreement = True` skips the welcome pages).
2. In the copy's `cura.cfg`:
   * set `single_instance = False`: otherwise the test Cura hands its files to the Cura you are running and quits;
   * delete the `ultimaker_auth_data` line: a second Cura using your login would make cloud backups of the test
     configuration and can rotate the refresh token of your real session.
3. Put this plugin (a copy or a directory junction) and `CuraTestProbe` into `<test>\Roaming\cura\5.13\plugins`.
4. Start Cura with `APPDATA=<test>\Roaming` and `LOCALAPPDATA=<test>\Local`.

If the copied printer doesn't load, Cura refuses to place meshes ("Can't load meshes before a printer is added");
`eval app.getMachineManager().addMachine('creality_ender3')` adds a stock one.

## Commands

| Command | Does |
|---|---|
| `open <path>` | Opens a file, as File > Open does. |
| `dialog accept <quality index> <remember 0/1>` | Sets the quality dialog's controls and accepts it; `dialog reject` and `dialog close` cancel it. |
| `dump` | Lists the scene nodes: name, type, bounding box size and bottom, linked file, MIME type. |
| `grab <path prefix>` | Saves every visible Cura window as `<prefix>_<n>.png` (the 3D view included). |
| `menu <item>` | Activates an Extensions menu item, e.g. `menu Configure`. |
| `pref <key> <value>`, `getpref <key>` | Sets or reads a preference. |
| `reload`, `clear`, `quit` | Reload All, clear the build plate, close Cura (saving its configuration). |
| `windows`, `plugins <id>`, `eval <expression>` | Debugging helpers. |

For example, a part drawn on SolidWorks' Top plane as a 40 x 20 mm rectangle extruded 5 mm should `dump` as
`size=(40.0, 5.0, 20.0) bottom=0.0`: flat on the plate, the way it lies in SolidWorks.
