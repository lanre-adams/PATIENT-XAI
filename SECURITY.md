# Security policy

PATIENT-XAI is a research demonstrator that processes **synthetic data only**. It must not be deployed
with real patient data in its current form.

## If you were to adapt it for real data (do not do this without governance approval)
- Real health data require an approved ethics application, a data-processing agreement, a DPIA and
  storage in an approved trusted research environment. None of that exists for this project.
- The API has **no authentication or authorisation**; CORS is restricted to localhost by default.
- The audit log stores prediction metadata in the database; it is not tamper-evident.
- The container runs as a non-root user; there are no secrets to manage.

## Reporting a vulnerability
Please open a private security advisory on the GitHub repository, or email the maintainer
at lanreadams88@gmail.com with "PATIENT-XAI security" in the subject. Do not include real patient data in any report.
