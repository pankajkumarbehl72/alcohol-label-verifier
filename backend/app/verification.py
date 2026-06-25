import re
from typing import Optional, List
from rapidfuzz import fuzz

from app.models import ApplicationFields, ExtractedLabelFields, FieldCheck, CheckStatus


REQUIRED_GOVERNMENT_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or operate "
    "machinery, and may cause health problems."
)


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("“", '"').replace("”", '"')
    value = value.upper()
    value = re.sub(r"[^A-Z0-9%./' ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_for_fuzzy(value: Optional[str]) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^A-Z0-9 ]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_abv_percent(value: Optional[str]) -> Optional[float]:
    if not value:
        return None

    text = value.upper()

    # Matches "45%", "45.0 %", "45% ALC/VOL"
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if pct_match:
        return float(pct_match.group(1))

    # Matches "90 proof" and converts to ABV
    proof_match = re.search(r"(\d+(?:\.\d+)?)\s*PROOF", text)
    if proof_match:
        return float(proof_match.group(1)) / 2

    return None


def normalize_net_contents(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    text = value.upper().replace(" ", "")
    match = re.search(r"(\d+(?:\.\d+)?)(ML|MILLILITER|MILLILITERS|L|LITER|LITERS)", text)
    if not match:
        return None

    amount = float(match.group(1))
    unit = match.group(2)

    if unit in ["L", "LITER", "LITERS"]:
        amount = amount * 1000

    if amount.is_integer():
        return f"{int(amount)}ML"
    return f"{amount}ML"


def fuzzy_check(field: str, expected: str, found: Optional[str], pass_score: int = 90, warning_score: int = 75) -> FieldCheck:
    if not found:
        return FieldCheck(
            field=field,
            status=CheckStatus.FAIL,
            expected=expected,
            found=found,
            score=0,
            message=f"{field} was not found on the label."
        )

    expected_norm = normalize_for_fuzzy(expected)
    found_norm = normalize_for_fuzzy(found)

    score = fuzz.token_sort_ratio(expected_norm, found_norm)
    partial_score = fuzz.partial_ratio(expected_norm, found_norm)
    token_set_score = fuzz.token_set_ratio(expected_norm, found_norm)

    best_score = max(score, partial_score, token_set_score)

    # Important for cases like:
    # Expected: OLD TOM DISTILLERY
    # Found: OLD TOM
    # This is incomplete but highly related, so mark WARNING instead of FAIL.
    expected_tokens = set(expected_norm.split())
    found_tokens = set(found_norm.split())

    missing_tokens = expected_tokens - found_tokens
    shared_tokens = expected_tokens & found_tokens

    if expected_norm == found_norm:
        status = CheckStatus.PASS
        msg = f"{field} matches exactly after normalization."
    elif token_set_score >= pass_score and len(missing_tokens) == 0:
        status = CheckStatus.PASS
        msg = f"{field} matches after ignoring word order/punctuation."
    elif best_score >= pass_score:
        status = CheckStatus.PASS
        msg = f"{field} appears to match with minor formatting differences."
    elif len(shared_tokens) >= 2 and len(missing_tokens) <= 2:
        status = CheckStatus.WARNING
        msg = f"{field} is partially matched but missing token(s): {', '.join(sorted(missing_tokens))}. Agent review recommended."
    elif best_score >= warning_score:
        status = CheckStatus.WARNING
        msg = f"{field} is similar but should be reviewed by an agent."
    else:
        status = CheckStatus.FAIL
        msg = f"{field} does not match the application."

    return FieldCheck(
        field=field,
        status=status,
        expected=expected,
        found=found,
        score=round(best_score, 2),
        message=msg
    )

def alcohol_content_check(expected: str, found: Optional[str]) -> FieldCheck:
    expected_abv = extract_abv_percent(expected)
    found_abv = extract_abv_percent(found)

    if found_abv is None:
        return FieldCheck(
            field="Alcohol Content",
            status=CheckStatus.FAIL,
            expected=expected,
            found=found,
            score=0,
            message="Alcohol content was not found or could not be parsed."
        )

    if expected_abv is None:
        return FieldCheck(
            field="Alcohol Content",
            status=CheckStatus.WARNING,
            expected=expected,
            found=found,
            score=None,
            message="Expected alcohol content could not be parsed; agent review needed."
        )

    difference = abs(expected_abv - found_abv)
    if difference <= 0.1:
        return FieldCheck(
            field="Alcohol Content",
            status=CheckStatus.PASS,
            expected=expected,
            found=found,
            score=100,
            message=f"Alcohol content matches: expected {expected_abv}% ABV, found {found_abv}% ABV."
        )

    return FieldCheck(
        field="Alcohol Content",
        status=CheckStatus.FAIL,
        expected=expected,
        found=found,
        score=0,
        message=f"Alcohol content mismatch: expected {expected_abv}% ABV, found {found_abv}% ABV."
    )


def net_contents_check(expected: str, found: Optional[str]) -> FieldCheck:
    expected_norm = normalize_net_contents(expected)
    found_norm = normalize_net_contents(found)

    if not found_norm:
        return FieldCheck(
            field="Net Contents",
            status=CheckStatus.FAIL,
            expected=expected,
            found=found,
            score=0,
            message="Net contents were not found or could not be parsed."
        )

    if expected_norm == found_norm:
        return FieldCheck(
            field="Net Contents",
            status=CheckStatus.PASS,
            expected=expected,
            found=found,
            score=100,
            message=f"Net contents match after unit normalization: {found_norm}."
        )

    return FieldCheck(
        field="Net Contents",
        status=CheckStatus.FAIL,
        expected=expected,
        found=found,
        score=0,
        message=f"Net contents mismatch: expected {expected_norm}, found {found_norm}."
    )


def government_warning_check(found: Optional[str], raw_text: Optional[str]) -> FieldCheck:
    warning_source = found or raw_text or ""

    if not warning_source:
        return FieldCheck(
            field="Government Warning",
            status=CheckStatus.FAIL,
            expected=REQUIRED_GOVERNMENT_WARNING,
            found=None,
            score=0,
            message="Government warning was not found on the label."
        )

    required_norm = normalize_text(REQUIRED_GOVERNMENT_WARNING)
    found_norm = normalize_text(warning_source)

    # Strict ideal check.
    if required_norm in found_norm:
        return FieldCheck(
            field="Government Warning",
            status=CheckStatus.PASS,
            expected=REQUIRED_GOVERNMENT_WARNING,
            found=found,
            score=100,
            message="Government warning text appears to match the required wording."
        )

    # Partial check for helpful review feedback.
    if "GOVERNMENT WARNING" not in found_norm:
        return FieldCheck(
            field="Government Warning",
            status=CheckStatus.FAIL,
            expected=REQUIRED_GOVERNMENT_WARNING,
            found=found,
            score=0,
            message="Government warning heading was missing or not detected in all caps."
        )

    similarity = fuzz.partial_ratio(required_norm, found_norm)

    if similarity >= 85:
        status = CheckStatus.WARNING
        msg = "Government warning is close, but wording/punctuation should be reviewed carefully."
    else:
        status = CheckStatus.FAIL
        msg = "Government warning text does not match the required wording."

    return FieldCheck(
        field="Government Warning",
        status=status,
        expected=REQUIRED_GOVERNMENT_WARNING,
        found=found,
        score=round(similarity, 2),
        message=msg
    )


def overall_status(checks: List[FieldCheck]) -> CheckStatus:
    if any(c.status == CheckStatus.FAIL for c in checks):
        return CheckStatus.FAIL
    if any(c.status == CheckStatus.WARNING for c in checks):
        return CheckStatus.WARNING
    return CheckStatus.PASS


def verify_label(application: ApplicationFields, extracted: ExtractedLabelFields) -> List[FieldCheck]:
    checks = [
        fuzzy_check("Brand Name", application.brand_name, extracted.brand_name),
        fuzzy_check("Class/Type", application.class_type, extracted.class_type),
        alcohol_content_check(application.alcohol_content, extracted.alcohol_content),
        net_contents_check(application.net_contents, extracted.net_contents),
        government_warning_check(extracted.government_warning, extracted.raw_text),
    ]

    if application.producer_name_address:
        checks.append(
            fuzzy_check(
                "Producer/Bottler Name and Address",
                application.producer_name_address,
                extracted.producer_name_address,
                pass_score=85,
                warning_score=70
            )
        )

    if application.country_of_origin:
        checks.append(
            fuzzy_check(
                "Country of Origin",
                application.country_of_origin,
                extracted.country_of_origin,
                pass_score=90,
                warning_score=80
            )
        )

    return checks
