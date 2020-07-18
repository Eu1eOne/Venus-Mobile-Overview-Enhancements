# Venus-Mobile-Overview-Enhancements
This replaces the Mobile Overview page in Victron Venus OS to add additional information

A new file: SystemReasonMessage.qml is added to provide text readout of ESS "reason codes"

This version supports Venus versions 2.4 and 2.5 and 2.60 release candidates through 35

Changes to the screen:
  Removed logo and added AC INPUT and SYSTEM tiles originally displayed on other overviews
  Merged SYSTEM and STATUS tiles
  Added voltage, current and frequency to AC INPUT and AC LOADS tiles
  Rearranged tiles to match a left to right signal flow : sources on left, loads on right - more or less
  Large text for main parameter in each tile has been reduced in size to allow more parameters without
  expanding tile height
  Removed speed from STATUS to reduce tile height
  Hide "reason" text if it's blank to save space
  Changed clock to 12-hour format
  Capitialized battery state: "Idle", "Charging", "Discharging"
  Tiles for subsystems were originally hidden, causing tiles within a column to resize
  This behavior is changed, keeping all tiles in place but hiding informaiton within the tile
  Adjusted button widths so that pump button fits within tank column
  Hide pump button when not enabled giving more room for tanks
  All tiles (except tank info) is within a single ListView rather than in separate columns
  making it easier to rearrange, add or remove tiles

  Code was also added to hide a SeeLevel dBus (NMEA2000 tank sensor) service if present
  because that object constantly switches tanks
  These changes have no effect on other tanks or systems
  
  Show ESS "reason codes" as text rather than "#1", etc.
  Combine ESS reason codes with the notification Marquee, saving vertical space on the tile.

All changes are included in a two files file: OverviewMobile.qml, SystemReasonMessage.qml.
To install, rename the existing OverviewMobile.qml file in /opt/victronenergy/gui/qml to preserve it in case you wish to back out the changes in the future.
Copy both of these files to the same directory.
You will need to kill the gui process or reboot the CCGX to see the changes.


