# AutoBim

AutoBim is a simple bed tramming utility for OctoPrint using ABL. Tramming is the process of making sure your bed is as
parallel to your printer's X axis as possible. Or, put simply:

`Tilted Bed + Tramming = Parallel Bed`

## Alternatives

This functionality seems to be part of `bugfix-2.0.x` branch at the time of writing, i.e. see
[here](https://github.com/MarlinFirmware/Configurations/blob/526f5a70495fd1fbe4161924450d949a3fbefd6b/config/default/Configuration.h#L1460-L1464)

So if you may want to check out that before using this plugin.

## Why should I use it?

#### Doesn't Marline already account for a tilted bed that if I have an ABL?

Yes, but it really shouldn't. Imho ABL should be used for correcting irregularities in bed surface (warps, bumps, etc.)
and for having the same distance to the bed on every print (think different beds, different bed temps, etc.). Tilted
beds should be dealt with in hardware, not in software.

#### Couldn't I just use a piece of paper for levelling as I did before getting an ABL probe?

Sure, but where is the fun in that?

#### I use `insert any other method here`. Is this more accurate than my method?

I think that depends on the method, and even more on how good you are at your method. It may, it may not.

## Requirements

* OctoPrint (duh)
* ABL probe, such as BLTouch
* Marlin firmware with support for
  * [`G30` - Single Z-Probe](https://marlinfw.org/docs/gcode/G030.html)
    * Send `G30 X30 Y30` over OctoPrints Terminal. Make sure to home the printer before you do.
  * [`M117` - Set LCD Message](https://marlinfw.org/docs/gcode/M117.html)
    * Send `M117 Hello World` over OctoPrints Terminal and look for `Hello World` on the printer's screen

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/j-be/AutoBim/archive/master.zip

## Configuration

None yet.

Planned are (ordered by assumed priority):

* Corner points - currently its hard-coded to an Ender 3's `(30, 30), (200, 30), (200, 200), (30, 200)`.
* Accuracy threshold (currently dependent on what precision Marlin returns on `G30` - in my cas `0.01`)
* Enable/Disable multi-pass (i.e. go on until a full round measures ok)
* Invert arrows on display for inverse screw threads
* Pattern for `G30` response parsing

## Why the name?

This plugin is meant to help with bed tramming. I am from Vienna, and [trams](https://en.wikipedia.org/wiki/Tram) in
Vienna are called "Bim" (like "bin" as in "trash bin", just with an `m` instead of the `n`).

## Credits

Credit goes to the following projects for being there and letting me look at and copy their code:

* https://github.com/jneilliii/OctoPrint-BedLevelVisualizer
* https://github.com/marian42/octoprint-preheat

Make sure to check them out, and don't forget:

> "Toss a coin to your developers, o valley of plenty, o valley of plenty..."
