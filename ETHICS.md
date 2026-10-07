# Ethics statement

## What this project is
A pre-application research demonstrator built on **synthetic** data. It involves no human participants,
no patient records and no personal data, so no ethics approval was required or sought.

## Safeguards built in
- Every UI screen shows a "research demonstrator — not a medical device" notice; every API response carries
  an `X-Research-Demonstrator` header; reports repeat the notice.
- The Explanation Engine is deterministic and template-based. Automated tests fail if any output contains
  treatment-advice phrasing, and they check that prediction, association, uncertainty, counterfactual
  simulation and causality are presented separately.
- Counterfactual results always carry the caveat: *"Counterfactual scenarios represent model-based simulations
  and do not establish that modifying a variable will causally produce the predicted clinical outcome."*
- Simulator ground truth is shown next to model-based simulations to make the prediction/causation gap visible.
- Subgroup metrics (sex) are reported, and requests that produce predictions or reports are logged with the model version.

## What a real-data PhD project would additionally need
Research ethics approval; data-access agreements with the custodian (e.g. NHS trust, UK Biobank, a Nigerian
programme data owner); a DPIA under UK GDPR; a trusted research environment; patient and public involvement
in the design of explanations; clinical co-supervision; pre-registered evaluation; and a pathway that respects
UK MHRA software-as-a-medical-device rules **before** any prospective use.
