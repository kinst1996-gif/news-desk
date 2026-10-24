"""Hashtags that fit each story, plus a check against what Google Trends says people search for right now.

tags_for(title, summary, topic, trends) -> (["#Tag", ...], ["trending term", ...])
google_trends(geos)                      -> [{"term", "traffic", "geo"}]
"""
import re, time
import news_bot as n

# Companies worth tagging by name (pattern, hashtag)
COMPANIES = [(r"\b%s\b" % re.escape(name), "#" + tag) for name, tag in [
    ("NVIDIA", "NVIDIA"), ("Siemens", "Siemens"), ("ABB", "ABB"), ("Emerson", "Emerson"), ("Rosemount", "Rosemount"),
    ("Yokogawa", "Yokogawa"), ("Honeywell", "Honeywell"), ("Rockwell", "RockwellAutomation"), ("Schneider Electric", "SchneiderElectric"),
    ("Endress+Hauser", "EndressHauser"), ("KROHNE", "KROHNE"), ("WIKA", "WIKA"), ("VEGA", "VEGA"), ("Fluke", "Fluke"), ("Omron", "Omron"),
    ("Mitsubishi Electric", "MitsubishiElectric"), ("Beckhoff", "Beckhoff"), ("AVEVA", "AVEVA"), ("AspenTech", "AspenTech"),
    ("OpenAI", "OpenAI"), ("Anthropic", "Anthropic"), ("Claude", "Claude"), ("ChatGPT", "ChatGPT"), ("Gemini", "Gemini"),
    ("Google", "Google"), ("Microsoft", "Microsoft"), ("Meta", "Meta"), ("Apple", "Apple"), ("Amazon", "Amazon"), ("AWS", "AWS"),
    ("Mistral", "MistralAI"), ("Hugging Face", "HuggingFace"), ("DeepSeek", "DeepSeek"), ("Intel", "Intel"), ("AMD", "AMD"),
    ("Samsung", "Samsung"), ("TSMC", "TSMC"), ("Tesla", "Tesla"), ("Boston Dynamics", "BostonDynamics"), ("Figure", "FigureAI"),
    ("Aramco", "Aramco"), ("ADNOC", "ADNOC"), ("Shell", "Shell"), ("ExxonMobil", "ExxonMobil"), ("Schlumberger|SLB", "SLB"),
]]

# Subject words (pattern, hashtag); order = priority
TOPICS = [(re.compile(p, re.I), t) for p, t in [
    (r"flow ?meter|flow measurement|coriolis|ultrasonic flow|magnetic flow", "#FlowMeasurement"),
    (r"pressure (transmitter|sensor|gauge|measurement)", "#PressureMeasurement"),
    (r"level (measurement|sensor|transmitter)|radar level", "#LevelMeasurement"),
    (r"temperature (sensor|measurement|transmitter)|thermocouple|\bRTD\b", "#TemperatureMeasurement"),
    (r"gas (analy[sz]er|detection|density)|analy[sz]er", "#ProcessAnalytics"),
    (r"\bvalves?\b|actuator", "#Valves"),
    (r"\bpumps?\b", "#Pumps"),
    (r"calibrat", "#Calibration"),
    (r"\bsensors?\b", "#Sensors"),
    (r"\bPLC\b|programmable logic", "#PLC"),
    (r"\bSCADA\b", "#SCADA"),
    (r"\bDCS\b|distributed control", "#DCS"),
    (r"\bOPC ?UA\b", "#OPCUA"),
    (r"\bIIoT\b|industrial internet of things", "#IIoT"),
    (r"digital twin", "#DigitalTwin"),
    (r"\bOT\b|operational technology|industrial cyber|ICS security|ransomware", "#OTSecurity"),
    (r"cyber ?security|cyberattack|breach", "#Cybersecurity"),
    (r"predictive maintenance|condition monitoring", "#PredictiveMaintenance"),
    (r"\bhydrogen\b", "#Hydrogen"),
    (r"\bLNG\b|natural gas", "#LNG"),
    (r"oil (and|&) gas|offshore|upstream|refiner", "#OilAndGas"),
    (r"\bwater (treatment|utility|utilities)|wastewater", "#WaterTreatment"),
    (r"energy transition|renewable|solar|wind (farm|power)", "#EnergyTransition"),
    (r"semiconductor|\bchips?\b|wafer|substrate", "#Semiconductors"),
    (r"data ?cent(er|re)|AI infrastructure|AI factor", "#AIInfrastructure"),
    (r"\bGPUs?\b", "#GPU"),
    (r"humanoid", "#HumanoidRobots"),
    (r"\bcobots?\b|collaborative robot", "#Cobots"),
    (r"\bdrones?\b|\bUAV\b", "#Drones"),
    (r"autonomous (vehicle|driving|mobile robot)|\bAMR\b|self-driving", "#AutonomousSystems"),
    (r"\bagents?\b|agentic", "#AIAgents"),
    (r"\bLLMs?\b|large language model|language model", "#LLM"),
    (r"generative AI|\bGenAI\b", "#GenAI"),
    (r"open[- ]source|open[- ]weight", "#OpenSource"),
    (r"machine learning|deep learning", "#MachineLearning"),
    (r"computer vision|machine vision", "#MachineVision"),
    (r"edge (computing|AI)", "#EdgeComputing"),
    (r"\bmanufactur", "#Manufacturing"),
    (r"supply chain", "#SupplyChain"),
    (r"sustainab|decarboni|emission", "#Sustainability"),
    (r"process safety|functional safety|safety instrumented|hazardous area|explosion[- ]proof", "#ProcessSafety"),
    (r"\bUAE\b|Dubai|Abu Dhabi|Emirat", "#UAE"),
    (r"Saudi", "#SaudiArabia"),
    (r"\bIndia\b|Indian", "#India"),
]]

BASE = {"Instrumentation": ["#Instrumentation", "#ProcessAutomation"],
        "AI": ["#AI", "#ArtificialIntelligence"],
        "Robotics": ["#Robotics", "#Automation"],
        "UAE": ["#UAE", "#MiddleEast"],
        "UAE AI": ["#UAE", "#AI", "#UAEAI"]}

_trend_cache = {"at": 0, "data": []}


def google_trends(geos=("AE", "US", "IN")):
    """Daily trending searches from Google Trends RSS, cached for an hour."""
    if time.time() - _trend_cache["at"] < 3600:
        return _trend_cache["data"]
    out = []
    for geo in geos:
        try:
            _, body, _ = n.req(f"https://trends.google.com/trending/rss?geo={geo}", headers=n.UA, raw=True, timeout=20)
        except Exception as e:
            print("trends failed", geo, e)
            continue
        t = body.decode("utf-8", "replace")
        for item in re.findall(r"<item>(.*?)</item>", t, re.S):
            term = re.search(r"<title>([^<]+)</title>", item)
            traffic = re.search(r"<ht:approx_traffic>([^<]+)<", item)
            if term:
                out.append({"term": n.strip(term.group(1)), "traffic": traffic.group(1) if traffic else "", "geo": geo})
    _trend_cache.update(at=time.time(), data=out)
    return out


def camel(term):
    words = re.findall(r"[A-Za-z0-9]+", term)
    return "#" + "".join(w if w.isupper() else w.capitalize() for w in words) if words else ""


def tags_for(title, summary="", topic="AI", trends=None, limit=6):
    text = f"{title} {summary}"
    trending = []
    for tr in trends or []:
        term = tr["term"]
        if len(term) > 3 and re.fullmatch(r"[\x20-\x7e]+", term) and re.search(r"\b%s\b" % re.escape(term), text, re.I):
            trending.append(term)
    specific = []
    for pat, tag in COMPANIES:
        if re.search(pat, text):          # case-sensitive: "Meta" the company, not "metadata"
            specific.append(tag)
    for rx, tag in TOPICS:
        if rx.search(text):
            specific.append(tag)
    base = BASE.get(topic, BASE["AI"])
    tags = [camel(t) for t in trending[:2]] + specific[:4] + (base[:1] if len(specific) >= 3 else base)
    seen, final = set(), []
    for t in tags:
        if t and t.lower() not in seen:
            seen.add(t.lower()); final.append(t)
    return final[:limit], trending[:2]
