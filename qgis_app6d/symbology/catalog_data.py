# -*- coding: utf-8 -*-
"""
APP-6(D) symbol catalog data.

Provides a structured registry of known entities, organised by
**Symbol Set**, for use by the catalog browser GUI (Step 3) and the
rendering engine.

Each entry is a plain ``dict`` with the following keys:

* ``code``  – 6-digit entity code (positions 11-16 of the SIDC)
* ``name``  – human-readable name
* ``category`` – grouping label for the tree view
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ======================================================================
# Lightweight catalog entry
# ======================================================================

@dataclass
class CatalogEntry:
    """One entry in the symbol catalog."""

    symbol_set: str  # 2-digit code, e.g. "10"
    entity_code: str  # 6-digit code, e.g. "121100"
    name: str  # Human-readable name
    category: str = ""  # Grouping label
    description: str = ""  # Optional tooltip / description
    modifier_1: str = "00"  # 2-digit Modifier 1 code
    modifier_2: str = "00"  # 2-digit Modifier 2 code
    app6b_func: str = "------"  # 6-char APP-6B function ID (pos 5-10)

    def sidc_template(self, identity: str = "3", status: str = "0") -> str:
        """Build a full 20-char SIDC with defaults for version/context etc.

        The resulting SIDC uses:
        * Version 10 (APP-6D)
        * Context 0 (Reality)
        * Given *identity* (default 3 = Friend)
        * This entry's symbol set + entity
        * Given *status* (default 0 = Present)
        * No HQ/TF/Dummy, no amplifier
        * Entry-specific modifiers (M1, M2)

        Activities (symbol set "40") override the default identity to
        "1" (Unknown) because they use a neutral cloverleaf frame that
        does not carry an affiliation.
        """
        # Activities have no affiliation → always use Unknown frame
        if self.symbol_set == "40" and identity == "3":
            identity = "1"
        return (
            "10"  # version
            "0"  # context = Reality
            f"{identity}"  # standard identity
            f"{self.symbol_set}"  # symbol set
            f"{status}"  # status
            "0"  # HQ/TF/Dummy = none
            "00"  # amplifier = none
            f"{self.entity_code}"  # entity (6 digits)
            f"{self.modifier_1}"  # modifier 1
            f"{self.modifier_2}"  # modifier 2
        )


# ======================================================================
# Catalog registry
# ======================================================================

# -- Land Unit (10) ----------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 landunit.js mappings
# (src/numbersidc/sidc/landunit.js)

LAND_UNIT_ENTRIES: list[CatalogEntry] = [
    # -- Command & Control --
    CatalogEntry("10", "110000", "Command and Control", category="Command & Control", app6b_func="U-----"),
    CatalogEntry("10", "110500", "Liaison", category="Command & Control", app6b_func="UCR---"),
    CatalogEntry("10", "111000", "Signal", category="Command & Control", app6b_func="UCS---"),
    CatalogEntry("10", "111400", "Special Troops", category="Command & Control", app6b_func="U-----"),

    # -- Combat Arms --
    CatalogEntry("10", "121100", "Infantry", category="Combat Arms", app6b_func="UCI---"),
    CatalogEntry("10", "121100", "Light Infantry", category="Combat Arms", app6b_func="UCI---",
                 modifier_2="19"),  # M2=19 → Light
    CatalogEntry("10", "121104", "Motorized Infantry", category="Combat Arms", app6b_func="UCIM--"),
    CatalogEntry("10", "121102", "Mechanized Infantry", category="Combat Arms", app6b_func="UCIZ--"),
    CatalogEntry("10", "121100", "Mountain Infantry", category="Combat Arms", app6b_func="UCI---",
                 modifier_2="27"),  # M2=27 → Mountain
    CatalogEntry("10", "121100", "Airborne Infantry", category="Combat Arms", app6b_func="UCI---",
                 modifier_2="01"),  # M2=01 → Airborne
    CatalogEntry("10", "120100", "Air Assault", category="Combat Arms", app6b_func="UCAA--"),
    CatalogEntry("10", "120500", "Armor", category="Combat Arms", app6b_func="UCAC--"),
    CatalogEntry("10", "120500", "Light Armor", category="Combat Arms", app6b_func="UCAC--",
                 modifier_2="19"),  # M2=19 → Light
    CatalogEntry("10", "120501", "Armored Reconnaissance", category="Combat Arms", app6b_func="UCAR--"),
    CatalogEntry("10", "121000", "Combined Arms", category="Combat Arms", app6b_func="UCN---"),
    CatalogEntry("10", "121300", "Reconnaissance", category="Combat Arms", app6b_func="UCAR--"),
    CatalogEntry("10", "121700", "Special Forces", category="Combat Arms", app6b_func="UUSF--"),
    CatalogEntry("10", "121800", "Special Operations Forces", category="Combat Arms", app6b_func="UUSOF-"),

    # -- Fire Support --
    CatalogEntry("10", "130100", "Air Defence", category="Fire Support", app6b_func="UCAAD-"),
    CatalogEntry("10", "130300", "Field Artillery", category="Fire Support", app6b_func="UCFH--"),
    CatalogEntry("10", "130301", "SP Artillery", category="Fire Support", app6b_func="UCFHS-"),
    CatalogEntry("10", "130300", "Rocket Artillery", category="Fire Support", app6b_func="UCFH--",
                 modifier_1="41"),  # M1=41 → Multiple Rocket Launcher
    CatalogEntry("10", "130700", "Missile", category="Fire Support", app6b_func="UCFAM-"),
    CatalogEntry("10", "130800", "Mortar", category="Fire Support", app6b_func="UCFM--"),

    # -- UAS / Drone --
    # Entity 121900 = Unmanned Systems (GR.IC.UNMANNED SYSTEMS) in APP-6D Land Unit.
    # UCVU-- = Unmanned Systems; UCVUF- = Fixed Wing + UAV modifier.
    # M1 modifiers (APP-6D Land Unit sIdm1): 03=Attack, 47=UAV, 69=Utility.
    CatalogEntry("10", "121900", "Unmanned Aerial Vehicle (UAS)", category="UAS / Drone", app6b_func="UCVU--"),
    CatalogEntry("10", "121900", "UAS – Attack", category="UAS / Drone", app6b_func="UCVUF-",
                 modifier_1="03"),   # M1=03 → Attack
    CatalogEntry("10", "121900", "UAS – Reconnaissance", category="UAS / Drone", app6b_func="UCVUF-",
                 modifier_1="47"),   # M1=47 → Unmanned Aerial Vehicle (APP-6D)
    CatalogEntry("10", "121900", "UAS – Logistics / Cargo", category="UAS / Drone", app6b_func="UCVU--",
                 modifier_1="69"),   # M1=69 → Utility

    # -- Combat Support --
    CatalogEntry("10", "120600", "Aviation (Rotary Wing)", category="Combat Support", app6b_func="UCAAH-"),
    CatalogEntry("10", "120800", "Aviation (Fixed Wing)", category="Combat Support", app6b_func="UCAAF-"),
    CatalogEntry("10", "140700", "Engineer", category="Combat Support", app6b_func="UCE---"),
    CatalogEntry("10", "151000", "Military Intelligence", category="Combat Support", app6b_func="UCMI--"),
    CatalogEntry("10", "150500", "Electronic Warfare", category="Combat Support", app6b_func="UCJ---"),
    CatalogEntry("10", "140100", "CBRN", category="Combat Support", app6b_func="UCBC--"),
    CatalogEntry("10", "141200", "Military Police", category="Combat Support", app6b_func="UCMP--"),
    CatalogEntry("10", "142200", "Air and Missile Defense", category="Combat Support", app6b_func="UCAAA-"),

    # -- Combat Service Support --
    CatalogEntry("10", "161300", "Medical", category="Combat Service Support", app6b_func="UH----"),
    CatalogEntry("10", "163400", "Supply", category="Combat Service Support", app6b_func="USS---"),
    CatalogEntry("10", "163600", "Transportation", category="Combat Service Support", app6b_func="USST--"),
    CatalogEntry("10", "161100", "Maintenance", category="Combat Service Support", app6b_func="USM---"),
    CatalogEntry("10", "160000", "Sustainment", category="Combat Service Support", app6b_func="USS---"),
]

# -- Land Equipment (15) -----------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 landequipment.js mappings

LAND_EQUIPMENT_ENTRIES: list[CatalogEntry] = [
    # -- Weapons --
    CatalogEntry("15", "110000", "Weapon", category="Weapons"),
    CatalogEntry("15", "110900", "Howitzer", category="Weapons"),
    CatalogEntry("15", "111000", "Missile Launcher", category="Weapons"),
    CatalogEntry("15", "111400", "Mortar", category="Weapons"),
    CatalogEntry("15", "111600", "Multiple Rocket Launcher", category="Weapons"),

    # -- Armored Vehicles --
    CatalogEntry("15", "120200", "Tank", category="Armored Vehicles"),
    CatalogEntry("15", "120103", "APC", category="Armored Vehicles"),
    CatalogEntry("15", "120101", "Armored Fighting Vehicle", category="Armored Vehicles"),
    CatalogEntry("15", "120105", "Main Battle Tank", category="Armored Vehicles"),

    # -- Engineering --
    CatalogEntry("15", "130100", "Bridge", category="Engineering"),
    CatalogEntry("15", "130800", "Earthmover", category="Engineering"),
    CatalogEntry("15", "130900", "Mine Clearing", category="Engineering"),

    # -- Utility Vehicles --
    CatalogEntry("15", "140100", "Utility Vehicle", category="Utility Vehicles"),
    CatalogEntry("15", "140600", "Semi-Trailer Truck", category="Utility Vehicles"),

    # -- Mines --
    CatalogEntry("15", "210100", "Land Mine", category="Mines"),
    CatalogEntry("15", "210400", "IED", category="Mines"),

    # -- Sensors --
    CatalogEntry("15", "220300", "Radar", category="Sensors"),

    # -- Aviation --
    CatalogEntry("15", "250000", "Helicopter", category="Aviation"),
]

# -- Air (01) -----------------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 air.js

AIR_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("01", "110000", "Military Air Track", category="Military"),
    CatalogEntry("01", "110100", "Fixed Wing", category="Military – Fixed Wing"),
    CatalogEntry("01", "110101", "Medical Evacuation (FW)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110102", "Attack/Strike", category="Military – Fixed Wing"),
    CatalogEntry("01", "110103", "Bomber", category="Military – Fixed Wing"),
    CatalogEntry("01", "110104", "Fighter", category="Military – Fixed Wing"),
    CatalogEntry("01", "110105", "Fighter/Bomber", category="Military – Fixed Wing"),
    CatalogEntry("01", "110107", "Cargo (FW)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110108", "Jammer / ECM", category="Military – Fixed Wing"),
    CatalogEntry("01", "110109", "Tanker", category="Military – Fixed Wing"),
    CatalogEntry("01", "110110", "Patrol", category="Military – Fixed Wing"),
    CatalogEntry("01", "110111", "Reconnaissance (FW)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110112", "Trainer (FW)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110113", "Utility (FW)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110114", "VSTOL", category="Military – Fixed Wing"),
    CatalogEntry("01", "110115", "Airborne Command Post", category="Military – Fixed Wing"),
    CatalogEntry("01", "110116", "Airborne Early Warning", category="Military – Fixed Wing"),
    CatalogEntry("01", "110117", "Antisurface Warfare", category="Military – Fixed Wing"),
    CatalogEntry("01", "110118", "Antisubmarine Warfare (FW)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110119", "Communications", category="Military – Fixed Wing"),
    CatalogEntry("01", "110120", "Combat Search and Rescue", category="Military – Fixed Wing"),
    CatalogEntry("01", "110121", "Electronic Support", category="Military – Fixed Wing"),
    CatalogEntry("01", "110122", "Government", category="Military – Fixed Wing"),
    CatalogEntry("01", "110123", "Mine Countermeasures (FW)", category="Military – Fixed Wing"),
    CatalogEntry("01", "110124", "Personnel Recovery", category="Military – Fixed Wing"),
    CatalogEntry("01", "110125", "Search and Rescue", category="Military – Fixed Wing"),
    CatalogEntry("01", "110126", "Special Operations Forces", category="Military – Fixed Wing"),
    CatalogEntry("01", "110127", "Ultra Light", category="Military – Fixed Wing"),
    CatalogEntry("01", "110128", "Photographic Reconnaissance", category="Military – Fixed Wing"),
    CatalogEntry("01", "110129", "VIP", category="Military – Fixed Wing"),
    CatalogEntry("01", "110130", "SEAD", category="Military – Fixed Wing"),
    CatalogEntry("01", "110131", "Passenger", category="Military – Fixed Wing"),
    CatalogEntry("01", "110132", "Escort", category="Military – Fixed Wing"),
    CatalogEntry("01", "110133", "Electronic Attack", category="Military – Fixed Wing"),
    CatalogEntry("01", "110200", "Rotary Wing", category="Military – Rotary Wing"),
    CatalogEntry("01", "110201", "Medical Evacuation (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110202", "Attack (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110203", "Cargo (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110204", "Utility (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110205", "Antisubmarine Warfare (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110206", "C2 (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110207", "Mine Countermeasures (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110208", "Search and Rescue (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110209", "Reconnaissance (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110210", "Special Operations Forces (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110211", "VIP (RW)", category="Military – Rotary Wing"),
    CatalogEntry("01", "110300", "Unmanned Aerial Vehicle", category="Military – UAV"),
    CatalogEntry("01", "110301", "UAV – Fixed Wing", category="Military – UAV"),
    CatalogEntry("01", "110302", "UAV – Rotary Wing", category="Military – UAV"),
    CatalogEntry("01", "110303", "UAV – Attack", category="Military – UAV"),
    CatalogEntry("01", "110304", "UAV – Cargo", category="Military – UAV"),
    CatalogEntry("01", "110305", "UAV – Reconnaissance", category="Military – UAV"),
    CatalogEntry("01", "110400", "Vertical-Takeoff UAV", category="Military – UAV"),
    CatalogEntry("01", "110500", "Military Balloon", category="Military – LTA"),
    CatalogEntry("01", "110600", "Military Airship", category="Military – LTA"),
    CatalogEntry("01", "110700", "Tethered Lighter Than Air", category="Military – LTA"),

    # -- Civilian --
    CatalogEntry("01", "120000", "Civilian Air Track", category="Civilian"),
    CatalogEntry("01", "120100", "Civilian Fixed Wing", category="Civilian"),
    CatalogEntry("01", "120200", "Civilian Rotary Wing", category="Civilian"),
    CatalogEntry("01", "120300", "Civilian UAV", category="Civilian"),
    CatalogEntry("01", "120400", "Civilian Balloon", category="Civilian"),
    CatalogEntry("01", "120500", "Civilian Airship", category="Civilian"),
    CatalogEntry("01", "120600", "Civilian Tethered LTA", category="Civilian"),
    CatalogEntry("01", "120700", "Civilian Medical Evacuation", category="Civilian"),

    # -- Weapon --
    CatalogEntry("01", "130000", "Weapon", category="Weapon"),
    CatalogEntry("01", "130100", "Bomb", category="Weapon"),
    CatalogEntry("01", "130200", "Underwater Decoy", category="Weapon"),

    # -- Manual Track --
    CatalogEntry("01", "140000", "Manual Track", category="Manual Track"),
]


# -- Air Missile (02) ---------------------------------------------------

AIR_MISSILE_ENTRIES: list[CatalogEntry] = [
    CatalogEntry("02", "110000", "Air Missile", category="Missile"),
    # Operational variants via M1 modifiers
    CatalogEntry("02", "110000", "Air-to-Air Missile", category="Missile", modifier_1="01"),
    CatalogEntry("02", "110000", "Air-to-Surface Missile", category="Missile", modifier_1="02"),
    CatalogEntry("02", "110000", "Air-to-Subsurface Missile", category="Missile", modifier_1="03"),
    CatalogEntry("02", "110000", "Anti-Ballistic Missile", category="Missile", modifier_1="05"),
    CatalogEntry("02", "110000", "Ballistic Missile", category="Missile", modifier_1="06"),
    CatalogEntry("02", "110000", "Cruise Missile", category="Missile", modifier_1="07"),
    CatalogEntry("02", "110000", "Interceptor", category="Missile", modifier_1="08"),
]


# -- Space (05) ----------------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 space.js

SPACE_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("05", "110000", "Military Space Track", category="Military"),
    CatalogEntry("05", "110100", "Space Vehicle", category="Military"),
    CatalogEntry("05", "110200", "Re-entry Vehicle", category="Military"),
    CatalogEntry("05", "110300", "Planet Lander", category="Military"),
    CatalogEntry("05", "110400", "Orbiter Shuttle", category="Military"),
    CatalogEntry("05", "110500", "Capsule", category="Military"),
    CatalogEntry("05", "110600", "Satellite (General)", category="Military – Satellite"),
    CatalogEntry("05", "110700", "Satellite", category="Military – Satellite"),
    CatalogEntry("05", "110800", "Antisatellite Weapon", category="Military"),
    CatalogEntry("05", "110900", "Astronomical Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111000", "Biosatellite", category="Military – Satellite"),
    CatalogEntry("05", "111100", "Communications Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111200", "Earth Observation Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111300", "Miniaturized Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111400", "Navigational Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111500", "Reconnaissance Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111600", "Space Station", category="Military – Satellite"),
    CatalogEntry("05", "111700", "Tethered Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111800", "Weather Satellite", category="Military – Satellite"),
    CatalogEntry("05", "111900", "Space Launch Vehicle", category="Military"),

    # -- Civilian --
    CatalogEntry("05", "120000", "Civilian Space Track", category="Civilian"),
    CatalogEntry("05", "120100", "Civilian Orbiter Shuttle", category="Civilian"),
    CatalogEntry("05", "120200", "Civilian Capsule", category="Civilian"),
    CatalogEntry("05", "120300", "Civilian Satellite", category="Civilian – Satellite"),
    CatalogEntry("05", "120400", "Civilian Astronomical Sat.", category="Civilian – Satellite"),
    CatalogEntry("05", "120500", "Civilian Biosatellite", category="Civilian – Satellite"),
    CatalogEntry("05", "120600", "Civilian Comms Satellite", category="Civilian – Satellite"),
    CatalogEntry("05", "120700", "Civilian Earth Obs. Sat.", category="Civilian – Satellite"),
    CatalogEntry("05", "120800", "Civilian Miniaturized Sat.", category="Civilian – Satellite"),
    CatalogEntry("05", "120900", "Civilian Navigational Sat.", category="Civilian – Satellite"),
    CatalogEntry("05", "121000", "Civilian Space Station", category="Civilian – Satellite"),
    CatalogEntry("05", "121100", "Civilian Tethered Sat.", category="Civilian – Satellite"),
    CatalogEntry("05", "121200", "Civilian Weather Sat.", category="Civilian – Satellite"),
    CatalogEntry("05", "121300", "Civilian Planet Lander", category="Civilian"),
    CatalogEntry("05", "121400", "Civilian Space Vehicle", category="Civilian"),

    # -- Manual Track --
    CatalogEntry("05", "130000", "Manual Track (Space)", category="Manual Track"),
]


# -- Space Missile (06) --------------------------------------------------

SPACE_MISSILE_ENTRIES: list[CatalogEntry] = [
    CatalogEntry("06", "110000", "Space Missile", category="Missile"),
    CatalogEntry("06", "110000", "Ballistic Missile (Space)", category="Missile", modifier_1="01"),  # M1=01 → BALLISTIC
    CatalogEntry("06", "110000", "Space Launch Vehicle (Missile)", category="Missile", modifier_1="02"),  # M1=02 → SPACE
]


# -- Land Civilian (11) -------------------------------------------------

LAND_CIVILIAN_ENTRIES: list[CatalogEntry] = [
    CatalogEntry("11", "110000", "Civilian", category="Civilian"),
    CatalogEntry("11", "110100", "Environmental Protection", category="Civilian"),
    CatalogEntry("11", "110200", "Government Organization", category="Civilian"),
    CatalogEntry("11", "110300", "Individual", category="Civilian"),
    CatalogEntry("11", "110400", "Group/Team", category="Civilian"),
    CatalogEntry("11", "110500", "Killing Victim", category="Civilian"),
    CatalogEntry("11", "110600", "Kidnapping Victim", category="Civilian"),
    CatalogEntry("11", "110700", "Religious Leader", category="Civilian"),
    CatalogEntry("11", "110800", "Displaced Person", category="Civilian"),
    CatalogEntry("11", "110900", "Composite Loss", category="Civilian"),
]


# -- Land Installation (20) --------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 landinstallation.js

LAND_INSTALLATION_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("20", "110000", "Military Installation", category="Military"),
    CatalogEntry("20", "110100", "Aerial/Satellite", category="Military"),
    CatalogEntry("20", "110200", "Aircraft Production/Assembly", category="Military"),
    CatalogEntry("20", "110300", "Ammunition Cache", category="Military"),
    CatalogEntry("20", "110400", "Ammunition and Explosives", category="Military"),
    CatalogEntry("20", "110500", "C3I", category="Military"),
    CatalogEntry("20", "110600", "CBRN", category="Military"),
    CatalogEntry("20", "110700", "Construction/Engineering", category="Military"),
    CatalogEntry("20", "110800", "Corrosion", category="Military"),
    CatalogEntry("20", "110900", "Dam", category="Military"),
    CatalogEntry("20", "111000", "Disposal/Contamination", category="Military"),
    CatalogEntry("20", "111100", "Emergency Collection Point", category="Military"),
    CatalogEntry("20", "111200", "Equipment Manufacture", category="Military"),
    CatalogEntry("20", "111300", "Mine", category="Military"),
    CatalogEntry("20", "111400", "Missile/Rocket Launcher", category="Military"),
    CatalogEntry("20", "111500", "Nuclear Facility", category="Military"),
    CatalogEntry("20", "111501", "Nuclear Research Facility", category="Military"),
    CatalogEntry("20", "111502", "Nuclear Reactor", category="Military"),
    CatalogEntry("20", "111600", "Petroleum/Gas/Oil", category="Military"),
    CatalogEntry("20", "111700", "Radar", category="Military"),
    CatalogEntry("20", "111800", "Research", category="Military"),
    CatalogEntry("20", "111900", "Sea Vehicle Production", category="Military"),
    CatalogEntry("20", "112000", "Technical Maintenance", category="Military"),
    CatalogEntry("20", "112100", "Telecommunications", category="Military"),
    CatalogEntry("20", "112200", "Training", category="Military"),
    CatalogEntry("20", "112300", "Vehicle Production", category="Military"),
    CatalogEntry("20", "112400", "Warehouse/Storage", category="Military"),

    # -- Infrastructure – Agriculture --
    CatalogEntry("20", "120100", "Agriculture/Food Infrastructure", category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120101", "Agricultural Laboratory", category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120102", "Animal Feedlot", category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120103", "Commercial/Institutional Farm", category="Infrastructure – Agriculture"),
    CatalogEntry("20", "120104", "Grain Storage", category="Infrastructure – Agriculture"),

    # -- Infrastructure – Banking/Finance --
    CatalogEntry("20", "120200", "Banking, Finance & Insurance", category="Infrastructure – Banking"),
    CatalogEntry("20", "120201", "ATM", category="Infrastructure – Banking"),
    CatalogEntry("20", "120202", "Bank", category="Infrastructure – Banking"),
    CatalogEntry("20", "120203", "Financial Exchange", category="Infrastructure – Banking"),

    # -- Infrastructure – Commercial --
    CatalogEntry("20", "120300", "Commercial Infrastructure", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120301", "Chemical Plant", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120302", "Firearms Manufacturer", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120303", "Firearms Retailer", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120304", "Hazardous Material Production", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120305", "Industrial Site", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120306", "Landfill", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120307", "Pharmaceutical Manufacturer", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120308", "Contaminated Hazardous Waste Site", category="Infrastructure – Commercial"),
    CatalogEntry("20", "120309", "Toxic Release Inventory", category="Infrastructure – Commercial"),

    # -- Infrastructure – Education --
    CatalogEntry("20", "120400", "Educational Facilities", category="Infrastructure – Education"),
    CatalogEntry("20", "120401", "College/University", category="Infrastructure – Education"),
    CatalogEntry("20", "120402", "School", category="Infrastructure – Education"),

    # -- Infrastructure – Electric Power --
    CatalogEntry("20", "120500", "Electric Power", category="Infrastructure – Electric"),
    CatalogEntry("20", "120501", "Electric Power Generation Station", category="Infrastructure – Electric"),
    CatalogEntry("20", "120502", "Electric Power Substation", category="Infrastructure – Electric"),
    CatalogEntry("20", "120503", "Natural Gas Facility", category="Infrastructure – Electric"),
    CatalogEntry("20", "120504", "Propane Facility", category="Infrastructure – Electric"),

    # -- Infrastructure – Government --
    CatalogEntry("20", "120600", "Government Site", category="Infrastructure – Government"),
    CatalogEntry("20", "120601", "Courthouse", category="Infrastructure – Government"),
    CatalogEntry("20", "120602", "Embassy", category="Infrastructure – Government"),
    CatalogEntry("20", "120603", "Government Building", category="Infrastructure – Government"),
    CatalogEntry("20", "120604", "Prison/Jail", category="Infrastructure – Government"),

    # -- Infrastructure – Medical --
    CatalogEntry("20", "120700", "Medical Infrastructure", category="Infrastructure – Medical"),
    CatalogEntry("20", "120701", "Hospital", category="Infrastructure – Medical"),
    CatalogEntry("20", "120702", "Medical Treatment Facility", category="Infrastructure – Medical"),
    CatalogEntry("20", "120703", "Pharmacy", category="Infrastructure – Medical"),

    # -- Infrastructure – Military Base --
    CatalogEntry("20", "120800", "Military Infrastructure", category="Infrastructure – Military"),
    CatalogEntry("20", "120801", "Military Base", category="Infrastructure – Military"),
    CatalogEntry("20", "120802", "Airfield/Airport", category="Infrastructure – Military"),

    # -- Infrastructure – Postal --
    CatalogEntry("20", "120900", "Postal Service", category="Infrastructure – Postal"),
    CatalogEntry("20", "120901", "Post Office", category="Infrastructure – Postal"),

    # -- Infrastructure – Public Venues --
    CatalogEntry("20", "121000", "Public Venues", category="Infrastructure – Public"),
    CatalogEntry("20", "121001", "Enclosed Facility", category="Infrastructure – Public"),
    CatalogEntry("20", "121002", "Open Facility", category="Infrastructure – Public"),
    CatalogEntry("20", "121003", "Recreational Area", category="Infrastructure – Public"),
    CatalogEntry("20", "121004", "Religious Institution", category="Infrastructure – Public"),

    # -- Infrastructure – Special Needs --
    CatalogEntry("20", "121100", "Special Needs", category="Infrastructure – Special Needs"),
    CatalogEntry("20", "121101", "Adult Day Care", category="Infrastructure – Special Needs"),
    CatalogEntry("20", "121102", "Child Day Care", category="Infrastructure – Special Needs"),
    CatalogEntry("20", "121103", "Elder Care", category="Infrastructure – Special Needs"),

    # -- Infrastructure – Telecommunications --
    CatalogEntry("20", "121200", "Telecommunications", category="Infrastructure – Telecom"),
    CatalogEntry("20", "121201", "Broadcast Transmitter", category="Infrastructure – Telecom"),
    CatalogEntry("20", "121202", "Telecommunications Tower", category="Infrastructure – Telecom"),
    CatalogEntry("20", "121203", "Internet Service Provider", category="Infrastructure – Telecom"),

    # -- Infrastructure – Transportation --
    CatalogEntry("20", "121300", "Transportation Infrastructure", category="Infrastructure – Transport"),
    CatalogEntry("20", "121301", "Airport", category="Infrastructure – Transport"),
    CatalogEntry("20", "121302", "Air Traffic Control", category="Infrastructure – Transport"),
    CatalogEntry("20", "121303", "Bus Station", category="Infrastructure – Transport"),
    CatalogEntry("20", "121304", "Ferry Terminal", category="Infrastructure – Transport"),
    CatalogEntry("20", "121305", "Helicopter Landing Site", category="Infrastructure – Transport"),
    CatalogEntry("20", "121306", "Maintenance Facility", category="Infrastructure – Transport"),
    CatalogEntry("20", "121307", "Port/Harbor", category="Infrastructure – Transport"),
    CatalogEntry("20", "121308", "Railroad Station/Depot", category="Infrastructure – Transport"),
    CatalogEntry("20", "121309", "Rest Area", category="Infrastructure – Transport"),
    CatalogEntry("20", "121310", "Seaport", category="Infrastructure – Transport"),
    CatalogEntry("20", "121311", "Toll Facility", category="Infrastructure – Transport"),
    CatalogEntry("20", "121312", "Traffic Inspection Facility", category="Infrastructure – Transport"),
    CatalogEntry("20", "121313", "Tunnel", category="Infrastructure – Transport"),

    # -- Infrastructure – Water --
    CatalogEntry("20", "121400", "Water Supply", category="Infrastructure – Water"),
    CatalogEntry("20", "121401", "Controlled Water", category="Infrastructure – Water"),
    CatalogEntry("20", "121402", "Water Treatment", category="Infrastructure – Water"),
    CatalogEntry("20", "121403", "Well", category="Infrastructure – Water"),
]


# -- Sea Surface (30) ---------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 sea.js

SEA_SURFACE_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("30", "110000", "Military Sea Surface Track", category="Military"),

    # -- Combatant --
    CatalogEntry("30", "120000", "Combatant", category="Combatant"),
    CatalogEntry("30", "120100", "Carrier", category="Combatant"),
    CatalogEntry("30", "120200", "Surface Combatant, Line", category="Combatant – Line"),
    CatalogEntry("30", "120201", "Battleship", category="Combatant – Line"),
    CatalogEntry("30", "120202", "Cruiser", category="Combatant – Line"),
    CatalogEntry("30", "120203", "Destroyer", category="Combatant – Line"),
    CatalogEntry("30", "120204", "Frigate", category="Combatant – Line"),
    CatalogEntry("30", "120205", "Corvette", category="Combatant – Line"),
    CatalogEntry("30", "120206", "Littoral Combatant Ship", category="Combatant – Line"),
    CatalogEntry("30", "120300", "Amphibious Warfare Ship", category="Combatant – Amphibious"),
    CatalogEntry("30", "120301", "Amphibious Assault Ship, General", category="Combatant – Amphibious"),
    CatalogEntry("30", "120302", "Amphibious Assault Ship, Helicopter", category="Combatant – Amphibious"),
    CatalogEntry("30", "120303", "Amphibious Transport Dock", category="Combatant – Amphibious"),
    CatalogEntry("30", "120304", "Landing Ship", category="Combatant – Amphibious"),
    CatalogEntry("30", "120305", "Landing Craft", category="Combatant – Amphibious"),
    CatalogEntry("30", "120400", "Mine Warfare Vessel", category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120401", "Minelayer", category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120402", "Minesweeper", category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120403", "Minehunter", category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120404", "Mine Countermeasures (MCM)", category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120405", "MCM Support", category="Combatant – Mine Warfare"),
    CatalogEntry("30", "120500", "Patrol Boat", category="Combatant"),
    CatalogEntry("30", "120501", "Patrol Anti-Submarine", category="Combatant"),
    CatalogEntry("30", "120502", "Patrol Coastal", category="Combatant"),
    CatalogEntry("30", "120600", "Decoy", category="Combatant"),
    CatalogEntry("30", "120700", "Unmanned Surface Vehicle", category="Combatant"),
    CatalogEntry("30", "120800", "Military Speedboat", category="Combatant"),
    CatalogEntry("30", "120801", "Speedboat, Armed", category="Combatant"),
    CatalogEntry("30", "120900", "Military Jet Ski", category="Combatant"),
    CatalogEntry("30", "121000", "Navy Task Organization Unit", category="Combatant – Task Org"),
    CatalogEntry("30", "121001", "Task Force", category="Combatant – Task Org"),
    CatalogEntry("30", "121002", "Task Group", category="Combatant – Task Org"),
    CatalogEntry("30", "121003", "Task Unit", category="Combatant – Task Org"),
    CatalogEntry("30", "121004", "Task Element", category="Combatant – Task Org"),
    CatalogEntry("30", "121005", "Convoy", category="Combatant – Task Org"),
    CatalogEntry("30", "121100", "Radar (Sea Surface)", category="Combatant"),

    # -- Noncombatant --
    CatalogEntry("30", "130000", "Noncombatant", category="Noncombatant"),
    CatalogEntry("30", "130100", "Auxiliary Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130101", "Ammunition Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130102", "Combat Stores Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130103", "Fast Combat Support Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130104", "Hospital Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130105", "Intelligence Collector", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130106", "Oiler", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130107", "Repair Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130108", "Research Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130109", "Salvage Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130110", "Submarine Tender", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130111", "Survey Ship", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130112", "Tug", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130113", "Transport", category="Noncombatant – Auxiliary"),
    CatalogEntry("30", "130200", "Service Craft/Vessel", category="Noncombatant – Service"),
    CatalogEntry("30", "130201", "Barge", category="Noncombatant – Service"),
    CatalogEntry("30", "130202", "Diving Vessel", category="Noncombatant – Service"),
    CatalogEntry("30", "130203", "Dredge", category="Noncombatant – Service"),
    CatalogEntry("30", "130204", "Launch", category="Noncombatant – Service"),

    # -- Civilian --
    CatalogEntry("30", "140000", "Civilian Ship", category="Civilian"),
    CatalogEntry("30", "140100", "Merchant Ship", category="Civilian – Merchant"),
    CatalogEntry("30", "140101", "Cargo Vessel", category="Civilian – Merchant"),
    CatalogEntry("30", "140102", "Container Ship", category="Civilian – Merchant"),
    CatalogEntry("30", "140103", "Dredger (Civ.)", category="Civilian – Merchant"),
    CatalogEntry("30", "140104", "Ferry", category="Civilian – Merchant"),
    CatalogEntry("30", "140105", "Heavy Lift Ship", category="Civilian – Merchant"),
    CatalogEntry("30", "140106", "Hovercraft", category="Civilian – Merchant"),
    CatalogEntry("30", "140107", "Merchant Marine Oiler/Tanker", category="Civilian – Merchant"),
    CatalogEntry("30", "140108", "LNG Carrier", category="Civilian – Merchant"),
    CatalogEntry("30", "140109", "Oil Rig", category="Civilian – Merchant"),
    CatalogEntry("30", "140110", "Passenger Vessel", category="Civilian – Merchant"),
    CatalogEntry("30", "140111", "Roll-on/Roll-off", category="Civilian – Merchant"),
    CatalogEntry("30", "140112", "Tug (Civilian)", category="Civilian – Merchant"),
    CatalogEntry("30", "140113", "Yacht", category="Civilian – Merchant"),
    CatalogEntry("30", "140200", "Fishing Vessel", category="Civilian"),
    CatalogEntry("30", "140201", "Drift Netter", category="Civilian"),
    CatalogEntry("30", "140202", "Trawler", category="Civilian"),
    CatalogEntry("30", "140203", "Dory/Whaler", category="Civilian"),
    CatalogEntry("30", "140300", "Law Enforcement Vessel", category="Civilian"),
    CatalogEntry("30", "140400", "Sailing Vessel", category="Civilian – Leisure"),
    CatalogEntry("30", "140500", "Motorized Vessel (Leisure)", category="Civilian – Leisure"),
    CatalogEntry("30", "140600", "Jet Ski (Civilian)", category="Civilian – Leisure"),
    CatalogEntry("30", "140700", "Unmanned Surface Vehicle (Civ.)", category="Civilian"),

    # -- Own Ship / Fused / Manual --
    CatalogEntry("30", "150000", "Own Ship", category="Own Ship"),
    CatalogEntry("30", "160000", "Fused Track (Sea Surface)", category="Fused Track"),
    CatalogEntry("30", "170000", "Manual Track (Sea Surface)", category="Manual Track"),
]


# -- Sea Subsurface (35) ------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 subsurface.js

SEA_SUBSURFACE_ENTRIES: list[CatalogEntry] = [
    # -- Military --
    CatalogEntry("35", "110000", "Military Subsurface Track", category="Military"),
    CatalogEntry("35", "110100", "Submarine", category="Military – Submarine"),
    CatalogEntry("35", "110101", "Submarine, Surfaced", category="Military – Submarine"),
    CatalogEntry("35", "110102", "Submarine, Snorkeling", category="Military – Submarine"),
    CatalogEntry("35", "110103", "Submarine, Bottomed", category="Military – Submarine"),
    CatalogEntry("35", "110200", "Other Submersible", category="Military"),
    CatalogEntry("35", "110300", "Non-Submarine", category="Military"),
    CatalogEntry("35", "110400", "Autonomous Underwater Vehicle", category="Military"),
    CatalogEntry("35", "110500", "Military Diver", category="Military"),

    # -- Civilian --
    CatalogEntry("35", "120000", "Civilian Subsurface Track", category="Civilian"),
    CatalogEntry("35", "120100", "Civilian Submersible", category="Civilian"),
    CatalogEntry("35", "120200", "Civilian AUV/UUV", category="Civilian"),
    CatalogEntry("35", "120300", "Civilian Diver", category="Civilian"),

    # -- Underwater Weapon --
    CatalogEntry("35", "130000", "Underwater Weapon", category="Weapon"),
    CatalogEntry("35", "130100", "Torpedo", category="Weapon"),
    CatalogEntry("35", "130200", "Improvised Explosive Device", category="Weapon"),
    CatalogEntry("35", "130300", "Underwater Decoy", category="Weapon"),

    # -- Echo / Fused / Manual --
    CatalogEntry("35", "140000", "Echo Tracker Classifier", category="Echo"),
    CatalogEntry("35", "150000", "Fused Track (Subsurface)", category="Fused Track"),
    CatalogEntry("35", "160000", "Manual Track (Subsurface)", category="Manual Track"),

    # -- Seabed Installation --
    CatalogEntry("35", "200000", "Seabed Installation, Military", category="Seabed Installation"),
    CatalogEntry("35", "210000", "Seabed Installation, Non-Military", category="Seabed Installation"),
]


# -- Mine Warfare (36) --------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 minewarfare.js

MINE_WARFARE_ENTRIES: list[CatalogEntry] = [
    # -- Sea Mine (General) --
    CatalogEntry("36", "110000", "Sea Mine (General)", category="Sea Mine"),

    # -- Bottom Mine --
    CatalogEntry("36", "110100", "Sea Mine – Bottom", category="Sea Mine – Bottom"),
    CatalogEntry("36", "110101", "Bottom Mine – General", category="Sea Mine – Bottom"),

    # -- Moored Mine --
    CatalogEntry("36", "110200", "Sea Mine – Moored", category="Sea Mine – Moored"),
    CatalogEntry("36", "110201", "Moored Mine – General", category="Sea Mine – Moored"),

    # -- Floating Mine --
    CatalogEntry("36", "110300", "Sea Mine – Floating", category="Sea Mine – Floating"),
    CatalogEntry("36", "110301", "Floating Mine – General", category="Sea Mine – Floating"),

    # -- Rising Mine --
    CatalogEntry("36", "110400", "Sea Mine – Rising", category="Sea Mine – Rising"),

    # -- Other Mine Types --
    CatalogEntry("36", "110500", "Sea Mine – Other Position", category="Sea Mine"),
    CatalogEntry("36", "110600", "Kingfisher", category="Sea Mine"),
    CatalogEntry("36", "110700", "Small Object – Mine", category="Sea Mine"),

    # -- Exercise Mine --
    CatalogEntry("36", "110800", "Exercise Mine – General", category="Exercise Mine"),
    CatalogEntry("36", "110801", "Exercise Mine – Bottom", category="Exercise Mine"),
    CatalogEntry("36", "110802", "Exercise Mine – Moored", category="Exercise Mine"),
    CatalogEntry("36", "110803", "Exercise Mine – Floating", category="Exercise Mine"),
    CatalogEntry("36", "110804", "Exercise Mine – Rising", category="Exercise Mine"),

    # -- Neutralized Mine --
    CatalogEntry("36", "110900", "Neutralized Mine – General", category="Neutralized Mine"),
    CatalogEntry("36", "110901", "Neutralized Mine – Bottom", category="Neutralized Mine"),
    CatalogEntry("36", "110902", "Neutralized Mine – Moored", category="Neutralized Mine"),
    CatalogEntry("36", "110903", "Neutralized Mine – Floating", category="Neutralized Mine"),
    CatalogEntry("36", "110904", "Neutralized Mine – Rising", category="Neutralized Mine"),

    # -- Mine-Like Contact (MILCO) --
    CatalogEntry("36", "111000", "MILCO – General", category="MILCO"),
    CatalogEntry("36", "111100", "MILCO – Low Confidence", category="MILCO"),
    CatalogEntry("36", "111200", "MILCO – High Confidence", category="MILCO"),

    # -- Mine-Like Echo (MILEC) --
    CatalogEntry("36", "111300", "MILEC – General", category="MILEC"),
    CatalogEntry("36", "111301", "MILEC – Low Confidence", category="MILEC"),
    CatalogEntry("36", "111302", "MILEC – High Confidence", category="MILEC"),

    # -- Decoy/Obstructor --
    CatalogEntry("36", "111400", "Decoy – General", category="Decoy"),
    CatalogEntry("36", "111500", "Mine Anchor", category="Mine Anchor"),

    # -- Unexploded Ordnance --
    CatalogEntry("36", "120000", "Unexploded Explosive Ordnance", category="UXO"),
]


# -- Activities (40) ----------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 activites.js

ACTIVITY_ENTRIES: list[CatalogEntry] = [
    # -- Incident --
    CatalogEntry("40", "110000", "Incident", category="Incident"),

    # -- Criminal Activity --
    CatalogEntry("40", "110100", "Criminal Activity Incident", category="Incident – Criminal"),
    CatalogEntry("40", "110101", "Arrest", category="Incident – Criminal"),
    CatalogEntry("40", "110102", "Arson", category="Incident – Criminal"),
    CatalogEntry("40", "110103", "Attempted Criminal Activity", category="Incident – Criminal"),
    CatalogEntry("40", "110104", "Drive-by Shooting", category="Incident – Criminal"),
    CatalogEntry("40", "110105", "Drug Related", category="Incident – Criminal"),
    CatalogEntry("40", "110106", "Extortion", category="Incident – Criminal"),
    CatalogEntry("40", "110107", "Graffiti", category="Incident – Criminal"),
    CatalogEntry("40", "110108", "Killing", category="Incident – Criminal"),
    CatalogEntry("40", "110109", "Kidnapping", category="Incident – Criminal"),
    CatalogEntry("40", "110110", "Piracy", category="Incident – Criminal"),
    CatalogEntry("40", "110111", "Poisoning", category="Incident – Criminal"),
    CatalogEntry("40", "110112", "Robbery", category="Incident – Criminal"),
    CatalogEntry("40", "110113", "Theft", category="Incident – Criminal"),

    # -- Bombing --
    CatalogEntry("40", "110200", "Bomb/Bombing", category="Incident – Bombing"),
    CatalogEntry("40", "110201", "Bomb Threat", category="Incident – Bombing"),
    CatalogEntry("40", "110202", "Booby Trap", category="Incident – Bombing"),
    CatalogEntry("40", "110203", "VBIED (Detonated)", category="Incident – Bombing"),
    CatalogEntry("40", "110204", "IED – Detonated", category="Incident – Bombing"),
    CatalogEntry("40", "110205", "IED – Premature Detonation", category="Incident – Bombing"),
    CatalogEntry("40", "110206", "IED – Suspected", category="Incident – Bombing"),
    CatalogEntry("40", "110207", "VBIED (Suspected)", category="Incident – Bombing"),

    # -- Shooting / Sniping --
    CatalogEntry("40", "110300", "IED (General)", category="Incident – IED"),
    CatalogEntry("40", "110400", "Shooting", category="Incident"),
    CatalogEntry("40", "110500", "Sniping", category="Incident"),

    # -- Drug-related / Explosion --
    CatalogEntry("40", "110600", "Explosion/Bang", category="Incident"),

    # -- Civil Disturbance --
    CatalogEntry("40", "120000", "Civil Disturbance", category="Civil Disturbance"),
    CatalogEntry("40", "120100", "Demonstration", category="Civil Disturbance"),
    CatalogEntry("40", "120200", "Riot", category="Civil Disturbance"),

    # -- Operation --
    CatalogEntry("40", "130000", "Operation", category="Operation"),
    CatalogEntry("40", "130100", "Patrol (Activity)", category="Operation"),
    CatalogEntry("40", "130200", "Reconnaissance (Activity)", category="Operation"),
    CatalogEntry("40", "130300", "Surveillance", category="Operation"),
    CatalogEntry("40", "130400", "Engagement", category="Operation"),
    CatalogEntry("40", "130500", "Interdiction", category="Operation"),
    CatalogEntry("40", "130600", "Ambush", category="Operation"),
    CatalogEntry("40", "130700", "Cordon and Search", category="Operation"),
    CatalogEntry("40", "130800", "Security", category="Operation"),

    # -- Fire Event --
    CatalogEntry("40", "140000", "Fire Event", category="Fire Event"),
    CatalogEntry("40", "140100", "Wildfire", category="Fire Event"),
    CatalogEntry("40", "140200", "Fire – Origin", category="Fire Event"),
    CatalogEntry("40", "140300", "Hot Spot", category="Fire Event"),
    CatalogEntry("40", "140400", "Non-Residential Fire", category="Fire Event"),
    CatalogEntry("40", "140500", "Residential Fire", category="Fire Event"),
    CatalogEntry("40", "140600", "School Fire", category="Fire Event"),
    CatalogEntry("40", "140700", "Smoke", category="Fire Event"),
    CatalogEntry("40", "140800", "Special Needs Fire", category="Fire Event"),

    # -- HAZMAT --
    CatalogEntry("40", "150000", "HAZMAT", category="HAZMAT"),
    CatalogEntry("40", "150100", "Chemical Agent", category="HAZMAT"),
    CatalogEntry("40", "150200", "Combustible", category="HAZMAT"),
    CatalogEntry("40", "150300", "Corrosive Material", category="HAZMAT"),
    CatalogEntry("40", "150400", "Explosive", category="HAZMAT"),
    CatalogEntry("40", "150500", "Flammable Gas", category="HAZMAT"),
    CatalogEntry("40", "150600", "Flammable Liquid", category="HAZMAT"),
    CatalogEntry("40", "150700", "Flammable Solid", category="HAZMAT"),
    CatalogEntry("40", "150800", "Non-Flammable Gas", category="HAZMAT"),
    CatalogEntry("40", "150900", "Organic Peroxide", category="HAZMAT"),
    CatalogEntry("40", "151000", "Oxidizer", category="HAZMAT"),
    CatalogEntry("40", "151100", "Radioactive Material", category="HAZMAT"),
    CatalogEntry("40", "151200", "Spontaneously Combustible", category="HAZMAT"),
    CatalogEntry("40", "151300", "Toxic/Infectious", category="HAZMAT"),
    CatalogEntry("40", "151400", "Unexploded Ordnance (Act.)", category="HAZMAT"),
    CatalogEntry("40", "151500", "Water w/ Calcium Hypochlorite", category="HAZMAT"),

    # -- Transportation Incident --
    CatalogEntry("40", "160000", "Transportation Incident", category="Transportation"),
    CatalogEntry("40", "160100", "Air Incident", category="Transportation"),
    CatalogEntry("40", "160200", "Marine Incident", category="Transportation"),
    CatalogEntry("40", "160300", "Rail Incident", category="Transportation"),
    CatalogEntry("40", "160400", "Vehicle Incident", category="Transportation"),

    # -- Natural Event --
    CatalogEntry("40", "170000", "Natural Event", category="Natural Event"),
    CatalogEntry("40", "170100", "Avalanche", category="Natural Event"),
    CatalogEntry("40", "170200", "Earthquake", category="Natural Event"),
    CatalogEntry("40", "170300", "Flood", category="Natural Event"),
    CatalogEntry("40", "170400", "Infestation", category="Natural Event"),
    CatalogEntry("40", "170500", "Landslide/Mudslide", category="Natural Event"),
    CatalogEntry("40", "170600", "Tornado", category="Natural Event"),
    CatalogEntry("40", "170700", "Tsunami", category="Natural Event"),
    CatalogEntry("40", "170800", "Volcanic Eruption", category="Natural Event"),

    # -- Emergency –-
    CatalogEntry("40", "180000", "Emergency Medical Operations", category="Emergency"),
    CatalogEntry("40", "180100", "Emergency Collection Point (Act.)", category="Emergency"),
    CatalogEntry("40", "180200", "Emergency Incident CP", category="Emergency"),
    CatalogEntry("40", "180300", "Emergency Operations Center", category="Emergency"),
    CatalogEntry("40", "180400", "Emergency Shelter", category="Emergency"),
    CatalogEntry("40", "180500", "Emergency Staging Area", category="Emergency"),
    CatalogEntry("40", "180600", "Emergency Food Distribution", category="Emergency"),
    CatalogEntry("40", "180700", "Emergency Water Distribution", category="Emergency"),
]


# -- SIGINT – shared entity codes for sets 50-54 ------------------------
# Entity codes aligned with milsymbol v3.0.4 signalsintelligence.js

def _sigint_entries(symbol_set: str) -> list[CatalogEntry]:
    """Build SIGINT catalog entries for a given symbol set (50–54)."""
    return [
        CatalogEntry(symbol_set, "110000", "Signal Intercept", category="SIGINT"),
        CatalogEntry(symbol_set, "110100", "Communications", category="SIGINT"),
        CatalogEntry(symbol_set, "110200", "Jammer / ECM", category="SIGINT"),
        CatalogEntry(symbol_set, "110300", "Radar", category="SIGINT"),
    ]


SIGINT_SPACE_ENTRIES: list[CatalogEntry] = _sigint_entries("50")
SIGINT_AIR_ENTRIES: list[CatalogEntry] = _sigint_entries("51")
SIGINT_LAND_ENTRIES: list[CatalogEntry] = _sigint_entries("52")
SIGINT_SURFACE_ENTRIES: list[CatalogEntry] = _sigint_entries("53")
SIGINT_SUBSURFACE_ENTRIES: list[CatalogEntry] = _sigint_entries("54")


# -- Cyberspace (60) ----------------------------------------------------
# Entity codes aligned with milsymbol v3.0.4 cyberspace.js

CYBERSPACE_ENTRIES: list[CatalogEntry] = [
    # -- Botnet --
    CatalogEntry("60", "110000", "Botnet", category="Botnet"),
    CatalogEntry("60", "110100", "C2 / Command and Control", category="Botnet"),
    CatalogEntry("60", "110200", "Herder", category="Botnet"),
    CatalogEntry("60", "110300", "Callback Domain", category="Botnet"),
    CatalogEntry("60", "110400", "Zombie", category="Botnet"),

    # -- Infection --
    CatalogEntry("60", "120000", "Infection", category="Infection"),
    CatalogEntry("60", "120100", "Advanced Persistent Threat", category="Infection"),
    CatalogEntry("60", "120200", "Non-Advanced Persistent Threat", category="Infection"),

    # -- Health & Status --
    CatalogEntry("60", "130000", "Health and Status", category="Health & Status"),
    CatalogEntry("60", "130100", "Normal", category="Health & Status"),
    CatalogEntry("60", "130200", "Network Outage", category="Health & Status"),
    CatalogEntry("60", "130300", "Known Intrusion", category="Health & Status"),
    CatalogEntry("60", "130400", "Known Compromised", category="Health & Status"),

    # -- Device Type --
    CatalogEntry("60", "140000", "Device Type", category="Device"),
    CatalogEntry("60", "140100", "Core Router", category="Device"),
    CatalogEntry("60", "140200", "Router", category="Device"),
    CatalogEntry("60", "140300", "Cross Domain Solution", category="Device"),
    CatalogEntry("60", "140400", "Mail Server", category="Device"),
    CatalogEntry("60", "140500", "Web Server", category="Device"),
    CatalogEntry("60", "140600", "Peer-to-Peer Node", category="Device"),
    CatalogEntry("60", "140700", "Firewall", category="Device"),
    CatalogEntry("60", "140800", "Switch", category="Device"),
    CatalogEntry("60", "140900", "Host", category="Device"),
    CatalogEntry("60", "141000", "Virtual Private Network", category="Device"),

    # -- Device Domain --
    CatalogEntry("60", "150000", "Device Domain", category="Device Domain"),
    CatalogEntry("60", "150100", "Department of Defense (DoD)", category="Device Domain"),
    CatalogEntry("60", "150200", "Government", category="Device Domain"),
    CatalogEntry("60", "150300", "Contractor", category="Device Domain"),
    CatalogEntry("60", "150400", "Supervisory Control/SCADA", category="Device Domain"),
    CatalogEntry("60", "150500", "Non-Government", category="Device Domain"),

    # -- Effect --
    CatalogEntry("60", "160000", "Effect", category="Effect"),
    CatalogEntry("60", "160100", "Achieve", category="Effect"),
    CatalogEntry("60", "160200", "Block", category="Effect"),
    CatalogEntry("60", "160300", "Degrade", category="Effect"),
    CatalogEntry("60", "160400", "Deny", category="Effect"),
    CatalogEntry("60", "160500", "Destroy", category="Effect"),
    CatalogEntry("60", "160600", "Disrupt", category="Effect"),
    CatalogEntry("60", "160700", "Locate", category="Effect"),
    CatalogEntry("60", "160800", "Manipulate", category="Effect"),
    CatalogEntry("60", "160900", "Neutralize", category="Effect"),

    # -- Large --
    CatalogEntry("60", "170000", "Large", category="Large"),
    CatalogEntry("60", "170100", "Server", category="Large"),
    CatalogEntry("60", "170200", "Desktop Workstation", category="Large"),

    # -- Network --
    CatalogEntry("60", "180000", "Network", category="Network"),

    # -- Small --
    CatalogEntry("60", "190000", "Small", category="Small"),
    CatalogEntry("60", "190100", "Handheld", category="Small"),
    CatalogEntry("60", "190200", "Laptop", category="Small"),
    CatalogEntry("60", "190300", "Cellular Phone", category="Small"),
    CatalogEntry("60", "190400", "Tablet", category="Small"),

    # -- Persona / Organization --
    CatalogEntry("60", "200000", "Persona Type", category="Persona"),
    CatalogEntry("60", "200100", "Online Persona", category="Persona"),
    CatalogEntry("60", "200200", "Organization", category="Persona"),
]


# ======================================================================
# Aggregate catalog
# ======================================================================

ALL_ENTRIES: list[CatalogEntry] = (
    AIR_ENTRIES
    + AIR_MISSILE_ENTRIES
    + SPACE_ENTRIES
    + SPACE_MISSILE_ENTRIES
    + LAND_UNIT_ENTRIES
    + LAND_CIVILIAN_ENTRIES
    + LAND_EQUIPMENT_ENTRIES
    + LAND_INSTALLATION_ENTRIES
    + SEA_SURFACE_ENTRIES
    + SEA_SUBSURFACE_ENTRIES
    + MINE_WARFARE_ENTRIES
    + ACTIVITY_ENTRIES
    + SIGINT_SPACE_ENTRIES
    + SIGINT_AIR_ENTRIES
    + SIGINT_LAND_ENTRIES
    + SIGINT_SURFACE_ENTRIES
    + SIGINT_SUBSURFACE_ENTRIES
    + CYBERSPACE_ENTRIES
)


# -- Symbol-Set human-readable names ------------------------------------

SYMBOL_SET_NAMES: dict[str, str] = {
    "01": "Air",
    "02": "Air Missile",
    "05": "Space",
    "06": "Space Missile",
    "10": "Land Unit",
    "11": "Land Civilian",
    "15": "Land Equipment",
    "20": "Land Installation",
    "25": "Control Measure",
    "30": "Sea Surface",
    "35": "Sea Subsurface",
    "36": "Mine Warfare",
    "40": "Activities",
    "45": "METOC – Atmospheric",
    "46": "METOC – Oceanographic",
    "47": "METOC – Space",
    "50": "SIGINT – Space",
    "51": "SIGINT – Air",
    "52": "SIGINT – Land",
    "53": "SIGINT – Surface",
    "54": "SIGINT – Subsurface",
    "60": "Cyberspace",
}


# -- Lookup helpers -----------------------------------------------------

_INDEX_BY_SET: dict[str, list[CatalogEntry]] | None = None


def entries_by_symbol_set(symbol_set: str) -> list[CatalogEntry]:
    """Return all catalog entries for a given symbol-set code."""
    global _INDEX_BY_SET
    if _INDEX_BY_SET is None:
        _INDEX_BY_SET = {}
        for e in ALL_ENTRIES:
            _INDEX_BY_SET.setdefault(e.symbol_set, []).append(e)
    return _INDEX_BY_SET.get(symbol_set, [])


def find_entry(symbol_set: str, entity_code: str) -> Optional[CatalogEntry]:
    """Find a catalog entry by symbol set and entity code."""
    for e in entries_by_symbol_set(symbol_set):
        if e.entity_code == entity_code:
            return e
    return None


def search_catalog(query: str) -> list[CatalogEntry]:
    """Full-text search across name and category.

    Returns entries whose name or category contains
    *query* (case-insensitive).
    """
    q = query.lower()
    return [
        e
        for e in ALL_ENTRIES
        if q in e.name.lower()
        or q in e.category.lower()
    ]
