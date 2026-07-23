"""Plain-English DTC explanations, layered on top of OBD-Insight's severity rules."""

CATEGORY_NAMES = {
    "P": "Powertrain",
    "B": "Body",
    "C": "Chassis",
    "U": "Network/Communication",
}

SPECIFIC_EXPLANATIONS = {
    "P0300": "Random/multiple cylinder misfire detected.",
    "P0301": "Cylinder 1 misfire detected.",
    "P0171": "Fuel system too lean (Bank 1).",
    "P0174": "Fuel system too lean (Bank 2).",
    "P0420": "Catalyst system efficiency below threshold (Bank 1).",
    "P0455": "Large EVAP system leak detected.",
    "P0128": "Coolant thermostat below regulating temperature.",
    "C1001": "Accessory Protocol Interface Module reported a network/communication fault.",
    "B115E": "Body Control Module fault, often tied to restraint or seatbelt circuitry.",
    "B10B9": "HVAC blend door or actuator fault.",
    "B2312": "Driver seat module fault, often a memory or position sensor issue.",
    "B2316": "Driver seat module fault, often a switch or motor circuit issue.",
}


def explain(code):
    """Return a short, plain-English description for a DTC."""
    if not code:
        return "No code provided."

    base = code.split(":")[0].split("-")[0].upper()
    if base in SPECIFIC_EXPLANATIONS:
        return SPECIFIC_EXPLANATIONS[base]

    category = CATEGORY_NAMES.get(base[0], "Unknown system") if base else "Unknown system"
    return f"{category} code. No specific write-up yet - check vehicle-specific service data for {base}."
