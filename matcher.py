import re
import pandas as pd
from rapidfuzz.fuzz import ratio, token_set_ratio


WEBSITE_FILE = "bellhaven_locations.csv"
CRM_FILE = "crm_accounts.csv"
OUTPUT_FILE = "match_results.csv"

BELLHAVEN_PARENT_ID = "0015QAPLGS3FVYEEEM"


# =========================================================
# NORMALIZATION
# =========================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def normalize_name(value):
    value = clean_text(value)

    replacements = {
        "health care": "healthcare",
        "centre": "center",
        "rehabilitation": "rehab",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value.strip()


def normalize_street(value):
    value = clean_text(value)

    replacements = {
        "street": "st",
        "avenue": "ave",
        "boulevard": "blvd",
        "road": "rd",
        "drive": "dr",
        "lane": "ln",
        "court": "ct",
        "circle": "cir",
        "highway": "hwy",
        "parkway": "pkwy",
        "north": "n",
        "south": "s",
        "east": "e",
        "west": "w",
    }

    words = value.split()

    words = [
        replacements.get(word, word)
        for word in words
    ]

    return " ".join(words)


def normalize_zip(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value[:5]


def normalize_phone(value):
    """
    Normalize US phone numbers by removing all
    formatting characters.

    Examples:
    (614) 555-1234
    614-555-1234
    +1 614 555 1234

    all become:
    6145551234
    """

    if pd.isna(value):
        return ""

    digits = re.sub(
        r"\D",
        "",
        str(value)
    )

    if (
        len(digits) == 11
        and digits.startswith("1")
    ):
        digits = digits[1:]

    return digits


# =========================================================
# MATCH SCORING
# =========================================================

def calculate_match_score(web, crm):

    web_name = normalize_name(
        web.get("name", "")
    )

    crm_name = normalize_name(
        crm.get("name", "")
    )

    web_street = normalize_street(
        web.get("address", "")
    )

    crm_street = normalize_street(
        crm.get("billing_street", "")
    )

    web_city = clean_text(
        web.get("city", "")
    )

    crm_city = clean_text(
        crm.get("billing_city", "")
    )

    web_state = clean_text(
        web.get("state", "")
    )

    crm_state = clean_text(
        crm.get("billing_state", "")
    )

    web_zip = normalize_zip(
        web.get("zip", "")
    )

    crm_zip = normalize_zip(
        crm.get("billing_zip", "")
    )

    web_phone = normalize_phone(
        web.get("phone", "")
    )

    crm_phone = normalize_phone(
        crm.get("phone", "")
    )

    # -----------------------------------------------------
    # Individual signals
    # -----------------------------------------------------

    name_score = token_set_ratio(
        web_name,
        crm_name
    )

    street_score = ratio(
        web_street,
        crm_street
    )

    zip_match = (
        web_zip != ""
        and crm_zip != ""
        and web_zip == crm_zip
    )

    phone_match = (
        web_phone != ""
        and crm_phone != ""
        and web_phone == crm_phone
    )

    city_match = (
        web_city != ""
        and crm_city != ""
        and web_city == crm_city
    )

    state_match = (
        web_state != ""
        and crm_state != ""
        and web_state == crm_state
    )

    # -----------------------------------------------------
    # Weighted score
    # -----------------------------------------------------

    score = 0

    # Physical location is most important
    score += street_score * 0.30

    # Name supports the match
    score += name_score * 0.25

    # ZIP is strong evidence
    if zip_match:
        score += 20

    # Phone is another strong identifier
    if phone_match:
        score += 15

    # Supporting geographic evidence
    if city_match:
        score += 7

    if state_match:
        score += 3

    score = min(
        round(score, 2),
        100
    )

    return {
        "score": score,
        "name_score": round(name_score, 2),
        "street_score": round(street_score, 2),
        "zip_match": zip_match,
        "phone_match": phone_match,
        "city_match": city_match,
        "state_match": state_match,
    }


# =========================================================
# CONFIDENCE RULES
# =========================================================

def is_confident_match(evidence):
    """
    Business rules used in addition to the
    weighted numeric score.
    """

    # Exact ZIP + very strong physical address
    if (
        evidence["zip_match"]
        and evidence["street_score"] >= 90
    ):
        return True

    # Same phone and ZIP
    if (
        evidence["phone_match"]
        and evidence["zip_match"]
    ):
        return True

    # Same phone + strong name
    if (
        evidence["phone_match"]
        and evidence["name_score"] >= 80
    ):
        return True

    # Strong address + strong name
    if (
        evidence["street_score"] >= 90
        and evidence["name_score"] >= 80
    ):
        return True

    # Strong overall score
    if evidence["score"] >= 75:
        return True

    return False


# =========================================================
# CLASSIFICATION
# =========================================================

def classify_match(web, crm, evidence):
    """
    Describe what kind of CRM situation
    appears to exist.

    This function does NOT update the CRM.
    """

    if not is_confident_match(evidence):
        return "NO_CONFIDENT_MATCH"

    status = str(
    crm.get("status", "") or ""
    ).strip()
    
    # A reviewer already escalated this account.
    # Do not keep proposing an automated ownership change.
    if status == "Needs Review":
        return "MATCH_ALREADY_NEEDS_REVIEW"

    parent_id = str(
        crm.get("parent_id", "") or ""
    ).strip()

    lifetime_revenue = float(
        crm.get("lifetime_revenue", 0) or 0
    )

    outstanding_ar = float(
        crm.get("outstanding_ar", 0) or 0
    )

    # -----------------------------------------------------
    # Already correctly under Bellhaven
    # -----------------------------------------------------

    if parent_id == BELLHAVEN_PARENT_ID:

        if evidence["name_score"] < 90:
            return "MATCH_NAME_UPDATE"

        return "MATCH_CORRECT"

    # -----------------------------------------------------
    # Wrong or missing parent
    # -----------------------------------------------------

    # Clipboard CHOW SOP
    if (
        lifetime_revenue > 0
        and outstanding_ar > 0
    ):
        return "MATCH_CHOW_REQUIRED"

    return "MATCH_REPARENT"


# =========================================================
# PROPOSED BUSINESS ACTION
# =========================================================

def get_proposed_action(classification):
    """
    Convert technical classification into a
    reviewer-friendly proposed action.
    """

    actions = {
        "MATCH_CORRECT":
            "NO_ACTION",
    
        "MATCH_NAME_UPDATE":
            "UPDATE_NAME",
    
        "MATCH_REPARENT":
            "REPARENT_ACCOUNT",
    
        "MATCH_CHOW_REQUIRED":
            "CREATE_CHOW_ACCOUNT",
    
        "NO_CONFIDENT_MATCH":
            "REVIEW_FOR_NEW_ACCOUNT",
        "MATCH_ALREADY_NEEDS_REVIEW":
        "NO_ACTION",
    }

    return actions.get(
        classification,
        "MANUAL_REVIEW"
    )


# =========================================================
# WEBSITE -> CRM MATCHING
# =========================================================

def match_website_to_crm(
    web_df,
    crm_df
):

    results = []

    for _, web in web_df.iterrows():

        candidate_scores = []

        for crm_index, crm in crm_df.iterrows():

            evidence = calculate_match_score(
                web,
                crm
            )

            candidate_scores.append(
                {
                    "crm_index": crm_index,
                    **evidence
                }
            )

        candidate_scores.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        best = candidate_scores[0]

        second = (
            candidate_scores[1]
            if len(candidate_scores) > 1
            else None
        )

        best_crm = crm_df.loc[
            best["crm_index"]
        ]

        second_score = (
            second["score"]
            if second
            else 0
        )

        score_gap = round(
            best["score"] - second_score,
            2
        )

        classification = classify_match(
            web,
            best_crm,
            best
        )

        proposed_action = get_proposed_action(
            classification
        )

        # A close second candidate means the match
        # deserves more human attention.
        ambiguous = (
            is_confident_match(best)
            and score_gap < 8
        )

        evidence_text = (
            f"Name={best['name_score']}; "
            f"Street={best['street_score']}; "
            f"ZIP={best['zip_match']}; "
            f"Phone={best['phone_match']}; "
            f"City={best['city_match']}; "
            f"State={best['state_match']}"
        )

        results.append(
            {
                # -----------------------------------------
                # Website evidence
                # -----------------------------------------
                "website_name":
                    web.get("name", ""),

                "website_address":
                    web.get("address", ""),

                "website_city":
                    web.get("city", ""),

                "website_state":
                    web.get("state", ""),

                "website_zip":
                    web.get("zip", ""),

                "website_phone":
                    web.get("phone", ""),

                "website_care_offerings":
                    web.get(
                        "care_offerings",
                        ""
                    ),

                "source_url":
                    web.get(
                        "source_url",
                        ""
                    ),

                # -----------------------------------------
                # Best CRM candidate
                # -----------------------------------------
                "crm_account_id":
                    best_crm.get(
                        "account_id",
                        ""
                    ),

                "crm_name":
                    best_crm.get(
                        "name",
                        ""
                    ),

                "crm_address":
                    best_crm.get(
                        "billing_street",
                        ""
                    ),

                "crm_city":
                    best_crm.get(
                        "billing_city",
                        ""
                    ),

                "crm_state":
                    best_crm.get(
                        "billing_state",
                        ""
                    ),

                "crm_zip":
                    best_crm.get(
                        "billing_zip",
                        ""
                    ),

                "crm_phone":
                    best_crm.get(
                        "phone",
                        ""
                    ),

                "crm_parent_id":
                    best_crm.get(
                        "parent_id",
                        ""
                    ),

                "crm_parent_name":
                    best_crm.get(
                        "parent_name",
                        ""
                    ),

                "lifetime_revenue":
                    best_crm.get(
                        "lifetime_revenue",
                        0
                    ),

                "outstanding_ar":
                    best_crm.get(
                        "outstanding_ar",
                        0
                    ),

                # -----------------------------------------
                # Matching evidence
                # -----------------------------------------
                "match_score":
                    best["score"],

                "name_score":
                    best["name_score"],

                "street_score":
                    best["street_score"],

                "zip_match":
                    best["zip_match"],

                "phone_match":
                    best["phone_match"],

                "city_match":
                    best["city_match"],

                "state_match":
                    best["state_match"],

                "second_best_score":
                    second_score,

                "score_gap":
                    score_gap,

                "ambiguous":
                    ambiguous,

                # -----------------------------------------
                # Classification / action
                # -----------------------------------------
                "classification":
                    classification,

                "proposed_action":
                    proposed_action,

                "evidence":
                    evidence_text,

                # -----------------------------------------
                # Review app fields
                # -----------------------------------------
                "decision": "",

                "decision_note": "",
            }
        )

    return pd.DataFrame(results)


# =========================================================
# DUPLICATE DETECTION
# =========================================================

def find_possible_duplicates(crm_df):
    """
    Identify CRM records that likely represent
    the same physical facility.

    CHOW-linked historical/current account pairs
    are intentionally excluded.
    """

    duplicates = []
    

    for i in range(len(crm_df)):

        account_a = crm_df.iloc[i]

        for j in range(
            i + 1,
            len(crm_df)
        ):

            account_b = crm_df.iloc[j]
            # ---------------------------------------------
            # ALREADY-RESOLVED DUPLICATE SAFETY
            # ---------------------------------------------

            dup_a = str(
                account_a.get(
                    "duplicate_of_account",
                    ""
                ) or ""
            ).strip()

            dup_b = str(
                account_b.get(
                    "duplicate_of_account",
                    ""
                ) or ""
            ).strip()

            # If either account is already linked as a
            # duplicate, do not propose this pair again.
            if dup_a or dup_b:
                continue
            # -------------------------------------------------
            # CHOW SAFETY
            # -------------------------------------------------
            # A historical account linked to a newly created
            # current account is intentional and must not be
            # treated as a duplicate.
            # -------------------------------------------------

            id_a = str(
                account_a.get(
                    "account_id",
                    ""
                )
            ).strip()

            id_b = str(
                account_b.get(
                    "account_id",
                    ""
                )
            ).strip()

            chow_a = str(
                account_a.get(
                    "chow_current_account",
                    ""
                )
                or ""
            ).strip()

            chow_b = str(
                account_b.get(
                    "chow_current_account",
                    ""
                )
                or ""
            ).strip()

            if (
                chow_a == id_b
                or chow_b == id_a
            ):
                continue

            # -------------------------------------------------
            # ZIP check
            # -------------------------------------------------

            zip_a = normalize_zip(
                account_a.get(
                    "billing_zip",
                    ""
                )
            )

            zip_b = normalize_zip(
                account_b.get(
                    "billing_zip",
                    ""
                )
            )

            # Require same ZIP first
            if (
                not zip_a
                or not zip_b
                or zip_a != zip_b
            ):
                continue

            # -------------------------------------------------
            # Address similarity
            # -------------------------------------------------

            street_score = ratio(
                normalize_street(
                    account_a.get(
                        "billing_street",
                        ""
                    )
                ),
                normalize_street(
                    account_b.get(
                        "billing_street",
                        ""
                    )
                )
            )

            # -------------------------------------------------
            # Name similarity
            # -------------------------------------------------

            name_score = token_set_ratio(
                normalize_name(
                    account_a.get(
                        "name",
                        ""
                    )
                ),
                normalize_name(
                    account_b.get(
                        "name",
                        ""
                    )
                )
            )

            # -------------------------------------------------
            # Phone comparison
            # -------------------------------------------------

            phone_a = normalize_phone(
                account_a.get(
                    "phone",
                    ""
                )
            )

            phone_b = normalize_phone(
                account_b.get(
                    "phone",
                    ""
                )
            )

            phone_match = (
                phone_a != ""
                and phone_b != ""
                and phone_a == phone_b
            )

            # -------------------------------------------------
            # Duplicate candidate rule
            # -------------------------------------------------

            if (
                street_score >= 90
                and name_score >= 85
            ):

                duplicates.append(
                    {
                        "account_1_id":
                            account_a[
                                "account_id"
                            ],

                        "account_1_name":
                            account_a["name"],

                        "account_2_id":
                            account_b[
                                "account_id"
                            ],

                        "account_2_name":
                            account_b["name"],

                        "zip":
                            zip_a,

                        "street_score":
                            street_score,

                        "name_score":
                            name_score,

                        "phone_match":
                            phone_match,

                        "proposed_action":
                            "REVIEW_DUPLICATE",
                    }
                )

    return pd.DataFrame(
        duplicates
    )


# =========================================================
# STALE BELLHAVEN ACCOUNTS
# =========================================================

def find_stale_bellhaven_accounts(
    crm_df,
    match_df
):
    """
    Find active Bellhaven accounts that do not
    confidently match a current website facility.

    Already handled Needs Review, Inactive, and
    duplicate-linked accounts are excluded so
    daily reruns do not re-propose them.
    """

    # -----------------------------------------------------
    # Start with accounts currently under Bellhaven
    # -----------------------------------------------------

    bellhaven_crm = crm_df[
        crm_df["parent_id"]
        .fillna("")
        == BELLHAVEN_PARENT_ID
    ].copy()

    # -----------------------------------------------------
    # Do not re-propose records already handled
    # -----------------------------------------------------

    bellhaven_crm = bellhaven_crm[
        ~bellhaven_crm[
            "status"
        ].isin(
            [
                "Needs Review",
                "Inactive",
            ]
        )
    ].copy()

    # -----------------------------------------------------
    # Do not re-propose known duplicate records
    # -----------------------------------------------------

    bellhaven_crm = bellhaven_crm[
        bellhaven_crm[
            "duplicate_of_account"
        ]
        .fillna("")
        .eq("")
    ].copy()

    # -----------------------------------------------------
    # Find CRM accounts already confidently matched
    # to current website facilities
    # -----------------------------------------------------

    confidently_matched_ids = set(
        match_df.loc[
            match_df[
                "classification"
            ] != "NO_CONFIDENT_MATCH",
            "crm_account_id"
        ].astype(str)
    )

    # -----------------------------------------------------
    # Remaining records are stale candidates
    # -----------------------------------------------------

    stale = bellhaven_crm[
        ~bellhaven_crm[
            "account_id"
        ]
        .astype(str)
        .isin(
            confidently_matched_ids
        )
    ].copy()

    if not stale.empty:

        stale[
            "proposed_action"
        ] = (
            "REVIEW_STALE_ACCOUNT"
        )

    return stale


# =========================================================
# OUTPUT SUMMARY
# =========================================================

def print_summary(match_df):

    print(
        "\n--- MATCHING SUMMARY ---"
    )

    print(
        f"Website facilities: "
        f"{len(match_df)}"
    )

    print(
        "\nClassification counts:"
    )

    print(
        match_df[
            "classification"
        ].value_counts()
    )

    print(
        "\nProposed action counts:"
    )

    print(
        match_df[
            "proposed_action"
        ].value_counts()
    )

    print(
        "\nAmbiguous matches:",
        match_df[
            "ambiguous"
        ].sum()
    )

    low = match_df[
        match_df[
            "classification"
        ] == "NO_CONFIDENT_MATCH"
    ]

    print(
        "\nLow-confidence / review-needed:"
    )

    if low.empty:

        print("None")

    else:

        print(
            low[
                [
                    "website_name",
                    "crm_name",
                    "match_score",
                    "website_zip",
                    "crm_zip",
                    "phone_match",
                    "proposed_action",
                ]
            ].to_string(
                index=False
            )
        )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print(
        "Loading website and CRM data..."
    )

    website_df = (
        pd.read_csv(
            WEBSITE_FILE,
            dtype=str
        )
        .fillna("")
    )

    crm_df = (
        pd.read_csv(
            CRM_FILE
        )
        .fillna("")
    )

    # -----------------------------------------------------
    # Financial fields
    # -----------------------------------------------------

    crm_df[
        "lifetime_revenue"
    ] = pd.to_numeric(
        crm_df[
            "lifetime_revenue"
        ],
        errors="coerce"
    ).fillna(0)

    crm_df[
        "outstanding_ar"
    ] = pd.to_numeric(
        crm_df[
            "outstanding_ar"
        ],
        errors="coerce"
    ).fillna(0)

    print(
        f"Website facilities: "
        f"{len(website_df)}"
    )

    print(
        f"CRM accounts: "
        f"{len(crm_df)}"
    )

    # -----------------------------------------------------
    # Main matching
    # -----------------------------------------------------

    match_df = (
        match_website_to_crm(
            website_df,
            crm_df
        )
    )

    match_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved match results "
        f"to {OUTPUT_FILE}"
    )

    print_summary(
        match_df
    )

    # -----------------------------------------------------
    # Duplicate candidates
    # -----------------------------------------------------

    duplicate_df = (
        find_possible_duplicates(
            crm_df
        )
    )

    duplicate_df.to_csv(
        "duplicate_candidates.csv",
        index=False
    )

    print(
        "\nPossible CRM duplicates:",
        len(duplicate_df)
    )

    if not duplicate_df.empty:

        print(
            duplicate_df.to_string(
                index=False
            )
        )

    # -----------------------------------------------------
    # Stale Bellhaven records
    # -----------------------------------------------------

    stale_df = (
        find_stale_bellhaven_accounts(
            crm_df,
            match_df
        )
    )

    stale_df.to_csv(
        "stale_bellhaven_accounts.csv",
        index=False
    )

    print(
        "\nBellhaven CRM accounts "
        "not matched to current website:",
        len(stale_df)
    )

    if not stale_df.empty:

        columns = [
            "account_id",
            "name",
            "billing_city",
            "billing_state",
            "billing_zip",
            "lifetime_revenue",
            "outstanding_ar",
            "proposed_action",
        ]

        print(
            stale_df[
                columns
            ].to_string(
                index=False
            )
        )

    print(
        "\nMatching complete."
    )