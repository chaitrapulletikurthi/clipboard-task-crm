import os
import json
import hashlib
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

API_TOKEN = os.getenv("CLIPBOARD_API_TOKEN")

BASE_URL = (
    "https://analyst-assessment-production.up.railway.app/api/v1"
)

BELLHAVEN_PARENT_ID = "0015QAPLGS3FVYEEEM"

MATCH_FILE = "match_results.csv"
DUPLICATE_FILE = "duplicate_candidates.csv"
STALE_FILE = "stale_bellhaven_accounts.csv"
DECISIONS_FILE = "decisions.json"


# =========================================================
# STREAMLIT CONFIG
# =========================================================

st.set_page_config(
    page_title="Bellhaven CRM Review",
    page_icon="🏥",
    layout="wide",
)

st.title("Bellhaven CRM Review")

st.caption(
    "Human review queue for Bellhaven ownership "
    "and CRM cleanup proposals."
)


# =========================================================
# API HELPERS
# =========================================================

def get_headers():

    if not API_TOKEN:
        raise ValueError(
            "CLIPBOARD_API_TOKEN was not found. "
            "Check your .env file."
        )

    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def unwrap_api_response(payload):

    if (
        isinstance(payload, dict)
        and isinstance(payload.get("data"), dict)
    ):
        return payload["data"]

    return payload


def get_account(account_id):

    url = f"{BASE_URL}/accounts/{account_id}"

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return unwrap_api_response(
        response.json()
    )


def patch_account(
    account_id,
    payload,
):

    url = f"{BASE_URL}/accounts/{account_id}"

    response = requests.patch(
        url,
        headers=get_headers(),
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def create_account(payload):

    url = f"{BASE_URL}/accounts"

    response = requests.post(
        url,
        headers=get_headers(),
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# DECISION STORAGE
# =========================================================

def load_decisions():

    path = Path(
        DECISIONS_FILE
    )

    if not path.exists():
        return {}

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(
                file
            )

    except json.JSONDecodeError:

        return {}


def save_decisions(
    decisions
):

    with open(
        DECISIONS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            decisions,
            file,
            indent=2,
        )


def make_proposal_id(
    *values
):

    raw = "|".join(
        str(value)
        for value in values
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]


decisions = load_decisions()


# =========================================================
# DATA LOADING
# =========================================================

@st.cache_data
def load_match_data():

    if not Path(
        MATCH_FILE
    ).exists():

        return pd.DataFrame()

    try:

        return (
            pd.read_csv(
                MATCH_FILE,
                dtype=str,
            )
            .fillna("")
        )

    except pd.errors.EmptyDataError:

        return pd.DataFrame()


@st.cache_data
def load_duplicate_data():

    if not Path(
        DUPLICATE_FILE
    ).exists():

        return pd.DataFrame()

    try:

        return (
            pd.read_csv(
                DUPLICATE_FILE,
                dtype=str,
            )
            .fillna("")
        )

    except pd.errors.EmptyDataError:

        return pd.DataFrame()


@st.cache_data
def load_stale_data():

    if not Path(
        STALE_FILE
    ).exists():

        return pd.DataFrame()

    try:

        return (
            pd.read_csv(
                STALE_FILE,
                dtype=str,
            )
            .fillna("")
        )

    except pd.errors.EmptyDataError:

        return pd.DataFrame()


match_df = load_match_data()
duplicate_df = load_duplicate_data()
stale_df = load_stale_data()


# =========================================================
# GENERAL HELPERS
# =========================================================

def to_number(value):

    try:

        if value in [
            None,
            "",
        ]:
            return 0.0

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0.0


def show_decision_status(
    proposal_id
):

    if proposal_id not in decisions:

        st.info(
            "Pending review"
        )

        return

    status = (
        decisions[
            proposal_id
        ]
        .get(
            "decision",
            ""
        )
    )

    if status == "approved":

        st.success(
            "Approved"
        )

    elif status == "rejected":

        st.error(
            "Rejected"
        )

    else:

        st.warning(
            status
        )


# =========================================================
# DISPLAY HELPERS
# =========================================================

def show_match_evidence(
    row
):

    left, right = (
        st.columns(2)
    )

    with left:

        st.subheader(
            "Website evidence"
        )

        st.write(
            f"**Name:** "
            f"{row.get('website_name', '')}"
        )

        st.write(
            f"**Address:** "
            f"{row.get('website_address', '')}"
        )

        st.write(
            f"**City:** "
            f"{row.get('website_city', '')}"
        )

        st.write(
            f"**State:** "
            f"{row.get('website_state', '')}"
        )

        st.write(
            f"**ZIP:** "
            f"{row.get('website_zip', '')}"
        )

        st.write(
            f"**Phone:** "
            f"{row.get('website_phone', '')}"
        )

        st.write(
            f"**Care offerings:** "
            f"{row.get('website_care_offerings', '')}"
        )

        source_url = row.get(
            "source_url",
            ""
        )

        if source_url:

            st.markdown(
                f"[Open Bellhaven source]"
                f"({source_url})"
            )

    with right:

        st.subheader(
            "CRM candidate"
        )

        st.write(
            f"**Account ID:** "
            f"{row.get('crm_account_id', '')}"
        )

        st.write(
            f"**Name:** "
            f"{row.get('crm_name', '')}"
        )

        st.write(
            f"**Address:** "
            f"{row.get('crm_address', '')}"
        )

        st.write(
            f"**City:** "
            f"{row.get('crm_city', '')}"
        )

        st.write(
            f"**State:** "
            f"{row.get('crm_state', '')}"
        )

        st.write(
            f"**ZIP:** "
            f"{row.get('crm_zip', '')}"
        )

        st.write(
            f"**Phone:** "
            f"{row.get('crm_phone', '')}"
        )

        st.write(
            f"**Current parent:** "
            f"{row.get('crm_parent_name', '')}"
        )

        st.write(
            f"**Lifetime revenue:** "
            f"${row.get('lifetime_revenue', '0')}"
        )

        st.write(
            f"**Outstanding AR:** "
            f"${row.get('outstanding_ar', '0')}"
        )


def show_score_evidence(
    row
):

    st.write(
        "### Matching evidence"
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    c1.metric(
        "Overall score",
        row.get(
            "match_score",
            ""
        ),
    )

    c2.metric(
        "Name score",
        row.get(
            "name_score",
            ""
        ),
    )

    c3.metric(
        "Street score",
        row.get(
            "street_score",
            ""
        ),
    )

    c4.metric(
        "Score gap",
        row.get(
            "score_gap",
            ""
        ),
    )

    st.write(
        f"""
**ZIP match:** {row.get('zip_match', '')}  
**Phone match:** {row.get('phone_match', '')}  
**City match:** {row.get('city_match', '')}  
**State match:** {row.get('state_match', '')}  
**Ambiguous:** {row.get('ambiguous', '')}
"""
    )


# =========================================================
# NEW ACCOUNT PAYLOAD
# =========================================================

def build_new_account_payload(
    row
):

    return {
        "name":
            row.get(
                "website_name",
                ""
            ),

        "parent_id":
            BELLHAVEN_PARENT_ID,

        "billing_street":
            row.get(
                "website_address",
                ""
            ),

        "billing_city":
            row.get(
                "website_city",
                ""
            ),

        "billing_state":
            row.get(
                "website_state",
                ""
            ),

        "billing_zip":
            row.get(
                "website_zip",
                ""
            ),

        "phone":
            row.get(
                "website_phone",
                ""
            ),

        "care_type":
            row.get(
                "website_care_offerings",
                ""
            ),

        "status":
            "Active",
    }


# =========================================================
# CREATED ACCOUNT ID
# =========================================================

def get_created_account_id(
    response
):

    if not isinstance(
        response,
        dict,
    ):

        return None

    if response.get(
        "account_id"
    ):

        return response[
            "account_id"
        ]

    data = response.get(
        "data"
    )

    if (
        isinstance(
            data,
            dict
        )
        and data.get(
            "account_id"
        )
    ):

        return data[
            "account_id"
        ]

    return None


# =========================================================
# APPLY MATCH ACTION
# =========================================================

def apply_match_action(
    row,
    selected_action,
):

    account_id = row.get(
        "crm_account_id",
        ""
    )

    # -----------------------------------------------------
    # NO ACTION
    # -----------------------------------------------------

    if selected_action == "NO_ACTION":

        return {
            "message":
                "No CRM update required."
        }

    # -----------------------------------------------------
    # UPDATE NAME
    # -----------------------------------------------------

    if selected_action == "UPDATE_NAME":

        payload = {
            "name":
                row.get(
                    "website_name",
                    ""
                )
        }

        return patch_account(
            account_id,
            payload,
        )

    # -----------------------------------------------------
    # REPARENT
    # -----------------------------------------------------

    if selected_action == "REPARENT_ACCOUNT":

        current = get_account(
            account_id
        )

        revenue = to_number(
            current.get(
                "lifetime_revenue",
                0
            )
        )

        outstanding_ar = to_number(
            current.get(
                "outstanding_ar",
                0
            )
        )

        if (
            revenue > 0
            and outstanding_ar > 0
        ):

            raise ValueError(
                "CHOW safety check triggered. "
                "This account has revenue history "
                "and outstanding AR, so its parent "
                "must not be changed directly."
            )

        payload = {
            "parent_id":
                BELLHAVEN_PARENT_ID
        }

        return patch_account(
            account_id,
            payload,
        )

    # -----------------------------------------------------
    # CREATE NEW ACCOUNT
    # -----------------------------------------------------

    if selected_action == "CREATE_NEW_ACCOUNT":

        payload = (
            build_new_account_payload(
                row
            )
        )

        return create_account(
            payload
        )

    # -----------------------------------------------------
    # NEEDS REVIEW
    # -----------------------------------------------------

    if selected_action == "MARK_NEEDS_REVIEW":

        if not account_id:

            raise ValueError(
                "No CRM account is available "
                "to mark for review."
            )

        payload = {
            "status":
                "Needs Review"
        }

        return patch_account(
            account_id,
            payload,
        )

    # -----------------------------------------------------
    # CHOW
    # -----------------------------------------------------

    if selected_action == "CREATE_CHOW_ACCOUNT":

        current = get_account(
            account_id
        )

        revenue = to_number(
            current.get(
                "lifetime_revenue",
                0
            )
        )

        outstanding_ar = to_number(
            current.get(
                "outstanding_ar",
                0
            )
        )

        if not (
            revenue > 0
            and outstanding_ar > 0
        ):

            raise ValueError(
                "CHOW conditions are not met. "
                "This account should probably "
                "be directly re-parented instead."
            )

        existing_chow = str(
            current.get(
                "chow_current_account",
                ""
            )
            or ""
        ).strip()

        if existing_chow:

            return {
                "message":
                    "CHOW already exists.",

                "new_account_id":
                    existing_chow,
            }

        new_payload = (
            build_new_account_payload(
                row
            )
        )

        new_account_response = (
            create_account(
                new_payload
            )
        )

        new_account_id = (
            get_created_account_id(
                new_account_response
            )
        )

        if not new_account_id:

            raise ValueError(
                "New CHOW account was created, "
                "but the returned account ID "
                "could not be read."
            )

        # Preserve old account.
        # Only set chow_current_account.
        old_update = {
            "chow_current_account":
                new_account_id
        }

        patch_account(
            account_id,
            old_update,
        )

        return {
            "message":
                "CHOW completed.",

            "old_account_id":
                account_id,

            "new_account_id":
                new_account_id,
        }

    raise ValueError(
        f"Unsupported action: "
        f"{selected_action}"
    )


# =========================================================
# REVIEW SETTINGS
# =========================================================

st.sidebar.header(
    "Review Settings"
)

show_decided = (
    st.sidebar.checkbox(
        "Show already decided proposals",
        value=False,
    )
)


# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4 = (
    st.tabs(
        [
            "Facility Matches",
            "Duplicates",
            "Stale Bellhaven",
            "Decision History",
        ]
    )
)


# =========================================================
# FACILITY MATCHES
# =========================================================

with tab1:

    st.header(
        "Website → CRM Review"
    )

    if match_df.empty:

        st.warning(
            "match_results.csv was not found."
        )

    else:

        show_no_action = (
            st.checkbox(
                "Show NO_ACTION records",
                value=False,
            )
        )

        rows_to_display = []

        for _, row in match_df.iterrows():

            system_action = row.get(
                "proposed_action",
                ""
            )

            if (
                not show_no_action
                and system_action
                == "NO_ACTION"
            ):
                continue

            # IMPORTANT:
            # Proposed action is part of the ID.
            # Re-parent and name update are separate proposals.
            proposal_id = (
                make_proposal_id(
                    "match",
                    row.get(
                        "website_name",
                        ""
                    ),
                    row.get(
                        "source_url",
                        ""
                    ),
                    row.get(
                        "crm_account_id",
                        ""
                    ),
                    row.get(
                        "proposed_action",
                        ""
                    ),
                )
            )

            if (
                proposal_id in decisions
                and not show_decided
            ):
                continue

            rows_to_display.append(
                (
                    row,
                    proposal_id,
                )
            )

        st.write(
            f"{len(rows_to_display)} "
            f"records shown."
        )

        for (
            row,
            proposal_id,
        ) in rows_to_display:

            title = (
                f"{row.get('website_name', '')} "
                f"→ "
                f"{row.get('proposed_action', '')}"
            )

            with st.expander(
                title,
                expanded=False,
            ):

                show_decision_status(
                    proposal_id
                )

                st.write(
                    f"**Classification:** "
                    f"{row.get('classification', '')}"
                )

                st.write(
                    f"**System proposal:** "
                    f"{row.get('proposed_action', '')}"
                )

                show_match_evidence(
                    row
                )

                show_score_evidence(
                    row
                )

                st.divider()

                system_action = row.get(
                    "proposed_action",
                    ""
                )

                if (
                    system_action
                    == "REVIEW_FOR_NEW_ACCOUNT"
                ):

                    options = [
                        "CREATE_NEW_ACCOUNT",
                        "MARK_NEEDS_REVIEW",
                        "NO_ACTION",
                        "REPARENT_ACCOUNT",
                        "CREATE_CHOW_ACCOUNT",
                    ]

                else:

                    options = [
                        system_action,
                        "MARK_NEEDS_REVIEW",
                        "NO_ACTION",
                    ]

                selected_action = (
                    st.selectbox(
                        "Final action",
                        options=options,
                        key=(
                            f"action_"
                            f"{proposal_id}"
                        ),
                    )
                )

                if (
                    selected_action
                    == "UPDATE_NAME"
                ):

                    st.caption(
                        "CRM write: "
                        "update name only."
                    )

                elif (
                    selected_action
                    == "REPARENT_ACCOUNT"
                ):

                    st.caption(
                        "CRM write: "
                        "update parent_id only."
                    )

                elif (
                    selected_action
                    == "MARK_NEEDS_REVIEW"
                ):

                    st.caption(
                        "CRM write: mark the candidate "
                        "account as Needs Review. "
                        "No parent change is made."
                    )

                elif (
                    selected_action
                    == "CREATE_NEW_ACCOUNT"
                ):

                    st.caption(
                        "CRM write: create a new "
                        "Active facility account "
                        "under Bellhaven using "
                        "website data."
                    )

                elif (
                    selected_action
                    == "CREATE_CHOW_ACCOUNT"
                ):

                    st.caption(
                        "CRM write: preserve the old "
                        "account, create a new "
                        "Bellhaven account, and set "
                        "chow_current_account on "
                        "the old account."
                    )

                review_note = (
                    st.text_area(
                        "Reviewer note",
                        key=(
                            f"note_"
                            f"{proposal_id}"
                        ),
                        placeholder=(
                            "Brief reason "
                            "for the decision."
                        ),
                    )
                )

                already_decided = (
                    proposal_id in decisions
                )

                c1, c2 = (
                    st.columns(2)
                )

                with c1:

                    if st.button(
                        "Approve",
                        key=(
                            f"approve_"
                            f"{proposal_id}"
                        ),
                        disabled=already_decided,
                        type="primary",
                    ):

                        try:

                            with st.spinner(
                                "Applying approved "
                                "CRM change..."
                            ):

                                api_result = (
                                    apply_match_action(
                                        row,
                                        selected_action,
                                    )
                                )

                            decisions[
                                proposal_id
                            ] = {
                                "decision":
                                    "approved",

                                "proposal_type":
                                    "match",

                                "website_name":
                                    row.get(
                                        "website_name",
                                        ""
                                    ),

                                "crm_account_id":
                                    row.get(
                                        "crm_account_id",
                                        ""
                                    ),

                                "action":
                                    selected_action,

                                "review_note":
                                    review_note,

                                "api_result":
                                    api_result,
                            }

                            save_decisions(
                                decisions
                            )

                            st.success(
                                "Approved "
                                "and processed."
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                f"CRM update failed: "
                                f"{error}"
                            )

                with c2:

                    if st.button(
                        "Reject",
                        key=(
                            f"reject_"
                            f"{proposal_id}"
                        ),
                        disabled=already_decided,
                    ):

                        decisions[
                            proposal_id
                        ] = {
                            "decision":
                                "rejected",

                            "proposal_type":
                                "match",

                            "website_name":
                                row.get(
                                    "website_name",
                                    ""
                                ),

                            "crm_account_id":
                                row.get(
                                    "crm_account_id",
                                    ""
                                ),

                            "action":
                                selected_action,

                            "review_note":
                                review_note,
                        }

                        save_decisions(
                            decisions
                        )

                        st.success(
                            "Proposal rejected."
                        )

                        st.rerun()


# =========================================================
# DUPLICATES
# =========================================================

with tab2:

    st.header(
        "Possible Duplicate Accounts"
    )

    if duplicate_df.empty:

        st.success(
            "No duplicate candidates found."
        )

    else:

        duplicate_rows = []

        for _, row in duplicate_df.iterrows():

            proposal_id = (
                make_proposal_id(
                    "duplicate",
                    row.get(
                        "account_1_id",
                        ""
                    ),
                    row.get(
                        "account_2_id",
                        ""
                    ),
                )
            )

            if (
                proposal_id in decisions
                and not show_decided
            ):
                continue

            duplicate_rows.append(
                (
                    row,
                    proposal_id,
                )
            )

        st.write(
            f"{len(duplicate_rows)} "
            f"records shown."
        )

        for (
            row,
            proposal_id,
        ) in duplicate_rows:

            account_1_id = row.get(
                "account_1_id",
                ""
            )

            account_2_id = row.get(
                "account_2_id",
                ""
            )

            with st.expander(
                f"{row.get('account_1_name', '')} "
                f"↔ "
                f"{row.get('account_2_name', '')}"
            ):

                show_decision_status(
                    proposal_id
                )

                try:

                    account_1_data = (
                        get_account(
                            account_1_id
                        )
                    )

                    account_2_data = (
                        get_account(
                            account_2_id
                        )
                    )

                except Exception as error:

                    st.error(
                        f"Could not load CRM "
                        f"accounts: {error}"
                    )

                    continue

                st.write(
                    "### Duplicate evidence"
                )

                e1, e2, e3, e4 = (
                    st.columns(4)
                )

                e1.metric(
                    "Name score",
                    row.get(
                        "name_score",
                        ""
                    ),
                )

                e2.metric(
                    "Street score",
                    row.get(
                        "street_score",
                        ""
                    ),
                )

                e3.metric(
                    "ZIP",
                    row.get(
                        "zip",
                        ""
                    ),
                )

                e4.metric(
                    "Phone match",
                    row.get(
                        "phone_match",
                        ""
                    ),
                )

                left, right = (
                    st.columns(2)
                )

                with left:

                    st.subheader(
                        "Account 1"
                    )

                    st.write(
                        f"**Account ID:** "
                        f"{account_1_id}"
                    )

                    st.write(
                        f"**Name:** "
                        f"{account_1_data.get('name', '')}"
                    )

                    st.write(
                        f"**Address:** "
                        f"{account_1_data.get('billing_street', '')}"
                    )

                    st.write(
                        f"**City:** "
                        f"{account_1_data.get('billing_city', '')}"
                    )

                    st.write(
                        f"**State:** "
                        f"{account_1_data.get('billing_state', '')}"
                    )

                    st.write(
                        f"**ZIP:** "
                        f"{account_1_data.get('billing_zip', '')}"
                    )

                    st.write(
                        f"**Phone:** "
                        f"{account_1_data.get('phone', '')}"
                    )

                    st.write(
                        f"**Parent:** "
                        f"{account_1_data.get('parent_name', '')}"
                    )

                    st.write(
                        f"**Status:** "
                        f"{account_1_data.get('status', '')}"
                    )

                    st.write(
                        f"**Care type:** "
                        f"{account_1_data.get('care_type', '')}"
                    )

                    st.write(
                        f"**Lifetime revenue:** "
                        f"${account_1_data.get('lifetime_revenue', 0)}"
                    )

                    st.write(
                        f"**Outstanding AR:** "
                        f"${account_1_data.get('outstanding_ar', 0)}"
                    )

                    st.write(
                        f"**CHOW link:** "
                        f"{account_1_data.get('chow_current_account', '')}"
                    )

                with right:

                    st.subheader(
                        "Account 2"
                    )

                    st.write(
                        f"**Account ID:** "
                        f"{account_2_id}"
                    )

                    st.write(
                        f"**Name:** "
                        f"{account_2_data.get('name', '')}"
                    )

                    st.write(
                        f"**Address:** "
                        f"{account_2_data.get('billing_street', '')}"
                    )

                    st.write(
                        f"**City:** "
                        f"{account_2_data.get('billing_city', '')}"
                    )

                    st.write(
                        f"**State:** "
                        f"{account_2_data.get('billing_state', '')}"
                    )

                    st.write(
                        f"**ZIP:** "
                        f"{account_2_data.get('billing_zip', '')}"
                    )

                    st.write(
                        f"**Phone:** "
                        f"{account_2_data.get('phone', '')}"
                    )

                    st.write(
                        f"**Parent:** "
                        f"{account_2_data.get('parent_name', '')}"
                    )

                    st.write(
                        f"**Status:** "
                        f"{account_2_data.get('status', '')}"
                    )

                    st.write(
                        f"**Care type:** "
                        f"{account_2_data.get('care_type', '')}"
                    )

                    st.write(
                        f"**Lifetime revenue:** "
                        f"${account_2_data.get('lifetime_revenue', 0)}"
                    )

                    st.write(
                        f"**Outstanding AR:** "
                        f"${account_2_data.get('outstanding_ar', 0)}"
                    )

                    st.write(
                        f"**CHOW link:** "
                        f"{account_2_data.get('chow_current_account', '')}"
                    )

                status_1 = str(
                    account_1_data.get(
                        "status",
                        ""
                    )
                )

                status_2 = str(
                    account_2_data.get(
                        "status",
                        ""
                    )
                )

                if (
                    status_1 == "Active"
                    and status_2 != "Active"
                ):

                    default_survivor = (
                        account_1_id
                    )

                elif (
                    status_2 == "Active"
                    and status_1 != "Active"
                ):

                    default_survivor = (
                        account_2_id
                    )

                else:

                    default_survivor = (
                        account_1_id
                    )

                survivor_options = [
                    account_1_id,
                    account_2_id,
                ]

                default_index = (
                    survivor_options.index(
                        default_survivor
                    )
                )

                st.divider()

                survivor = (
                    st.selectbox(
                        "Surviving account",
                        survivor_options,
                        index=default_index,
                        key=(
                            f"survivor_"
                            f"{proposal_id}"
                        ),
                    )
                )

                loser = (
                    account_2_id
                    if survivor
                    == account_1_id
                    else account_1_id
                )

                survivor_data = (
                    account_1_data
                    if survivor
                    == account_1_id
                    else account_2_data
                )

                loser_data = (
                    account_2_data
                    if survivor
                    == account_1_id
                    else account_1_data
                )

                loser_revenue = (
                    to_number(
                        loser_data.get(
                            "lifetime_revenue",
                            0
                        )
                    )
                )

                loser_ar = (
                    to_number(
                        loser_data.get(
                            "outstanding_ar",
                            0
                        )
                    )
                )

                loser_chow = str(
                    loser_data.get(
                        "chow_current_account",
                        ""
                    )
                    or ""
                ).strip()

                if (
                    loser_revenue > 0
                    or loser_ar > 0
                    or loser_chow
                ):

                    st.warning(
                        "The proposed losing account "
                        "has financial history or a "
                        "CHOW link. Review carefully "
                        "before marking it duplicate."
                    )

                st.info(
                    f"Keep **{survivor}** "
                    f"({survivor_data.get('status', '')}) "
                    f"as the surviving account."
                )

                st.caption(
                    f"CRM write: set {loser} "
                    f"status = Inactive and "
                    f"duplicate_of_account = "
                    f"{survivor}."
                )

                duplicate_note = (
                    st.text_area(
                        "Reviewer note",
                        key=(
                            f"dupnote_"
                            f"{proposal_id}"
                        ),
                        placeholder=(
                            "Brief reason for "
                            "choosing the "
                            "surviving account."
                        ),
                    )
                )

                already_decided = (
                    proposal_id in decisions
                )

                c1, c2 = (
                    st.columns(2)
                )

                with c1:

                    if st.button(
                        "Approve duplicate",
                        key=(
                            f"dupapprove_"
                            f"{proposal_id}"
                        ),
                        disabled=already_decided,
                        type="primary",
                    ):

                        try:

                            latest_loser = (
                                get_account(
                                    loser
                                )
                            )

                            latest_revenue = (
                                to_number(
                                    latest_loser.get(
                                        "lifetime_revenue",
                                        0
                                    )
                                )
                            )

                            latest_ar = (
                                to_number(
                                    latest_loser.get(
                                        "outstanding_ar",
                                        0
                                    )
                                )
                            )

                            latest_chow = str(
                                latest_loser.get(
                                    "chow_current_account",
                                    ""
                                )
                                or ""
                            ).strip()

                            if (
                                latest_revenue > 0
                                or latest_ar > 0
                                or latest_chow
                            ):

                                raise ValueError(
                                    "The losing account "
                                    "now has financial "
                                    "history or a CHOW "
                                    "relationship. "
                                    "Review again."
                                )

                            payload = {
                                "duplicate_of_account":
                                    survivor,

                                "status":
                                    "Inactive",
                            }

                            result = (
                                patch_account(
                                    loser,
                                    payload,
                                )
                            )

                            decisions[
                                proposal_id
                            ] = {
                                "decision":
                                    "approved",

                                "proposal_type":
                                    "duplicate",

                                "survivor":
                                    survivor,

                                "loser":
                                    loser,

                                "review_note":
                                    duplicate_note,

                                "api_result":
                                    result,
                            }

                            save_decisions(
                                decisions
                            )

                            st.success(
                                "Duplicate marked "
                                "Inactive."
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                f"Update failed: "
                                f"{error}"
                            )

                with c2:

                    if st.button(
                        "Reject duplicate",
                        key=(
                            f"dupreject_"
                            f"{proposal_id}"
                        ),
                        disabled=already_decided,
                    ):

                        decisions[
                            proposal_id
                        ] = {
                            "decision":
                                "rejected",

                            "proposal_type":
                                "duplicate",

                            "review_note":
                                duplicate_note,
                        }

                        save_decisions(
                            decisions
                        )

                        st.rerun()


# =========================================================
# STALE BELLHAVEN
# =========================================================

with tab3:

    st.header(
        "Bellhaven Accounts Missing From Website"
    )

    st.info(
        "These accounts are currently under "
        "Bellhaven in CRM but did not match a "
        "current Bellhaven website facility."
    )

    if stale_df.empty:

        st.success(
            "No stale Bellhaven candidates."
        )

    else:

        stale_rows = []

        for _, row in stale_df.iterrows():

            account_id = row.get(
                "account_id",
                ""
            )

            proposal_id = (
                make_proposal_id(
                    "stale",
                    account_id,
                )
            )

            if (
                proposal_id in decisions
                and not show_decided
            ):
                continue

            stale_rows.append(
                (
                    row,
                    proposal_id,
                )
            )

        st.write(
            f"{len(stale_rows)} "
            f"records shown."
        )

        for (
            row,
            proposal_id,
        ) in stale_rows:

            account_id = row.get(
                "account_id",
                ""
            )

            with st.expander(
                row.get(
                    "name",
                    account_id,
                )
            ):

                show_decision_status(
                    proposal_id
                )

                st.write(
                    f"**Account ID:** "
                    f"{account_id}"
                )

                st.write(
                    f"**Location:** "
                    f"{row.get('billing_city', '')}, "
                    f"{row.get('billing_state', '')} "
                    f"{row.get('billing_zip', '')}"
                )

                st.write(
                    f"**Lifetime revenue:** "
                    f"${row.get('lifetime_revenue', '0')}"
                )

                st.write(
                    f"**Outstanding AR:** "
                    f"${row.get('outstanding_ar', '0')}"
                )

                action = (
                    st.selectbox(
                        "Final action",
                        [
                            "MARK_NEEDS_REVIEW",
                            "MARK_INACTIVE",
                            "NO_ACTION",
                        ],
                        key=(
                            f"staleaction_"
                            f"{proposal_id}"
                        ),
                    )
                )

                if action == "MARK_NEEDS_REVIEW":

                    st.caption(
                        "CRM write: "
                        "status = Needs Review."
                    )

                elif action == "MARK_INACTIVE":

                    st.caption(
                        "CRM write: "
                        "status = Inactive."
                    )

                else:

                    st.caption(
                        "CRM write: none."
                    )

                stale_note = (
                    st.text_area(
                        "Reviewer note",
                        key=(
                            f"stalenote_"
                            f"{proposal_id}"
                        ),
                    )
                )

                already_decided = (
                    proposal_id
                    in decisions
                )

                c1, c2 = (
                    st.columns(2)
                )

                with c1:

                    if st.button(
                        "Approve",
                        key=(
                            f"staleapprove_"
                            f"{proposal_id}"
                        ),
                        disabled=already_decided,
                        type="primary",
                    ):

                        try:

                            if action == "NO_ACTION":

                                result = {
                                    "message":
                                        "No CRM change."
                                }

                            elif action == "MARK_NEEDS_REVIEW":

                                result = (
                                    patch_account(
                                        account_id,
                                        {
                                            "status":
                                                "Needs Review"
                                        },
                                    )
                                )

                            elif action == "MARK_INACTIVE":

                                result = (
                                    patch_account(
                                        account_id,
                                        {
                                            "status":
                                                "Inactive"
                                        },
                                    )
                                )

                            decisions[
                                proposal_id
                            ] = {
                                "decision":
                                    "approved",

                                "proposal_type":
                                    "stale",

                                "account_id":
                                    account_id,

                                "action":
                                    action,

                                "review_note":
                                    stale_note,

                                "api_result":
                                    result,
                            }

                            save_decisions(
                                decisions
                            )

                            st.success(
                                "Decision applied."
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                f"Update failed: "
                                f"{error}"
                            )

                with c2:

                    if st.button(
                        "Reject",
                        key=(
                            f"stalereject_"
                            f"{proposal_id}"
                        ),
                        disabled=already_decided,
                    ):

                        decisions[
                            proposal_id
                        ] = {
                            "decision":
                                "rejected",

                            "proposal_type":
                                "stale",

                            "account_id":
                                account_id,

                            "review_note":
                                stale_note,
                        }

                        save_decisions(
                            decisions
                        )

                        st.rerun()


# =========================================================
# DECISION HISTORY
# =========================================================

with tab4:

    st.header(
        "Decision History"
    )

    if not decisions:

        st.info(
            "No decisions have been "
            "recorded yet."
        )

    else:

        history_rows = []

        for (
            proposal_id,
            value,
        ) in decisions.items():

            history_rows.append(
                {
                    "proposal_id":
                        proposal_id,

                    **value,
                }
            )

        history_df = (
            pd.DataFrame(
                history_rows
            )
        )

        st.dataframe(
            history_df,
            use_container_width=True,
        )

        st.download_button(
            "Download decisions.json",
            data=json.dumps(
                decisions,
                indent=2,
            ),
            file_name="decisions.json",
            mime="application/json",
        )


# =========================================================
# QUEUE SUMMARY
# =========================================================

st.sidebar.header(
    "Queue Summary"
)


def current_proposal_ids():

    proposal_ids = []

    # Facility actions
    if not match_df.empty:

        for _, row in match_df.iterrows():

            if (
                row.get(
                    "proposed_action",
                    ""
                )
                == "NO_ACTION"
            ):
                continue

            proposal_ids.append(
                make_proposal_id(
                    "match",
                    row.get(
                        "website_name",
                        ""
                    ),
                    row.get(
                        "source_url",
                        ""
                    ),
                    row.get(
                        "crm_account_id",
                        ""
                    ),
                    row.get(
                        "proposed_action",
                        ""
                    ),
                )
            )

    # Duplicates
    if not duplicate_df.empty:

        for _, row in duplicate_df.iterrows():

            proposal_ids.append(
                make_proposal_id(
                    "duplicate",
                    row.get(
                        "account_1_id",
                        ""
                    ),
                    row.get(
                        "account_2_id",
                        ""
                    ),
                )
            )

    # Stale
    if not stale_df.empty:

        for _, row in stale_df.iterrows():

            proposal_ids.append(
                make_proposal_id(
                    "stale",
                    row.get(
                        "account_id",
                        ""
                    ),
                )
            )

    return proposal_ids


current_ids = (
    current_proposal_ids()
)

current_id_set = set(
    current_ids
)

decision_id_set = set(
    decisions.keys()
)

all_proposal_ids = (
    current_id_set
    | decision_id_set
)

pending_ids = (
    current_id_set
    - decision_id_set
)

approved_ids = {
    proposal_id
    for proposal_id, value
    in decisions.items()
    if value.get(
        "decision"
    ) == "approved"
}

rejected_ids = {
    proposal_id
    for proposal_id, value
    in decisions.items()
    if value.get(
        "decision"
    ) == "rejected"
}

total_proposals = len(
    all_proposal_ids
)

active_pending = len(
    pending_ids
)

approved_total = len(
    approved_ids
)

rejected_total = len(
    rejected_ids
)

resolved_total = (
    approved_total
    + rejected_total
)


st.sidebar.metric(
    "Total proposals",
    total_proposals,
)

st.sidebar.metric(
    "Pending review",
    active_pending,
)

st.sidebar.metric(
    "Resolved",
    resolved_total,
)

st.sidebar.metric(
    "Approved",
    approved_total,
)

st.sidebar.metric(
    "Rejected",
    rejected_total,
)

st.sidebar.warning(
    "Nothing writes to the CRM until "
    "the reviewer explicitly approves it."
)