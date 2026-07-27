# OBD-Insight

OBD-Insight is a Windows companion application that makes vehicle diagnostic
scans faster and easier to understand. Instead of looking up every trouble code
individually, users can quickly see which faults were detected and which ones
may need attention first.

The planned vehicle-history database will also track codes by vehicle. This will
help identify whether a fault is new, has appeared before, or returned after it
was cleared. The goal is to spend less time researching codes and more time
diagnosing the vehicle.

## How It Works

1. Run a vehicle scan using FORScan or another OBD-II diagnostic tool.
2. Click the **Analyze** button.
3. OBD-Insight captures or imports the scan data.
4. Fault codes are matched against diagnostic data and vehicle history.
5. Results are organized into clear priority categories.
6. Users immediately see which issues should be investigated first.

## Final Product Vision

<img width="1672" height="941" alt="OBD-Insight final product vision" src="https://github.com/user-attachments/assets/c4be30f8-bf5a-4c85-98fe-88f5e84e3914" />

## Current Version

- Paste copied FORScan Log-tab text from the clipboard
- Open a saved `.txt` or `.log` file
- Extract vehicle information and a masked VIN
- Detect modules and their full names
- Detect multiple DTCs and match them to the correct modules
- Show Critical, Warning, and Informational totals
- Handle extra spaces, tabs, blank lines, timestamps, and collapsed log text
- Save scans locally in a separate history folder for each vehicle

FORScan's `(WARN)` label is ignored when assigning severity. OBD-Insight uses
its own basic severity rules.

## Current App Screenshot

<img width="1918" height="1123" alt="image" src="https://github.com/user-attachments/assets/76b15fd8-fc30-4c54-ac09-7206c790d809" />

## Core Features

- One-click scan analysis
- Instant DTC recognition
- Color-coded severity indicators
- Plain-English fault explanations
- Vehicle-specific diagnostic insights
- Database-assisted code interpretation
- Scan history by vehicle
- Recurring code detection
- New vs. returning fault comparison
- Designed to work alongside FORScan and other OBD-II tools
- Fast and efficient diagnostic workflow

Some core features are still planned and will be added as development
continues. The **Current Version** section above shows what is available now.

## Run It

With the virtual environment active, open the Windows application:

```powershell
python src/app.py
```

In FORScan, copy the Log tab. In OBD-Insight, click **Paste from Clipboard**,
then click **Analyze Scan**. You can also choose **Open Log File** and select a
saved FORScan text file.

Successful scans are saved locally under:

```text
Documents\OBD-Insight Data\vehicles
```

The original terminal version remains available. Use the sample FORScan log:

```powershell
python src/main.py
```

Or pass your own FORScan Log text file:

```powershell
python src/main.py path/to/forscan_log.txt
```

## Priority System

### 🔴 Critical

Issues that may affect vehicle safety, drivability, braking, airbags, engine
performance, transmission behavior, or cause further damage.

### 🟡 Warning

Issues that should be diagnosed soon but may not require immediate action.

### ⚪ Informational

Stored, historical, intermittent, or low-priority codes that can be monitored
over time.

## Severity Rules

The current version uses simple starting rules:

- **Critical:** Engine misfire, ABS/brake, airbag/SRS, transmission, or severe
  powertrain-related issues
- **Warning:** Body, driver seat, comfort, sensor, or other non-critical module
  codes
- **Informational:** Stored, historical, intermittent, previously cleared, or
  not-present codes
