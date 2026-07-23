# OBD-Insight

OBD-Insight is a lightweight companion application for FORScan.

Vehicle scans often contain multiple fault codes spread across different modules. While FORScan provides detailed diagnostic data, identifying which issues need attention first can be time-consuming and overwhelming.

OBD-Insight is designed to solve that problem.

With a single click, scan results are analyzed and translated into clear, color-coded priorities, helping users quickly identify critical faults, warnings, and informational codes without manually researching every DTC.

The goal is simple:

**Spend less time searching codes and more time diagnosing vehicles.**

## Why?

Many technicians and vehicle owners do not memorize every fault code.

When a scan contains multiple DTCs, users often need to manually search each code, determine its severity, and decide which issues should be investigated first.

OBD-Insight streamlines that process by automatically:

* Identifying important faults
* Prioritizing issues by severity
* Providing plain-English explanations
* Highlighting what requires immediate attention
* Reducing diagnostic research time
* Tracking scan history over time
* Showing whether a code is new, repeated, or returning after being cleared
* Using stored vehicle data to recognize recurring problems across past scans

This history-based approach makes the app more useful than a one-time code lookup. Instead of only asking “what does this code mean?”, OBD-Insight can help answer:

* Has this code appeared before?
* Did it return after being cleared?
* Is this becoming a repeated issue?
* Which module keeps reporting problems?
* Is this likely a current issue or just an old stored code?

## How It Works

1. Run a vehicle scan using FORScan or another OBD-II diagnostic tool.
2. Click the Analyze button.
3. OBD-Insight captures or imports the scan data.
4. Fault codes are matched against diagnostic data and vehicle history.
5. Results are organized into clear priority categories.
6. Users immediately see which issues should be investigated first.

## Priority System

### 🔴 Critical

Issues that may affect vehicle safety, drivability, braking, airbags, engine performance, transmission behavior, or cause further damage.

### 🟡 Warning

Issues that should be diagnosed soon but may not require immediate action.

### ⚪ Informational

Stored, historical, intermittent, or low-priority codes that can be monitored over time.

## Core Features

* One-click scan analysis
* Instant DTC recognition
* Color-coded severity indicators
* Plain-English fault explanations
* Vehicle-specific diagnostic insights
* Database-assisted code interpretation
* Scan history by vehicle
* Recurring code detection
* New vs. returning fault comparison
* Designed to work alongside FORScan and other OBD-II tools
* Fast and efficient diagnostic workflow

## Purpose

OBD-Insight is not intended to replace professional diagnostic software.

Its purpose is to make diagnostic information easier to understand, reduce time spent researching fault codes, and help users focus on the issues that matter most.

## Prototype Preview


<img width="1672" height="941" alt="Prototype" src="https://github.com/user-attachments/assets/c4be30f8-bf5a-4c85-98fe-88f5e84e3914" />


This prototype shows OBD-Insight running alongside FORScan.

Raw scan results are automatically organized into color-coded priorities, helping users quickly identify important faults, review historical scan data, and access additional diagnostic insights without manually researching every code.

Each fault card can be expanded using **Add Details** to display additional diagnostic information, common causes, and vehicle-specific context. Users can also select **Ask AI** to ask follow-up questions about a specific fault using the current scan results and previously stored vehicle history as context.

## Current Prototype

* Reads FORScan Log tab text from a file
* Extracts basic vehicle information when available
* Detects `Found module:` lines
* Detects `DTCs in MODULE:` lines
* Extracts module names and DTC codes
* Classifies each DTC as Critical, Warning, or Informational
* Prints a clean terminal summary


## Run It

Use the sample FORScan log:

```bash
python src/main.py
```

Or pass your own FORScan Log text file:

```bash
python src/main.py path/to/forscan_log.txt
```

## Example Output

```text
Vehicle:
Lincoln MKX TiVCT 3.7L 2012 (2012 MY)
VIN: 2LM********18750

Modules Found:
8

Scan Summary:
3 DTCs found
0 Critical
3 Warning
0 Informational

Results:
WARNING       | BdyCM | Body Control Module  | B115E:55-0A
WARNING       | DSM   | Driver's Seat Module | B2312-60
WARNING       | DSM   | Driver's Seat Module | B2316-60
```

## Severity Rules

V1 uses simple rules:

* Critical: engine misfire, ABS/brake, airbag/SRS, transmission, or severe powertrain-related issues
* Warning: body, driver seat, comfort, sensor, or other non-critical module codes
* Informational: stored, historical, intermittent, previously cleared, or not-present codes

## Telegram Bot

`telegram_bot/` contains a Telegram front end that reuses this same
parser/severity engine so users can paste a FORScan log straight into a
chat and get instant triage, with a Stars-based premium tier for
cross-scan history (new/repeated/returning codes) and BotFather Affiliate
Program support for referral-driven distribution. See
[`telegram_bot/README.md`](telegram_bot/README.md) for setup and the
market research behind it.

## License

Proprietary - all rights reserved. See [`LICENSE`](LICENSE). This is not
open source software; no permission is granted to use, copy, or
distribute it without written consent from the copyright holder.
