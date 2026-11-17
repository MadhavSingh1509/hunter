"""
Script to generate config/company_registry.json (167 companies)
and config/campus_recruiter_registry.json (57 campus recruiters)
following HUNTER 4.0 specifications.
"""

import json
import os

COMPANY_SECTIONS = {
    "A": {
        "title": "A. Global Big Tech and Product Companies",
        "category": "Global Big Tech",
        "companies": [
            ("microsoft", "Microsoft", "https://careers.microsoft.com", "custom", "microsoft"),
            ("amazon", "Amazon", "https://www.amazon.jobs", "amazon_api", "amazon"),
            ("aws", "Amazon Web Services", "https://www.amazon.jobs/en/teams/amazon-web-services", "amazon_api", "aws"),
            ("google", "Google", "https://careers.google.com", "custom", "google"),
            ("adobe", "Adobe", "https://careers.adobe.com", "workday", "adobe"),
            ("apple", "Apple", "https://jobs.apple.com", "custom", "apple"),
            ("nvidia", "NVIDIA", "https://www.nvidia.com/en-us/about-nvidia/careers/", "workday", "nvidia"),
            ("uber", "Uber", "https://www.uber.com/careers", "custom", "uber"),
            ("walmart_global_tech", "Walmart Global Tech", "https://careers.walmart.com", "workday", "walmart"),
            ("salesforce", "Salesforce", "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site", "salesforce_workday", "salesforce"),
            ("servicenow", "ServiceNow", "https://careers.servicenow.com", "smartrecruiters", "servicenow"),
            ("oracle", "Oracle", "https://careers.oracle.com", "custom", "oracle"),
            ("sap_labs", "SAP Labs", "https://jobs.sap.com", "custom", "sap"),
            ("vmware_broadcom", "VMware / Broadcom", "https://careers.broadcom.com", "workday", "broadcom"),
            ("cisco", "Cisco", "https://jobs.cisco.com", "custom", "cisco"),
            ("juniper_networks", "Juniper Networks", "https://www.juniper.net/us/en/careers.html", "custom", "juniper"),
            ("arista_networks", "Arista Networks", "https://www.arista.com/en/careers", "greenhouse", "aristanetworks"),
            ("nutanix", "Nutanix", "https://www.nutanix.com/company/careers", "greenhouse", "nutanix"),
            ("dell_technologies", "Dell Technologies", "https://jobs.dell.com", "custom", "dell"),
            ("qualcomm", "Qualcomm", "https://qualcomm.wd5.myworkdayjobs.com/External", "workday", "qualcomm"),
            ("intuit", "Intuit", "https://jobs.intuit.com", "custom", "intuit"),
            ("atlassian", "Atlassian", "https://www.atlassian.com/company/careers", "lever", "atlassian"),
            ("akamai", "Akamai", "https://www.akamai.com/careers", "custom", "akamai"),
            ("rubrik", "Rubrik", "https://www.rubrik.com/company/careers", "greenhouse", "rubrik"),
            ("splunk", "Splunk", "https://www.splunk.com/en_us/careers.html", "lever", "splunk"),
            ("palo_alto_networks", "Palo Alto Networks", "https://jobs.paloaltonetworks.com", "smartrecruiters", "paloaltonetworks"),
            ("crowdstrike", "CrowdStrike", "https://crowdstrike.wd5.myworkdayjobs.com/crowdstrike_careers", "workday", "crowdstrike"),
            ("netapp", "NetApp", "https://netapp.wd1.myworkdayjobs.com/NetApp_Careers", "workday", "netapp"),
            ("commvault", "Commvault", "https://careers.commvault.com", "greenhouse", "commvault"),
            ("ibm", "IBM", "https://www.ibm.com/careers", "custom", "ibm"),
            ("databricks", "Databricks", "https://www.databricks.com/company/careers", "greenhouse", "databricks"),
            ("bloomberg", "Bloomberg", "https://bloomberg.wd1.myworkdayjobs.com/Bloomberg_Careers", "custom", "bloomberg"),
            ("nokia", "Nokia", "https://www.nokia.com/about-us/careers/", "custom", "nokia"),
            ("ericsson", "Ericsson", "https://jobs.ericsson.com", "custom", "ericsson"),
        ]
    },
    "B": {
        "title": "B. Banking, Finance and Financial Technology",
        "category": "Banking, Finance and FinTech",
        "companies": [
            ("goldman_sachs", "Goldman Sachs", "https://www.goldmansachs.com/careers", "custom", "goldmansachs"),
            ("jpmorgan_chase", "JPMorgan Chase", "https://careers.jpmorgan.com", "custom", "jpmorgan"),
            ("morgan_stanley", "Morgan Stanley", "https://www.morganstanley.com/about-us/careers", "custom", "morganstanley"),
            ("citi", "Citi", "https://jobs.citi.com", "custom", "citi"),
            ("deutsche_bank", "Deutsche Bank", "https://careers.db.com", "custom", "deutschebank"),
            ("barclays", "Barclays", "https://search.jobs.barclays", "barclays_talentbrew", "barclays"),
            ("wells_fargo", "Wells Fargo", "https://www.wellsfargo.com/about/careers/", "custom", "wellsfargo"),
            ("nomura", "Nomura", "https://www.nomuraholdings.com/careers/", "custom", "nomura"),
            ("hsbc", "HSBC", "https://www.hsbc.com/careers", "custom", "hsbc"),
            ("american_express", "American Express", "https://aexp.eightfold.ai/careers", "custom", "americanexpress"),
            ("visa", "Visa", "https://smartrecruiters.com/Visa", "smartrecruiters", "visa"),
            ("mastercard", "Mastercard", "https://mastercard.wd1.myworkdayjobs.com/CorporateCareers", "workday", "mastercard"),
            ("fiserv", "Fiserv", "https://www.careers.fiserv.com", "workday", "fiserv"),
            ("fis", "FIS", "https://careers.fisglobal.com", "workday", "fisglobal"),
            ("paypal", "PayPal", "https://paypal.wd1.myworkdayjobs.com/jobs", "workday", "paypal"),
            ("stripe", "Stripe", "https://stripe.com/jobs", "greenhouse", "stripe"),
            ("arcesium", "Arcesium", "https://www.arcesium.com/careers.html", "lever", "arcesium"),
            ("de_shaw", "DE Shaw", "https://www.deshawindia.com/careers", "custom", "deshaw"),
            ("tower_research", "Tower Research Capital", "https://www.tower-research.com/careers", "greenhouse", "towerresearchcapital"),
            ("graviton_research", "Graviton Research Capital", "https://gravitonresearch.com/careers", "custom", "graviton"),
            ("squarepoint_capital", "Squarepoint Capital", "https://www.squarepoint-capital.com/careers", "greenhouse", "squarepointcapital"),
            ("quadeye", "Quadeye", "https://quadeye.com/careers/", "custom", "quadeye"),
            ("future_first", "Future First", "https://www.futurefirst.com/careers", "custom", "futurefirst"),
        ]
    },
    "C": {
        "title": "C. Indian Product Companies and Unicorns",
        "category": "Indian Product & Unicorns",
        "companies": [
            ("flipkart", "Flipkart", "https://www.flipkartcareers.com", "custom", "flipkart"),
            ("zomato", "Zomato", "https://www.zomato.com/careers", "lever", "zomato"),
            ("swiggy", "Swiggy", "https://careers.swiggy.com", "greenhouse", "swiggy"),
            ("razorpay", "Razorpay", "https://razorpay.com/jobs/", "lever", "razorpay"),
            ("cred", "CRED", "https://cred.club/careers", "greenhouse", "cred"),
            ("phonepe", "PhonePe", "https://www.phonepe.com/careers/", "custom", "phonepe"),
            ("freshworks", "Freshworks", "https://www.freshworks.com/company/careers/", "greenhouse", "freshworks"),
            ("postman", "Postman", "https://www.postman.com/company/careers/", "greenhouse", "postman"),
            ("browserstack", "BrowserStack", "https://www.browserstack.com/careers", "greenhouse", "browserstack"),
            ("zoho", "Zoho", "https://www.zoho.com/careers/", "custom", "zoho"),
            ("groww", "Groww", "https://groww.in/careers", "greenhouse", "groww"),
            ("meesho", "Meesho", "https://www.meesho.io/jobs", "greenhouse", "meesho"),
            ("zerodha", "Zerodha", "https://zerodha.com/careers", "custom", "zerodha"),
            ("paytm", "Paytm", "https://jobs.lever.co/paytm", "lever", "paytm"),
            ("policybazaar", "PolicyBazaar", "https://www.policybazaar.com/careers/", "custom", "policybazaar"),
            ("slice", "Slice", "https://www.sliceit.com/careers", "greenhouse", "slice"),
            ("jupiter", "Jupiter", "https://jupiter.money/careers/", "lever", "jupiter"),
            ("fi_money", "Fi Money", "https://fi.money/careers", "lever", "fi-money"),
            ("myntra", "Myntra", "https://careers.myntra.com", "custom", "myntra"),
            ("media_net", "Media.net", "https://careers.media.net", "custom", "medianet"),
            ("dream11", "Dream11", "https://about.dream11.in/careers", "greenhouse", "dream11"),
            ("sharechat", "ShareChat", "https://sharechat.com/careers", "greenhouse", "sharechat"),
            ("dailyhunt", "Dailyhunt", "https://www.dailyhunt.in/careers", "lever", "dailyhunt"),
            ("inmobi", "InMobi", "https://www.inmobi.com/company/careers/", "smartrecruiters", "inmobi"),
            ("upstox", "Upstox", "https://upstox.com/careers/", "lever", "upstox"),
            ("navi", "Navi", "https://navi.com/careers", "lever", "navi"),
            ("kreditbee", "KreditBee", "https://www.kreditbee.in/careers", "custom", "kreditbee"),
            ("games24x7", "Games24x7", "https://www.games24x7.com/careers/", "lever", "games24x7"),
            ("cars24", "Cars24", "https://www.cars24.com/careers/", "lever", "cars24"),
            ("lenskart", "Lenskart", "https://lenskart.kekahire.com", "custom", "lenskart"),
            ("urban_company", "Urban Company", "https://www.urbancompany.com/careers", "lever", "urbancompany"),
            ("tata_1mg", "Tata 1mg", "https://www.1mg.com/jobs", "custom", "1mg"),
            ("rebel_foods", "Rebel Foods", "https://rebelfoods.com/careers", "custom", "rebelfoods"),
            ("cardekho", "CarDekho", "https://careers.cardekho.com", "custom", "cardekho"),
            ("physicswallah", "PhysicsWallah", "https://www.pw.live/careers", "custom", "physicswallah"),
            ("zepto", "Zepto", "https://www.zeptonow.com/careers", "lever", "zeptonow"),
            ("porter", "Porter", "https://porter.in/careers", "lever", "porter"),
            ("shiprocket", "Shiprocket", "https://www.shiprocket.in/careers/", "custom", "shiprocket"),
            ("ather_energy", "Ather Energy", "https://www.atherenergy.com/careers", "lever", "atherenergy"),
            ("ola_electric", "Ola Electric", "https://olaelectric.com/careers", "custom", "olaelectric"),
            ("ofbusiness", "OfBusiness", "https://www.ofbusiness.com/careers", "custom", "ofbusiness"),
            ("zetwerk", "Zetwerk", "https://www.zetwerk.com/careers/", "custom", "zetwerk"),
            ("apna", "Apna", "https://apna.co/careers", "lever", "apna"),
            ("rapido", "Rapido", "https://www.rapido.bike/Careers", "lever", "rapido"),
            ("unacademy", "Unacademy", "https://unacademy.com/careers", "lever", "unacademy"),
        ]
    },
    "D": {
        "title": "D. Enterprise SaaS, Developer Tools and B2B Technology",
        "category": "Enterprise SaaS & DevTools",
        "companies": [
            ("icertis", "Icertis", "https://www.icertis.com/company/careers/", "greenhouse", "icertis"),
            ("innovaccer", "Innovaccer", "https://innovaccer.com/careers", "greenhouse", "innovaccer"),
            ("chargebee", "Chargebee", "https://www.chargebee.com/company/careers/", "lever", "chargebee"),
            ("darwinbox", "Darwinbox", "https://darwinbox.com/careers.html", "custom", "darwinbox"),
            ("highradius", "HighRadius", "https://www.highradius.com/careers/", "custom", "highradius"),
            ("hasura", "Hasura", "https://hasura.io/careers/", "greenhouse", "hasura"),
            ("juspay", "Juspay", "https://juspay.in/careers", "custom", "juspay"),
            ("zeta", "Zeta", "https://www.zeta.tech/careers", "lever", "zeta"),
            ("gupshup", "Gupshup", "https://www.gupshup.io/careers", "custom", "gupshup"),
            ("druva", "Druva", "https://www.druva.com/about/careers/", "lever", "druva"),
            ("whatfix", "Whatfix", "https://whatfix.com/careers/", "greenhouse", "whatfix"),
            ("keka", "Keka", "https://www.keka.com/careers", "custom", "keka"),
            ("clevertap", "CleverTap", "https://clevertap.com/careers/", "greenhouse", "clevertap"),
            ("moengage", "MoEngage", "https://www.moengage.com/careers/", "lever", "moengage"),
            ("perfios", "Perfios", "https://www.perfios.com/careers", "custom", "perfios"),
            ("fynd", "Fynd", "https://jobs.lever.co/fynd", "lever", "fynd"),
            ("invideo", "InVideo", "https://invideo.io/careers", "greenhouse", "invideo"),
            ("harness", "Harness", "https://harness.io/careers", "greenhouse", "harness"),
            ("composio", "Composio", "https://composio.dev/careers", "greenhouse", "composio"),
            ("truefoundry", "TrueFoundry", "https://www.truefoundry.com/careers", "greenhouse", "truefoundry"),
            ("nanonets", "Nanonets", "https://nanonets.com/careers", "greenhouse", "nanonets"),
            ("observe_ai", "Observe.AI", "https://www.observe.ai/careers", "lever", "observeai"),
            ("uniphore", "Uniphore", "https://www.uniphore.com/careers/", "greenhouse", "uniphore"),
            ("yellow_ai", "Yellow.ai", "https://yellow.ai/careers/", "greenhouse", "yellowai"),
            ("haptik", "Haptik", "https://www.haptik.ai/careers/", "custom", "haptik"),
            ("mad_street_den", "Mad Street Den", "https://www.madstreetden.com/careers/", "custom", "madstreetden"),
        ]
    },
    "E": {
        "title": "E. AI, GenAI and Deep-Tech Startups",
        "category": "AI, GenAI and Deep-Tech",
        "companies": [
            ("sarvam_ai", "Sarvam AI", "https://www.sarvam.ai/careers", "ashby", "sarvam-ai"),
            ("krutrim", "Krutrim", "https://www.olakrutrim.com/careers", "custom", "krutrim"),
            ("neysa", "Neysa", "https://neysa.ai/careers", "custom", "neysa"),
            ("qpiai", "QpiAI", "https://qpiai.tech/careers", "custom", "qpiai"),
            ("emergent", "Emergent", "https://www.emergent.sh", "custom", "emergent"),
            ("gnani_ai", "Gnani.ai", "https://www.gnani.ai/careers/", "custom", "gnaniai"),
            ("qure_ai", "Qure.ai", "https://qure.ai/careers.html", "lever", "qureai"),
            ("niramai", "Niramai", "https://www.niramai.com/careers/", "custom", "niramai"),
            ("cropin", "Cropin", "https://www.cropin.com/careers", "lever", "cropin"),
            ("arya_ai", "Arya.ai", "https://arya.ai/careers", "custom", "aryaai"),
            ("e2e_networks", "E2E Networks", "https://www.e2enetworks.com/careers", "custom", "e2enetworks"),
            ("pixxel", "Pixxel", "https://www.pixxel.space/careers", "lever", "pixxel"),
            ("skyroot_aerospace", "Skyroot Aerospace", "https://skyroot.in/careers", "custom", "skyroot"),
            ("agnikul_cosmos", "Agnikul Cosmos", "https://agnikul.in/#/career", "custom", "agnikul"),
            ("ideaforge", "ideaForge", "https://ideaforge.co.in/careers", "custom", "ideaforge"),
            ("fractal_analytics", "Fractal Analytics", "https://fractal.ai/careers/", "greenhouse", "fractalanalytics"),
        ]
    },
    "F": {
        "title": "F. Semiconductor, Hardware and Engineering Technology",
        "category": "Semiconductor & Hardware",
        "companies": [
            ("synopsys", "Synopsys", "https://www.synopsys.com/careers.html", "custom", "synopsys"),
            ("cadence", "Cadence", "https://cadence.wd1.myworkdayjobs.com/External_Careers", "workday", "cadence"),
            ("texas_instruments", "Texas Instruments", "https://careers.ti.com", "custom", "ti"),
            ("micron", "Micron", "https://micron.wd1.myworkdayjobs.com/External", "workday", "micron"),
            ("amd", "AMD", "https://careers.amd.com", "custom", "amd"),
            ("intel", "Intel", "https://jobs.intel.com", "custom", "intel"),
            ("samsung_rd", "Samsung R&D", "https://research.samsung.com/sri-b", "custom", "samsung"),
        ]
    },
    "G": {
        "title": "G. Additional Campus and Technology Recruiters",
        "category": "Campus & Technology Recruiters",
        "companies": [
            ("accenture", "Accenture", "https://www.accenture.com/in-en/careers", "accenture_api", "accenture"),
            ("deloitte", "Deloitte", "https://jobsindia.deloitte.com", "custom", "deloitte"),
            ("ey", "EY", "https://careers.ey.com", "custom", "ey"),
            ("pwc", "PwC", "https://www.pwc.in/careers.html", "workday", "pwc"),
            ("publicis_sapient", "Publicis Sapient", "https://careers.publicissapient.com", "smartrecruiters", "publicissapient"),
            ("tcs_research", "TCS Research & Innovation", "https://www.tcs.com/careers", "custom", "tcs"),
            ("hcl_technologies", "HCL Technologies", "https://www.hcltech.com/careers", "custom", "hcl"),
            ("infosys", "Infosys", "https://www.infosys.com/careers/", "custom", "infosys"),
            ("wipro", "Wipro", "https://careers.wipro.com", "custom", "wipro"),
            ("icici_bank", "ICICI Bank", "https://www.icicicareers.com", "custom", "icicibank"),
            ("npci", "NPCI", "https://www.npci.org.in/who-we-are/careers", "custom", "npci"),
            ("payu", "PayU", "https://corporate.payu.com/careers/", "greenhouse", "payu"),
            ("sprinklr", "Sprinklr", "https://www.sprinklr.com/careers/", "greenhouse", "sprinklr"),
            ("thoughtspot", "ThoughtSpot", "https://www.thoughtspot.com/careers", "greenhouse", "thoughtspot"),
            ("cohesity", "Cohesity", "https://www.cohesity.com/company/careers/", "greenhouse", "cohesity"),
            ("devrev", "DevRev", "https://devrev.ai/careers", "lever", "devrev"),
        ]
    }
}

# Mandatory priority companies
MANDATORY_PRIORITY = {"accenture", "barclays", "salesforce", "amazon", "aws"}

def build_company_registry():
    registry = []
    total = 0
    seen_ids = set()

    for sec_key, sec_data in COMPANY_SECTIONS.items():
        for comp_id, name, careers_url, ats_type, ats_identifier in sec_data["companies"]:
            assert comp_id not in seen_ids, f"Duplicate company ID: {comp_id}"
            seen_ids.add(comp_id)
            total += 1

            priority = "mandatory_priority" if comp_id in MANDATORY_PRIORITY else ("high" if sec_key in ["A", "B"] else "normal")
            
            # Determine configured status
            is_configured = ats_type in [
                "amazon_api", "salesforce_workday", "barclays_talentbrew", "accenture_api",
                "greenhouse", "lever", "smartrecruiters", "ashby"
            ]

            entry = {
                "id": comp_id,
                "name": name,
                "section": sec_data["title"],
                "category": sec_data["category"],
                "careers_url": careers_url,
                "ats_type": ats_type,
                "ats_identifier": ats_identifier,
                "priority": priority,
                "status": "CONFIGURED" if is_configured else "NOT_CONFIGURED",
                "is_mandatory_priority": comp_id in MANDATORY_PRIORITY
            }
            registry.append(entry)

    print(f"Total companies in registry: {total}")
    assert total == 167, f"Expected 167 companies, got {total}"
    return registry


CAMPUS_RECRUITERS_PRIORITY_A = [
    ("amazon", "Amazon / AWS", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 12},
        {"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 25},
        {"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 28}
    ]),
    ("microsoft", "Microsoft", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 8},
        {"institute": "IIT Kharagpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 20}
    ]),
    ("google", "Google", "RECURRING", [
        {"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 15},
        {"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 18}
    ]),
    ("adobe", "Adobe", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 6},
        {"institute": "IIT Roorkee", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 10}
    ]),
    ("oracle", "Oracle", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 14},
        {"institute": "NIT Trichy", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 18}
    ]),
    ("qualcomm", "Qualcomm", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship (EE eligible)", "offers": 9},
        {"institute": "IIT Madras", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 16}
    ]),
    ("intel", "Intel", "RECURRING", [
        {"institute": "NIT Warangal", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 12},
        {"institute": "IIT Kanpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 15}
    ]),
    ("texas_instruments", "Texas Instruments", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship (EE eligible)", "offers": 5},
        {"institute": "IIT Kharagpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 14}
    ]),
    ("nvidia", "NVIDIA", "RECURRING", [
        {"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 12},
        {"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 14}
    ]),
    ("amd", "AMD", "OCCASIONAL", [
        {"institute": "IIT Hyderabad", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 8}
    ]),
    ("samsung_rd", "Samsung R&D", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 20},
        {"institute": "IIT Guwahati", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 22}
    ]),
    ("goldman_sachs", "Goldman Sachs", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 7},
        {"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 16}
    ]),
    ("jpmorgan_chase", "JPMorgan Chase", "RECURRING", [
        {"institute": "NIT Surathkal", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 18},
        {"institute": "IIT Roorkee", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 20}
    ]),
    ("morgan_stanley", "Morgan Stanley", "RECURRING", [
        {"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 11},
        {"institute": "NIT Trichy", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 14}
    ]),
    ("barclays", "Barclays", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 15},
        {"institute": "NIT Rourkela", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 18}
    ]),
    ("american_express", "American Express", "RECURRING", [
        {"institute": "IIT Roorkee", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 10},
        {"institute": "NIT Calicut", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 12}
    ]),
    ("accenture", "Accenture", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time (ASE / FSE)", "offers": 45},
        {"institute": "NIT Jamshedpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 60}
    ]),
    ("flipkart", "Flipkart", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 6},
        {"institute": "IIT Kharagpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 15}
    ]),
    ("meesho", "Meesho", "OCCASIONAL", [
        {"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 8},
        {"institute": "NIT Warangal", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 5}
    ]),
    ("salesforce", "Salesforce", "RECURRING", [
        {"institute": "NIT Surathkal", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 10},
        {"institute": "IIT Hyderabad", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 12}
    ]),
    ("de_shaw", "DE Shaw", "RECURRING", [
        {"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 6},
        {"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 7}
    ]),
    ("atlassian", "Atlassian", "RECURRING", [
        {"institute": "IIT Roorkee", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 8},
        {"institute": "NIT Trichy", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 10}
    ]),
    ("visa", "Visa", "RECURRING", [
        {"institute": "IIT Kanpur", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 12},
        {"institute": "NIT Warangal", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 14}
    ]),
    ("paypal", "PayPal", "RECURRING", [
        {"institute": "NIT Surathkal", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 9},
        {"institute": "IIT Madras", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 11}
    ]),
    ("cisco", "Cisco", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 16},
        {"institute": "NIT Calicut", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 20}
    ]),
    ("micron", "Micron", "OCCASIONAL", [
        {"institute": "NIT Warangal", "season": "2023-2024", "software_roles": True, "type": "Full-time (EE/ECE/CS)", "offers": 10}
    ]),
    ("oracle_financial_services", "Oracle Financial Services", "RECURRING", [
        {"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 12},
        {"institute": "NIT Durgapur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 15}
    ])
]

CAMPUS_RECRUITERS_PRIORITY_B = [
    ("databricks", "Databricks", "OCCASIONAL", [{"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 4}]),
    ("deutsche_bank", "Deutsche Bank", "RECURRING", [{"institute": "IIT Roorkee", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 14}]),
    ("wells_fargo", "Wells Fargo", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time & Internship", "offers": 10}]),
    ("icici_bank", "ICICI Bank", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 25}]),
    ("npci", "NPCI", "OCCASIONAL", [{"institute": "NIT Calicut", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 8}]),
    ("payu", "PayU", "OCCASIONAL", [{"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 6}]),
    ("sprinklr", "Sprinklr", "RECURRING", [{"institute": "IIT Kharagpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 10}]),
    ("thoughtspot", "ThoughtSpot", "OCCASIONAL", [{"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 5}]),
    ("cohesity", "Cohesity", "OCCASIONAL", [{"institute": "IIT Madras", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 5}]),
    ("devrev", "DevRev", "OCCASIONAL", [{"institute": "IIT Madras", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 4}]),
    ("shiprocket", "Shiprocket", "OCCASIONAL", [{"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 4}]),
    ("games24x7", "Games24x7", "OCCASIONAL", [{"institute": "IIT Roorkee", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 5}]),
    ("cars24", "Cars24", "OCCASIONAL", [{"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 5}]),
    ("porter", "Porter", "OCCASIONAL", [{"institute": "IIT Kanpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 4}]),
    ("myntra", "Myntra", "OCCASIONAL", [{"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 6}]),
    ("media_net", "Media.net", "RECURRING", [{"institute": "IIT Kharagpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 8}]),
    ("publicis_sapient", "Publicis Sapient", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 15}]),
    ("ibm", "IBM", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 18}]),
    ("deloitte", "Deloitte", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 30}]),
    ("ey", "EY", "RECURRING", [{"institute": "NIT Durgapur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 20}]),
    ("pwc", "PwC", "RECURRING", [{"institute": "NIT Jamshedpur", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 22}]),
    ("future_first", "Future First", "OCCASIONAL", [{"institute": "IIT Roorkee", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 6}]),
    ("arcesium", "Arcesium", "RECURRING", [{"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 8}]),
    ("graviton_research", "Graviton Research Capital", "RECURRING", [{"institute": "IIT Bombay", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 6}]),
    ("squarepoint_capital", "Squarepoint Capital", "OCCASIONAL", [{"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 4}]),
    ("quadeye", "Quadeye", "RECURRING", [{"institute": "IIT Delhi", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 7}]),
    ("tcs_research", "TCS Research & Innovation", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 25}]),
    ("hcl_technologies", "HCL Technologies", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 20}]),
    ("infosys", "Infosys", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 35}]),
    ("wipro", "Wipro", "RECURRING", [{"institute": "NIT Patna", "season": "2023-2024", "software_roles": True, "type": "Full-time", "offers": 28}])
]

def build_campus_recruiter_registry():
    watchlist = []
    assert len(CAMPUS_RECRUITERS_PRIORITY_A) == 27, f"Priority A count: {len(CAMPUS_RECRUITERS_PRIORITY_A)}"
    assert len(CAMPUS_RECRUITERS_PRIORITY_B) == 30, f"Priority B count: {len(CAMPUS_RECRUITERS_PRIORITY_B)}"

    for comp_id, name, recurrence, evidence in CAMPUS_RECRUITERS_PRIORITY_A:
        watchlist.append({
            "company_id": comp_id,
            "company_name": name,
            "priority_tier": "Priority A",
            "recurrence": recurrence,
            "evidence": evidence
        })

    for comp_id, name, recurrence, evidence in CAMPUS_RECRUITERS_PRIORITY_B:
        watchlist.append({
            "company_id": comp_id,
            "company_name": name,
            "priority_tier": "Priority B",
            "recurrence": recurrence,
            "evidence": evidence
        })

    total = len(watchlist)
    print(f"Total campus recruiters: {total}")
    assert total == 57, f"Expected 57 campus recruiters, got {total}"
    return watchlist

if __name__ == "__main__":
    os.makedirs("config", exist_ok=True)

    companies = build_company_registry()
    with open(os.path.join("config", "company_registry.json"), "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2)
    print("Saved config/company_registry.json")

    campus = build_campus_recruiter_registry()
    with open(os.path.join("config", "campus_recruiter_registry.json"), "w", encoding="utf-8") as f:
        json.dump(campus, f, indent=2)
    print("Saved config/campus_recruiter_registry.json")
