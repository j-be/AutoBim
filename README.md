# AutoBim

AutoBim is a simple bed tramming utility for OctoPrint using ABL. Tramming is the process of making sure your bed is as
parallel to your printer's X axis as possible. Or, put simply:

`Tilted Bed + Tramming = Parallel Bed`

## How does it work

The plugin adds a single button to OctoPrint's navbar, because that's all it needs. When the button is clicked, a
combination of GCodes `G0`, `G28`, `G30`, `M117` and a bit of message parsing is used to create something like
[this (link to YouTube)](https://www.youtube.com/watch?v=iXtuS8pXz94&start=190). Jump to 3:10 if it didn't already.

## Alternatives

This functionality seems to be part of `bugfix-2.0.x` branch at the time of writing, i.e. see
[here](https://github.com/MarlinFirmware/Configurations/blob/526f5a70495fd1fbe4161924450d949a3fbefd6b/config/default/Configuration.h#L1460-L1464)

So you may want to check out that before using this plugin.

## Why should I use it?

#### Doesn't Marlin already account for a tilted bed if I have an ABL probe?

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

**Hint:** Keep your hands away from the printer whenever possible. This not only reduces the risk of your hand colliding
with the knob (and thus putting it out of level again) because the printer suddenly moves. It also seems to increase
measurement accuracy, at least of my BL Touch. So: wait, adjust, hands off, wait, adjust, hands off, ...

## Preparation

### Check XY Probe Offset

Marlin needs to know where your probe is relative to the nozzle. This position is known as *XYZ Probe Offset*. While
pretty much everybody will have Z offset calibrated, X and Y are sometimes neglected. They shouldn't though, they are
important, too.

To check, send the following commands to the printer (e.g. via OctoPrint's Terminal) or do it any other way you are
comfortable doing it:

1. `G28`;  Home the printer
1. `G0 Z20`; Move the nozzle up so it is a safe distance from the bed. I consider 20mm to be safe, feel free to use a
   different value.
1. `G0 X30 Y30`; Probe X=30, Y=30
1. Mark the exact spot below the nozzle. This can e.g. be done be putting a piece of paper on the bed and marking the
   spot there. If you have a glass bed and a marker you know you can remove without residue, use that. Feel free to
   lower the nozzle a little bit if that makes it easier.
1. `G30 X30 Y30`; Probe the point. The printer should now move the probe to the point we marked in the step above.

If it probed the point your printer is correctly set up. If not, check out
[M851 in Marlin documentation](https://marlinfw.org/docs/gcode/M851.html) for further information on the topic.

## Configuration

Defaults are for an Ender 3 sized printer and a BLTouch. You can configure:

* Enable/Disable multi-pass (i.e. go on until a full round measures ok)
  * Default: `On`
* Invert arrows on display, e.g. for inverse screw threads on the adjustment screws
  * Default: `Off`
* Accuracy threshold
  * Default: `0.01`
* Points to probe
  * Default: `(30, 30), (200, 30), (200, 200), (30, 200)` (Ender 3)
  * Note: These coordinates refer to *probe* position, while most other coordinates (e.g. what is displayed on screen)
    refer to *nozzle* position. Try to use the points exactly above the set screws if that is possible (see **Works fine
    on the first corner, display says `ok. moving to next` but nothing happens** below) or get as close as possible.

Planned are (ordered by assumed priority):

* Allow for a different amount of probe points
* Pattern for `G30` response parsing

## What is supposed to happen

Since there are quite some unknowns in the process, here a list of what **should** happen when you click the button in
the navbar:

| Step |                                                                                                                        | You | Message on Display |
|------|------------------------------------------------------------------------------------------------------------------------|-----|--------------------|
| 1 | Home | | `wait...` |
| 2 | Raise to Z=20 | | `wait...` |
| 3 | Go to corner point and probe | | `wait...` |
| 4 | Display difference and direction to rotate the knob | Turn the leveling wheel/knob/lever | e.g. `0.16 >>>>>` for 0.16mm to high, turn right (i.e. counter-clockwise) to correct |
| 5 | Printer goes on probing until the difference is within threshold | Turn the leveling wheel/knob/lever | e.g. `-0.01 <` for 0.01mm to low, turn left (i.e. clockwise) to correct              |
| 6 | Measurement is within threshold | | `ok. moving to next` |
| 7 | If full round completed without a difference, we are done | | `done.`
| | Else, go to *Step 3* for the next corner | | `ok. moving to next` |

If that is not what happens look at **Troubleshooting** below. If that doesn't help consider opening an issue detailing
where it goes wrong, how, and (if you have a suspicion) why.

## Troubleshooting

### Works fine on the first (or first and second corner), display says `ok. moving to next` but nothing happens

Most likely that means the printer cannot reach the point set in *Points to probe* because it would need move beyond
what it considers to be its moving range. This is a feature known as "software endstops" in Marlin.

For your X axis, the most likely issue is `X_MAX_POS` set in the firmware. For most builds this will default to
`X_BED_SIZE`, but on most printers it should be possible to raise this a little bit, e.g. on my Ender 3 Pro this can be
set to 245 as it can easily move the nozzle 10mm left of the bed. It won't ever print there - that's what `X_BED_SIZE`
is for - but moving there temporarily, e.g. for probing, is fine. The same applies to `Y`, i.e. on an Ender 3 Pro you
can set it to 240.

Another reason could be, that `PROBING_MARGIN` in your firmware is set to something, that makes no sense. E.g. I heard
Ender 6 stock firmware seems to set `Y_BED_SIZE` to 260, the bed is 290 in depth, and Creality - in there infinite
wisdom - still seems to have decided to apply an additional `PROBING_MARGIN` of 30. This effectively makes 230 the
maximum usable Y coordinate for probing.

As to why the plugin doesn't react to this condition: At least on my machine there is no indication on the log, that the
printer can't do what it was told. I get an `ok`, which I find misleading at least. If you have an idea on how to catch
this error, which doesn't involve timing the response time on a `G30`, feel free to open an issue for that.

I found the following sequence in OctoPrint's Terminal to work well. Assuming you'd like to find the maximum `Y` value:

* `G28`; Home the printer
* `G0 Z20`; Raise hotend to Z=20 to avoid collisions while moving
* `G30 X30 Y195`; Tell printer to probe X=30 Y=195
  * If printer doesn't move try `G30 X30 Y190`
  * If printer moves try `G30 X30 Y192`
* ... and so on, until you found the maximum Y value
* Take that value and use it as the upper Y value in *Points to probe*

Also, please check out if #2 sounds like a good solution to the problem, and give it a thumbs up or thumbs down
respectively. Please don't comment to `+1`, I'd appreciate it.

As a **last resort** and if you have **no other possibility** you may consider temporarily disabling endstops in Marlin
using the `M121` command. Doing that could cause serious damage to your bed or printer, so once you did that **always
have your hand on the power switch** - just in case. When you are done, **be sure to reenable the endstops** using
`M120`. *You have been warned!*

### Printer homes, moves to first corner, probes, then nothing happens. Display is stuck on `wait...`

This most probably means that your printer returns the measured coordinates in a format different than mine does. To
check this, please go to OctoPrint's Terminal and enter a `G30` (make sure you homed before and raised your hotend a
little bit to avoid collisions). I'd recommend the following sequence:

1. `G28`;  Home the printer
1. `G0 Z20`; Move the nozzle up so it is a safe distance from the bed. I consider 20mm to be safe, feel free to use a
   different value.
1. `G30 X30 Y30`; Probe X=30, Y=30

On my printer I see the following (irrelevant stuff and `Recv: echo:busy: processing` removed for brevity):

```
Send: G28
[...]
Recv: X:159.00 Y:122.00 Z:12.03 E:0.00 Count X:12720 Y:9760 Z:4812
Recv: ok
[...]
Send: G0 Z20
Recv: ok
[...]
Send: G30 X30 Y30
[...]
Recv: Bed X: 30.00 Y: 30.00 Z: 0.00
Recv: X:72.00 Y:35.00 Z:12.03 E:0.00 Count X:5760 Y:2800 Z:4812
Recv: ok
```

I am most interested in if there is a line like the `Recv: Bed X: 30.00 Y: 30.00 Z: 0.00` above. If yours contains the
same information, but looks different, let me know, I'm happy to add that as a setting.


### I can't seem to get a full round complete - there is always one point, that is +/-0.01 off. Is something broken?

Most probably not. By using 0.01mm as threshold we are close to the BLTouch's tolerance, which means that there is
already a little luck involved, too. It can take some 5, 6 rounds (and more) with only some corners off by +/-0.01 until
a full run completes. If you don't care that much, you can always raise *Accuracy threshold* in the settings. Note, that
Marlin (at least my build does this) reports only 2 decimal digits, so a setting of `0.011` will have the same effect as
`0.02`. At the time of writing, Marlin's presumably equivalent `LEVEL_CORNERS_USE_PROBE` feature uses `0.1` as tolernace
by default (see [here](https://github.com/MarlinFirmware/Configurations/blob/526f5a70495fd1fbe4161924450d949a3fbefd6b/config/default/Configuration.h#L1462).

Additionally, keep in mind that changing one of the corners may affect other corners as well - which is why the plugin
does the multi-pass in the first place. The closer your probe points are to the set screws, the less the influence. So
you may want to spend a little time getting those right.

## Printer does a 3-point leveling at start of tramming

This means your firmware was compiled with [Unified Bed Leveling](https://marlinfw.org/docs/features/unified_bed_leveling.html).
Open the plugin settings and check the `UBL (Unified Bed Leveling)` checkbox.

## Why is it so slow? Why doesn't the plugin read `some value` from the printer?

Unfortunately, all parameters referring to probing seem to be hardcoded in Marlin and are not readable via GCode. It
seems, for example, the plugin is not able to override the amount the hotend is raised after probing (I think that
should be `LEVEL_CORNERS_Z_HOP`, but I'm not even sure on that), which would be great to save some time.

Also, there seems to be no way to read stuff like `TRAMMING_POINT_XY` and `TRAMMING_SCREW_THREAD`, so I need to add them
as settings.

That said: I am far from being an expert on Marlin. If you know a way to set them via G-Code, please open an issue
detailing on how one can do that and I will definitely have a look at it.

## Why the name?

This plugin is meant to help with bed tramming. I am from Vienna, and [trams](https://en.wikipedia.org/wiki/Tram) in
Vienna are called "Bim" (like "bin" as in "trash bin", just with an `m` instead of the `n`).

## Credits

Credit goes to the following projects for being there and letting me look at and copy their code:

* https://github.com/jneilliii/OctoPrint-BedLevelVisualizer
* https://github.com/marian42/octoprint-preheat

Make sure to check them out, and don't forget:

> "Toss a coin to your developers, o valley of plenty, o valley of plenty..."
