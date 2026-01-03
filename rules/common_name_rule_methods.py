"""
Static rule methods for Common name checklist.
Generated from Common_name.json.
Each method: rule_XXX(label_data=None) with a comment of the original rule text.
Dummy implementations (pass).
"""

RULE_NUMBER_TO_FUNC = {}
RULE_ID_TO_FUNC = {}


def _register(num: int, rule_id: str, fn):
    RULE_NUMBER_TO_FUNC[num] = fn
    RULE_ID_TO_FUNC[rule_id] = fn
    return fn


def get_rule_method_by_number(num: int):
    return RULE_NUMBER_TO_FUNC.get(num)


def get_rule_method_by_id(rule_id: str):
    return RULE_ID_TO_FUNC.get(rule_id)


# Rule 1
@_register(1, "sha1:4e1b93a10d39", None)
def rule_001(label_data=None):
    # is a common name present?
    content_links = [
        "https://inspection.canada.ca/en/food-labels/labelling/industry/common-name"
    ]
    pass


# Rule 2
@_register(2, "sha1:c20cfb1e7fdf", None)
def rule_002(label_data=None):
    # if not, is the product exempt from common name ?
    content_links = [
        "https://inspection.canada.ca/en/food-labels/labelling/industry/common-name#a1_2"
    ]
    pass


# Rule 3
@_register(3, "sha1:83c8e4a7093c", None)
def rule_003(label_data=None):
    # is the common name on the principal display panel (PDP)?
    content_links = [
        "https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s14c3"
    ]
    pass


# Rule 4
@_register(4, "sha1:858b303922e8", None)
def rule_004(label_data=None):
    # is the common name in letters of 1.6 mm or greater?
    content_links = [
        "https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s15c3"
    ]
    pass


# Rule 5
@_register(5, "sha1:f00c531f323c", None)
def rule_005(label_data=None):
    # or, if the area of the principal display surface (PDS) is 10 cm 2 (1.55 inches 2 ) or less, is the common name shown in characters with a minimum type height of 0.8 mm (1/32 inch)?
    content_links = [
        "https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s15c3"
    ]
    pass


# Rule 6
@_register(6, "sha1:c6287136bf6e", None)
def rule_006(label_data=None):
    # is it an appropriate common name?
    content_links = [
        "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference",
        "https://inspection.canada.ca/en/food-labels/labelling/industry/true-nature"
    ]
    pass


# Rule 7
@_register(7, "sha1:066ba186767c", None)
def rule_007(label_data=None):
    # as printed in bold face type, but not in italics, in the FDR or in the Canadian Standards of Identity documents incorporated by reference (IbR) in the SFCR
    content_links = [
        "https://inspection.canada.ca/en/about-cfia/acts-and-regulations/list-acts-and-regulations/documents-incorporated-reference"
    ]
    pass


# Rule 8
@_register(8, "sha1:15e066fd11d3", None)
def rule_008(label_data=None):
    # as prescribed by any other regulation
    content_links = []
    pass


# Rule 9
@_register(9, "sha1:b7d3432f46d3", None)
def rule_009(label_data=None):
    # the name by which the food is generally known or a name that is not generic and that describes the food, if the name is not so printed or prescribed, or
    content_links = []
    pass


# Rule 10
@_register(10, "sha1:5a34dc2408ac", None)
def rule_010(label_data=None):
    # if the food is likely to be mistaken for another food, the common name must include words that describe the food's true nature with respect to its condition
    content_links = [
        "https://inspection.canada.ca/en/food-labels/labelling/industry/true-nature"
    ]
    pass
