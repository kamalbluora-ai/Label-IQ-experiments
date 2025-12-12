import hashlib, json, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

URL = "https://inspection.canada.ca/en/food-labels/labelling/industry/requirements-checklist"

def norm_text(s):
    return " ".join(s.split()).strip()

def sha1_id(text, path):
    h = hashlib.sha1()
    h.update((norm_text(text) + "|" + "|".join(path)).encode("utf-8"))
    return "sha1:" + h.hexdigest()[:12]

def extract_links(el, base):
    links = []
    for a in el.find_all("a"):
        txt = norm_text(a.get_text(" "))
        href = a.get("href", "").strip()
        if href:
            links.append({"text": txt, "href": urljoin(base, href)})
    return links

def collect_li_rules(ul, path, base):
    rules = []
    for li in ul.find_all("li", recursive=False):
        # Handle nested lists (main bullet + indented sub-bullets)
        text_nodes = []
        for child in li.contents:
            if isinstance(child, NavigableString):
                text_nodes.append(str(child))
            elif isinstance(child, Tag) and child.name != "ul":
                text_nodes.append(child.get_text(" "))
        main_text = norm_text(" ".join(text_nodes))
        if main_text:
            rules.append({
                "id": sha1_id(main_text, path),
                "text": main_text,
                "citations": extract_links(li, base),
                "path": path
            })
        # Sub-list under this bullet → additional rules at same subsection level
        sub_ul = li.find("ul", recursive=False)
        if sub_ul:
            rules.extend(collect_li_rules(sub_ul, path, base))
    return rules

def parse_rules():
    html = requests.get(URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    # 1) Date modified
    date_modified = None
    for node in soup.find_all(text=lambda t: isinstance(t, NavigableString) and "Date modified:" in t):
        # next sibling or parent contains the date text
        parent = node.parent
        # try same line
        tail = norm_text(parent.get_text(" "))
        if "Date modified:" in tail:
            date_modified = norm_text(tail.split("Date modified:")[-1]).strip(": ").strip()
            if date_modified:
                break

    # 2) Find “Labelling requirements” anchor (h2) and then iterate h3/h4 underneath
    labelling_h2 = None
    for h2 in soup.find_all(["h2","h3"]):
        if norm_text(h2.get_text()) == "Labelling requirements":
            labelling_h2 = h2
            break
    if not labelling_h2:
        raise RuntimeError("Couldn't find 'Labelling requirements' section")

    # Build a flat list of nodes until we leave the content area
    sections = []
    cur = labelling_h2
    while cur:
        cur = cur.find_next_sibling()
        if not cur: break
        if cur.name == "h3":
            sections.append(cur)
        # Stop before footer or unrelated headings if needed
        if cur.name == "h2" and norm_text(cur.get_text()).startswith("Canadian Food Inspection Agency"):
            break

    output = {
        "source_url": URL,
        "date_modified": date_modified,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sections": []
    }

    for h3 in sections:
        section_title = norm_text(h3.get_text(" "))
        section = {"title": section_title, "rules": [], "subsections": [], "path": ["Labelling requirements", section_title]}
        # Gather siblings until next h3 or end
        sib = h3
        # First collect top-level bullets before any h4
        while True:
            sib = sib.find_next_sibling()
            if not sib or sib.name == "h3":
                break
            if sib.name == "ul":
                section["rules"].extend(collect_li_rules(sib, section["path"], URL))
            if sib.name == "h4":
                # Start a subsection; gather bullets until the next h4/h3
                sub_title = norm_text(sib.get_text(" "))
                sub = {"title": sub_title, "rules": [], "path": section["path"] + [sub_title]}
                sub_sib = sib
                while True:
                    sub_sib = sub_sib.find_next_sibling()
                    if not sub_sib or sub_sib.name in ("h4","h3"):
                        # push subsection and either continue (next h4) or outer loop (next h3)
                        section["subsections"].append(sub)
                        if not sub_sib or sub_sib.name == "h3":
                            sib = sub_sib  # so outer while will exit if h3
                            break
                        # else we encountered next h4: set sib to that h4 -1 so outer loop sees it
                        sib = sub_sib
                        # start next subsection
                        break
                    if sub_sib.name == "ul":
                        sub["rules"].extend(collect_li_rules(sub_sib, sub["path"], URL))
                if not sub_sib or (sub_sib and sub_sib.name == "h3"):
                    # We’ve already appended the sub; outer loop will handle h3
                    continue
        output["sections"].append(section)

    return output

if __name__ == "__main__":
    import os
    
    output_dir = "food_labelling_requirements_checklist"
    os.makedirs(output_dir, exist_ok=True)
    
    rules = parse_rules()
    output_file = os.path.join(output_dir, "cfia_rules.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    print("Wrote", output_file, "with", sum(len(s["rules"]) + sum(len(ss["rules"]) for ss in s["subsections"]) for s in rules["sections"]), "rules")
