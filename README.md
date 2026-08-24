# Bellhaven CRM Reconciliation

This project was built for the Clipboard Health Analyst Assessment.

The goal is to keep the CRM aligned with Bellhaven Senior Living's current website while handling the messy situations that happen when long-term care facilities are acquired, renamed, duplicated, or moved between parent companies.

The solution does more than identify possible problems. It:

1. Collects Bellhaven's current facilities from its website.
2. Pulls the current accounts from the CRM.
3. Compares the two sources.
4. Identifies records that may need a change.
5. Shows the evidence in a review screen.
6. Requires a person to approve every CRM change.
7. Writes only approved changes back to the CRM.
8. Can be run again safely after the CRM has been corrected.

I also completed the review process and applied the changes I believed were supported by the available evidence. The final CRM state was then checked by running the full process again.

---

# 1. The Problem I Was Solving

A facility's name alone is not enough to determine whether two records represent the same place.

A facility can:

- change its name,
- be acquired by another company,
- keep the same address but have a different phone number,
- appear more than once in the CRM,
- disappear from the operator's website,
- or have billing history that must be preserved during an ownership change.

Because of this, I did not treat this as a simple name-matching exercise.

My goal was to answer two separate questions:

**Question 1: Are these records actually the same physical facility?**

Then, only after answering that:

**Question 2: If they are the same facility, what should happen to the CRM account?**

Keeping those two questions separate was important because a strong facility match does not automatically mean that changing the CRM record is safe.

---

# 2. What I Built

The project has four main Python files.

## `scraper.py`

This collects Bellhaven's current facility information from the Bellhaven website.

For each location, I collect information such as:

- facility name,
- street address,
- city,
- state,
- ZIP code,
- phone number,
- care offerings,
- and the website source page.

The output is saved in:

```text
bellhaven_locations.csv
```

This represents Bellhaven's current public facility list.

---

## `crm.py`

This pulls account information from the CRM API.

The CRM data includes information such as:

- account ID,
- facility name,
- parent company,
- address,
- city,
- state,
- ZIP,
- phone,
- status,
- care type,
- lifetime revenue,
- outstanding accounts receivable,
- duplicate links,
- and change-of-ownership links.

The output is saved in:

```text
crm_accounts.csv
```

---

## `matcher.py`

This compares every Bellhaven website facility with the CRM records.

It does not automatically modify the CRM.

Instead, it gathers evidence and recommends what should happen.

Examples include:

```text
NO_ACTION
UPDATE_NAME
REPARENT_ACCOUNT
CREATE_NEW_ACCOUNT
CREATE_CHOW_ACCOUNT
MARK_NEEDS_REVIEW
```

It also separately looks for:

- possible duplicate CRM accounts, and
- Bellhaven CRM accounts that no longer appear to correspond to the current website.

The main outputs are:

```text
match_results.csv
duplicate_candidates.csv
stale_bellhaven_accounts.csv
```

---

## `app.py`

This is the human review application.

I built it in Streamlit so the reviewer does not have to read CSV files or inspect raw API responses.

For each proposed change, the reviewer can see:

- what the Bellhaven website says,
- what the CRM currently says,
- how closely the records match,
- whether the address matches,
- whether the city/state/ZIP match,
- whether the phone matches,
- the current parent company,
- lifetime revenue,
- outstanding AR,
- and the proposed CRM action.

The reviewer can then approve or reject the proposal.

**Nothing writes to the CRM until the reviewer explicitly approves it.**

That was an intentional design choice.

---

# 3. How I Matched Facilities

I did not use one field as the answer.

Instead, I compared several pieces of information together.

The main evidence was:

- facility name,
- street address,
- city,
- state,
- ZIP code,
- phone number,
- and current parent company.

The system calculates similarity for the name and street address while also checking the exact location fields.

This matters because real CRM data is rarely perfectly formatted.

For example:

```text
1250 NW Franklin Street
```

and

```text
1250 Northwest Franklin St
```

should not be treated as two completely different facilities just because the text is written differently.

Likewise, a facility may have been renamed after an acquisition while remaining at exactly the same physical location.

---

# 4. How the Matching Score Works

The matcher creates a score from several pieces of evidence rather than relying on one field.

The current weighting is:

```text
The overall matching score is a weighted score out of 100:

Overall Score =
(Street Similarity × 30%)
+ (Name Similarity × 25%)
+ 20 if ZIP matches
+ 15 if phone matches
+ 7 if city matches
+ 3 if state matches

The final score is capped at 100.
```

The final score is capped at 100.

In simple terms, I gave the most weight to the physical location because names and phone numbers can change after an acquisition or rebrand.

For example:

- a facility name may change,
- a phone number may change,
- but the street address, city, state, and ZIP often remain the strongest evidence that the physical facility is the same.

---

## Name Matching

Facility names are cleaned before comparison.

For example:

```text
Health Care
```

and

```text
Healthcare
```

are treated more consistently.

I also normalize common differences such as:

```text
Centre → Center
Rehabilitation → Rehab
```

The name score uses fuzzy matching so small wording differences do not automatically break a match.

---

## Address Matching

Street addresses are normalized before comparison.

Examples:

```text
Street → St
Avenue → Ave
Road → Rd
Drive → Dr
Lane → Ln
North → N
South → S
East → E
West → W
```

This allows addresses such as:

```text
1250 Northwest Franklin Street
```

and:

```text
1250 NW Franklin St
```

to be treated as the same location.

---

## Phone Matching

Phone numbers are compared after removing formatting.

For example:

```text
(614) 555-1234
614-555-1234
+1 614 555 1234
```

all become:

```text
6145551234
```

This prevents formatting differences from creating a false mismatch.

Phone is useful evidence, but I did not make it the deciding field because facility phone numbers can change.

---

## ZIP Matching

ZIP codes are normalized to the first five digits.

For example:

```text
45840
45840.0
45840-1234
```

are treated consistently as:

```text
45840
```

An exact ZIP match adds strong support to the overall score.

---

## Confidence Rules

I did not rely only on the final numeric score.

A record can also be treated as a confident match when certain strong combinations of evidence are present.

The current rules consider a match confident when any of the following is true:

```text
Exact ZIP + street score >= 90
```

or:

```text
Phone match + ZIP match
```

or:

```text
Phone match + name score >= 80
```

or:

```text
Street score >= 90 + name score >= 80
```

or:

```text
Overall score >= 75
```

This means a facility does not need every field to match perfectly.

For example, a phone number can differ while the exact address, city, state, and ZIP still provide strong evidence that the records represent the same physical facility.

---

## Ambiguous Matches

I also compare the best CRM candidate with the second-best candidate.

If the best match is confident but the score difference between the top two candidates is less than:

```text
8 points
```

the result is marked:

```text
Ambiguous = True
```

This does not automatically reject the match.

Instead, it tells the reviewer that another CRM account is almost as plausible and deserves closer inspection.

This is what happened in the Kettering case.

The top two CRM candidates were very close, and both represented records at the same physical address.

Because the available evidence could not safely distinguish them, I chose `Needs Review` rather than forcing a parent change.

---

## Matching Score vs Business Action

The matching score answers:

> How likely is it that these two records represent the same physical facility?

It does **not** answer:

> What should happen to the CRM account?

That decision is made separately.

For example, once a confident match is found:

- correct parent + correct name → `NO_ACTION`
- correct parent + outdated name → `UPDATE_NAME`
- wrong parent + safe financial condition → `REPARENT_ACCOUNT`
- wrong parent + revenue history + outstanding AR → `CREATE_CHOW_ACCOUNT`

This separation was important because identifying the facility correctly and deciding how to update the CRM are two different business questions.

# 5. Why I Did Not Trust Names Alone

Names were useful evidence, but they were not enough by themselves.

For example, I found cases where the CRM had an older facility name while the Bellhaven website showed a Bellhaven-branded name.

If the following matched:

- street address,
- city,
- state,
- ZIP,

and the other evidence was reasonable, that was much stronger evidence that the two records represented the same physical facility.

This allowed the system to identify rebranding situations rather than incorrectly creating a second account.

At the same time, I did not assume that similar names meant the records were the same.

If the address, city, ZIP and phone were different, I treated that as evidence that the CRM candidate could simply be a different facility.

---

# 6. Main Types of Decisions

## No Action

If the website facility already matched the correct CRM account and no correction was necessary, the result was:

```text
NO_ACTION
```

This is especially important for repeat runs. Once a problem has been fixed, the system should recognize the corrected CRM state instead of proposing the same change again.

---

## Update Name

Sometimes the physical facility clearly matched, but the CRM still contained an older name.

In that case, I updated only the name.

For example, a record could have:

- the same address,
- the same city,
- the same state,
- the same ZIP,
- the correct Bellhaven parent,

but an outdated facility name.

That is a naming problem, not a reason to create another facility account.

---

## Re-parent Existing Account

Sometimes the facility matched, but the CRM showed the wrong parent company.

Before changing the parent, I checked the account's financial history.

If it was safe according to the assessment rules, I changed only the parent relationship instead of creating an unnecessary duplicate account.

---

## Create a New Account

If the Bellhaven website contained a facility but the CRM did not contain a convincing corresponding account, I created a new Bellhaven facility account.

I did not force a weak CRM candidate to become a match simply because it had the highest score.

For example, two facilities might have a somewhat similar name because they are both Bellhaven locations, while having completely different:

- addresses,
- cities,
- ZIP codes,
- and phone numbers.

That is not enough evidence to treat them as the same facility.

---

## Needs Review

Some situations did not contain enough information to safely choose an account.

In those cases, I deliberately used:

```text
Needs Review
```

rather than making an unsupported assumption.

This is important because the goal is not to maximize the number of automatic changes. The goal is to improve CRM accuracy without damaging good data.

---

# 7. The Kettering Case: Why I Chose Needs Review

One of the most useful ambiguous cases was Bellhaven of Kettering.

The Bellhaven website showed:

```text
Bellhaven of Kettering
3313 Wilmington Pike
Kettering, OH 45429
```

The CRM contained more than one account at that same physical address.

One candidate was:

```text
Kettering Care Centre
3313 Wilmington Pike
```

Another was:

```text
Kettering Nursing & Rehabilitation
3313 Wilmington Pike
```

The website phone did not resolve the ambiguity.

Both CRM records also had no financial history that helped establish which one represented the current facility.

There was therefore not enough evidence to confidently decide which CRM account should be moved or renamed.

Instead of forcing an ownership change, I marked the relevant account:

```text
Needs Review
```

My reasoning was simple:

> Two CRM accounts share the same address, and neither phone matches the website. No other evidence confirms which account is correct, so more information is needed before making an ownership change.

I consider this an intentional outcome, not an unresolved system error.

In a real business process, I would want additional evidence such as an acquisition date, state license information, corporate ownership documentation, or another trusted source before changing this record.

---

# 8. Change of Ownership (CHOW)

This was one of the most important business rules in the assessment.

Changing a facility's parent is not always just a normal CRM update.

Before changing the parent company, I check:

```text
lifetime_revenue
outstanding_ar
```

The rule I implemented is:

### If the account does NOT have both revenue history and outstanding AR

The existing account can be moved directly to the correct parent.

### If the account DOES have revenue history AND outstanding AR greater than zero

I do **not** change the parent of the old account.

Instead:

1. Preserve the old account.
2. Create a new account for the current Bellhaven facility.
3. Put the new account under Bellhaven.
4. Set `chow_current_account` on the old account to the new account's ID.

This preserves the historical billing relationship.

---

# 9. Examples of CHOW Decisions

Two examples in my data were Bellhaven of Marietta and Bellhaven of Tiffin.

Both had strong evidence connecting the website facility to an existing CRM account.

However, those CRM accounts belonged to the previous parent and also contained both:

- revenue history, and
- outstanding AR.

Therefore, directly changing their parent would have violated the required billing rule.

For those cases I preserved the historical account and created a new Bellhaven account.

The old and new accounts are connected through:

```text
chow_current_account
```

This also matters for duplicate detection. The old and new CHOW accounts may have the same facility name and address, but they are **not accidental duplicates**. They represent different ownership/billing periods.

---

# 10. Duplicate Detection

I also checked the CRM for records that appear to represent the same facility more than once.

A possible duplicate is evaluated using evidence such as:

- name,
- street address,
- ZIP,
- phone,
- parent,
- status,
- revenue,
- outstanding AR,
- and CHOW relationships.

Before proposing a duplicate, the system excludes known CHOW-linked historical/current pairs.

It also avoids proposing accounts that have already been resolved through:

```text
duplicate_of_account
```

For a confirmed duplicate:

1. One account is selected as the surviving account.
2. The other account is marked `Inactive`.
3. The losing account's `duplicate_of_account` field points to the survivor.

---

# 11. Owosso Duplicate Example

The CRM contained two records for Bellhaven of Owosso.

Both had:

- the same facility name,
- the same address,
- the same city,
- the same state,
- the same ZIP,
- the same parent,
- and the same care type.

One account was Active and the other was already Inactive.

I kept the Active account as the survivor and linked the Inactive account to it using:

```text
duplicate_of_account
```

After this decision was applied, the duplicate finder no longer proposed the pair on the next run.

---

# 12. Bellhaven Accounts Missing From the Website

I also looked in the opposite direction.

Instead of asking only:

> Which CRM account matches this website facility?

I also asked:

> Which CRM accounts currently sit under Bellhaven but do not correspond to a current Bellhaven website facility?

These records were placed in a separate review section.

I did not automatically mark them Inactive.

A facility disappearing from a website is evidence that something may have changed, but it is not enough by itself to prove exactly what happened.

For uncertain cases I used:

```text
Needs Review
```

If an account also had revenue or outstanding AR, I treated that as another reason to avoid making an aggressive automatic change.

---

# 13. Human Review and Safety

The review application is intentionally the only place where proposed changes become CRM writes.

The automated part of the system can identify:

> "This looks like a name update."

or:

> "This account appears to belong under Bellhaven."

But it does not automatically make that decision final.

The reviewer sees the supporting evidence and chooses what to do.

This gives the workflow a simple separation:

```text
Automation finds the issue
        ↓
System explains the evidence
        ↓
Human reviews the proposal
        ↓
Human approves or rejects
        ↓
Only approved changes reach CRM
```

This was particularly important for ownership changes, duplicates, and ambiguous records.

---

# 14. Reviewer Notes and Decision History

Each reviewed proposal can include a short explanation of why the decision was made.

The decisions are stored in:

```text
decisions.json
```

This provides an audit trail showing:

- what was proposed,
- whether it was approved or rejected,
- what final action was selected,
- which CRM account was affected,
- the reviewer's explanation,
- and the API result.

This also made it easier to verify what had already been reviewed.

---

# 15. Safe Re-runs

A major requirement was that running the process again should be safe.

I approached this by making the matcher evaluate the **current CRM state** every time it runs.

For example:

### Before correction

A facility might produce:

```text
REPARENT_ACCOUNT
```

After the reviewer approves that change, the CRM now contains the correct parent.

### Next run

The matcher retrieves the CRM again.

It now sees that the parent is already correct, so the previous issue should become:

```text
NO_ACTION
```

The same idea applies to:

- name updates,
- new accounts,
- duplicates,
- CHOW relationships,
- stale records,
- and Needs Review records.

The system is therefore checking what is true **now**, rather than simply repeating yesterday's proposal.

---

# 16. An Important Re-run Detail

During testing, one facility demonstrated why the proposal history also needed to distinguish between different kinds of changes.

Bellhaven of Zanesville initially needed its parent corrected.

After that was approved and the pipeline was rerun, the ownership problem was gone.

The latest CRM state then revealed a second, separate issue: the facility still had its old Cedar Trail name.

That new issue needed to appear as a new proposal rather than being hidden because the same facility had already been reviewed once.

For that reason, the proposal identity includes the proposed action.

This means:

```text
Zanesville → REPARENT_ACCOUNT
```

and:

```text
Zanesville → UPDATE_NAME
```

are treated as two separate review decisions.

This allows the system to respond correctly as the CRM changes over time.

---

# 17. Final CRM Reconciliation

I did not stop after generating proposals.

I reviewed the proposed changes in the application and approved the changes that I believed were supported by the evidence.

I then fetched the updated CRM again and reran the complete matching process.

The final result was:

```text
Website facilities: 35

MATCH_CORRECT: 34
MATCH_ALREADY_NEEDS_REVIEW: 1

Proposed actions:
NO_ACTION: 35

Possible CRM duplicates: 0

Bellhaven CRM accounts not matched
to current website: 0
```

The one `MATCH_ALREADY_NEEDS_REVIEW` record is the intentionally unresolved Kettering case described above.

Because it is already marked for additional review, the matcher correctly produces:

```text
NO_ACTION
```

instead of repeatedly asking a reviewer to make the same uncertain decision.

The final pipeline therefore produces no new CRM changes.

---

# 18. Project Files

```text
clipboard-task-crm/
│
├── scraper.py
├── crm.py
├── matcher.py
├── app.py
│
├── bellhaven_locations.csv
├── crm_accounts.csv
├── match_results.csv
├── duplicate_candidates.csv
├── stale_bellhaven_accounts.csv
│
├── decisions.json
├── requirements.txt
├── .env.example
├── .gitignore
│
└── .github/
    └── workflows/
        └── daily.yml
```

### Main code

` scraper.py `  
Collects the current Bellhaven website locations.

` crm.py `  
Retrieves the latest CRM accounts.

` matcher.py `  
Compares the website and CRM and creates review proposals.

` app.py `  
Provides the human review interface and performs approved CRM writes.

### Generated data

` bellhaven_locations.csv `  
Latest Bellhaven website facilities.

` crm_accounts.csv `  
Latest CRM snapshot.

` match_results.csv `  
Website-to-CRM matching results.

` duplicate_candidates.csv `  
Possible duplicate accounts requiring review.

` stale_bellhaven_accounts.csv `  
Bellhaven CRM records that do not correspond to the current website list.

### Review history

` decisions.json `  
Record of the decisions made during human review.

---

# 19. Running the Project Locally

## Step 1 — Install Python packages

From the project folder:

```bash
pip install -r requirements.txt
```

---

## Step 2 — Add the CRM token

Create a file named:

```text
.env
```

in the project folder.

Add:

```text
CLIPBOARD_API_TOKEN=your_token_here
```

The real `.env` file is excluded from Git so the API token is not published.

`.env.example` shows the expected format without containing the real token.

---

## Step 3 — Collect the website data

```bash
python scraper.py
```

This creates/refreshes:

```text
bellhaven_locations.csv
```

---

## Step 4 — Retrieve the latest CRM data

```bash
python crm.py
```

This creates/refreshes:

```text
crm_accounts.csv
```

---

## Step 5 — Run the matching process

```bash
python matcher.py
```

This refreshes the review files:

```text
match_results.csv
duplicate_candidates.csv
stale_bellhaven_accounts.csv
```

---

## Step 6 — Open the review application

```bash
streamlit run app.py
```

The reviewer can then inspect proposed changes and approve or reject them.

Approved changes are sent to the CRM API.

---

## Step 7 — Verify the result

After making approved changes, rerun:

```bash
python crm.py
python matcher.py
```

This checks the new CRM state.

A resolved problem should no longer be proposed.

---

# 20. Daily Run Design

The assessment asks for the system to be designed to run daily.

I included:

```text
.github/workflows/daily.yml
```

as an example schedule.

The daily automated portion runs:

```text
Bellhaven website                 CRM API
       ↓                            ↓
   scraper.py                    crm.py
       ↓                            ↓
bellhaven_locations.csv      crm_accounts.csv
             \                  /
              \                /
                 matcher.py
                     ↓
              Review proposals
                     ↓
              Human review
```

The scheduled process intentionally stops before approval.

`app.py` remains the human decision layer.

This means a daily run can identify a new ownership or data-quality issue without automatically making a potentially harmful CRM change.

The GitHub Actions file is included as the schedule configuration requested by the assessment. The application itself does not need to be hosted.

---

# 21. How I Used AI

I used ChatGPT throughout the assessment as a thinking, development, and review partner.

I did not use an LLM to make the actual matching decisions inside the pipeline.

Instead, I used AI to help me work through the problem more carefully.

Examples include:

- discussing how to compare messy facility names and addresses,
- thinking through acquisition and rebranding scenarios,
- checking whether a proposed CRM action was supported by the evidence,
- working through the required CHOW rule,
- reviewing ambiguous cases such as Kettering,
- debugging Python and Streamlit issues,
- improving duplicate handling,
- checking repeat-run behavior,
- and reviewing whether the final workflow could accidentally make an unsafe CRM change.

I treated AI suggestions as suggestions rather than ground truth.

When the available CRM and website evidence did not support a confident conclusion, I chose to leave the record for additional review instead of using AI to guess.

I also used repeated runs of the actual CRM data to validate whether the logic behaved as intended.

---

# 22. What I Would Build Next

Given more time, I would focus on making the workflow easier to operate and giving reviewers better evidence rather than simply making the matching algorithm more aggressive.

## Better ownership history

The hardest cases are not necessarily low matching scores.

They are cases where multiple CRM records could legitimately represent the same physical facility at different points in time.

I would add trusted ownership information such as:

- acquisition dates,
- ownership effective dates,
- state licensing records,
- corporate announcements,
- or internal ownership history.

That would help resolve cases like Kettering without guessing.

---

## Better decision storage

For this assessment, reviewer decisions are stored in:

```text
decisions.json
```

For a production system, I would store decisions in a database or audit table.

That would make it easier to track:

- who reviewed a proposal,
- when it was reviewed,
- what the CRM looked like at the time,
- what evidence supported the decision,
- and what changed afterward.

---

## Notifications for new issues

A daily process should not require someone to manually check the application every day just to find out whether anything changed.

I would add a notification when new review items appear.

For example:

> 3 new Bellhaven CRM changes require review.

The reviewer could then open the application only when something actually needs attention.

---

## Tests for important business rules

I would add automated checks for the most important rules, especially:

- CHOW behavior,
- direct re-parenting,
- duplicate handling,
- already-resolved duplicates,
- Needs Review behavior,
- new account creation,
- name changes,
- and repeat runs.

This would make future changes to the matching logic safer.

---

## More explanation for matching scores

The current review application already shows the individual pieces of evidence.

I would go further and summarize the reasoning in plain language.

For example:

> Same address, city, state and ZIP. Name changed. Phone differs. Account is already under Bellhaven.

That is more useful to a reviewer than a score alone.

---

# 23. Design Principle

The main principle behind this solution is:

> **Automate the investigation, not the judgment when the evidence is uncertain.**

The system handles the repetitive work:

- collecting facility data,
- pulling CRM accounts,
- comparing records,
- finding likely problems,
- checking financial history,
- and organizing the evidence.

The reviewer handles the business decision when judgment is required.

This allowed me to correct the CRM while still preserving uncertain records, billing history, and an audit trail of the decisions that were made.
