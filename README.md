# 🔄 Azure User Lifecycle Automation (JML Automation with Microsoft Graph)

Automates the Joiner–Mover–Leaver (JML) process in Microsoft Entra ID using
Azure Functions, Microsoft Graph API, Terraform, and GitHub Actions.

## 📌 Overview

This project simulates a real-world enterprise IAM workflow: when a user joins,
changes role, or leaves an organization, this automation handles account
provisioning, group/RBAC assignment, and deprovisioning — without manual
intervention. It mirrors the Joiner-Mover-Leaver lifecycle used by enterprise
IAM platforms like SailPoint and Okta, but built entirely on Azure-native tooling.

**What it does:**
- **Joiner** — Creates the user in Entra ID via Microsoft Graph, optionally assigns
  to a security group.
- **Leaver** — Disables the account and revokes all active sign-in sessions.
- *(Mover — role/group reassignment — is a planned extension, see Future Enhancements.)*

## 🏗️ Architecture

```
 [Trigger Source]              [Automation Layer]              [Identity Layer]
 HTTP request        ────▶   Azure Function (Python)   ────▶  Microsoft Graph API
 (simulated HR event)         Consumption Plan                 (Entra ID)
                                    │                                │
                                    ▼                                ▼
                             Azure Key Vault                  Security Groups /
                             (RBAC-authorized,                App Role Assignments
                              Managed Identity access)
                                    │
                                    ▼
                          Azure Monitor / Log Analytics
                          (FunctionAppLogs, audit trail via KQL)
```

| Layer | Tool |
|---|---|
| Identity | Microsoft Entra ID, Microsoft Graph API |
| Compute | Azure Functions (Python 3.10, v2 programming model) |
| Secrets | Azure Key Vault (RBAC authorization) |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Monitoring | Azure Monitor + Log Analytics Workspace (KQL) |

## ⚙️ Tech Stack

`Azure Functions` `Microsoft Graph API` `Entra ID` `Terraform` `Key Vault`
`GitHub Actions` `Azure Monitor` `Python` `MSAL`

## 🚀 Features

- ✅ Automated user onboarding (account creation + group assignment) via Microsoft Graph API
- ✅ Automated offboarding (account disable + session revocation)
- ✅ Secrets managed via Key Vault + Managed Identity — zero hardcoded credentials
- ✅ Infrastructure fully defined as code (Terraform), imported and reconciled to zero drift
- ✅ CI/CD pipeline via GitHub Actions — auto-deploys on push, verified working end-to-end
- ✅ Centralized audit logging via Log Analytics, queried with KQL

## 📂 Project Structure

```
├── terraform/              # Infrastructure as Code (Resource Group, Storage,
│                              Function App, Log Analytics, Key Vault, RBAC)
├── UserLifecycleFunction/  # Azure Function source (function_app.py, v2 model)
├── .github/workflows/      # CI/CD pipeline (deploy.yml)
├── docs/screenshots/       # Evidence screenshots (see below)
└── README.md
```

## 🖥️ Setup & Deployment

1. Clone the repo
2. Register an app in Entra ID (App registrations → New registration), grant
   Microsoft Graph **Application permissions**: `User.ReadWrite.All`,
   `Group.ReadWrite.All`, `Directory.ReadWrite.All`, then **Grant admin consent**
3. Configure Terraform variables (subscription, tenant, resource names)
4. `terraform init && terraform plan && terraform apply`
5. Store the app's client secret in Key Vault, and as a Function App setting
6. Deploy the function: `func azure functionapp publish <app-name>` (or just
   push to `master` — GitHub Actions handles it automatically)
7. Trigger via HTTP request using the Function's host key:
   ```bash
   curl -X POST "https://<your-app>.azurewebsites.net/api/onboard?code=<function-key>" \
     -H "Content-Type: application/json" \
     -d '{"displayName": "Jane Doe", "mailNickname": "jdoe", "userPrincipalName": "jdoe@yourtenant.onmicrosoft.com"}'
   ```

## 📸 Screenshots

**App Registration — API Permissions (Admin Consent Granted)**
![API Permissions](https://github.com/anuragjha2000/Azure-User-Lifecycle-Automation/blob/master/api-permissions.png)

**Terraform Apply — All Resources Provisioned, Zero Drift**
![Terraform Resources](https://github.com/anuragjha2000/Azure-User-Lifecycle-Automation/blob/master/terraform-apply-resources.png)

**Offboarding Verified in Entra ID Portal**
![Offboard Success](https://github.com/anuragjha2000/Azure-User-Lifecycle-Automation/blob/master/offboard-success-portal.png)

**GitHub Actions CI/CD — Successful Deployment**
![GitHub Actions Success](https://github.com/anuragjha2000/Azure-User-Lifecycle-Automation/blob/master/github-actions-success.png)

**Offboard Test + Diagnostic Settings Creation (Cloud Shell)**
![Offboard and Diagnostics CLI](https://github.com/anuragjha2000/Azure-User-Lifecycle-Automation/blob/master/offboard-and-diagnostics-cli.png)

**Log Analytics — KQL Audit Trail Query (Onboard/Offboard Events)**
![Log Analytics Audit Query](https://github.com/anuragjha2000/Azure-User-Lifecycle-Automation/blob/master/log-analytics-audit-query.png)

## 🐛 Troubleshooting Log (Real Issues Hit & Fixed)

Documenting these because working through them *is* the IAM/cloud engineering
experience — not just the happy path:

- **Key Vault `MissingSubscriptionRegistration`** → resource provider wasn't
  registered on a fresh subscription; fixed with `az provider register --namespace Microsoft.KeyVault`.
- **Key Vault RBAC `Forbidden` on secret set** → newer vaults default to Azure
  RBAC instead of legacy access policies; fixed by assigning `Key Vault Secrets Officer`
  to my own account and `Key Vault Secrets User` to the Function App's Managed Identity.
- **Cloud Shell losing all files between sessions** → default `~` isn't persistent
  unless backed by a mounted Azure Files share; fixed by provisioning Cloud Shell
  persistent storage and rebuilding inside `~/clouddrive`.
- **Graph API `Authorization_RequestDenied` despite "Admin consent: Yes"** → the
  portal's consent button showed success but never actually created the App Role
  Assignments on the service principal (confirmed via `GET .../appRoleAssignments`
  returning an empty array). Fixed by creating the three role assignments directly
  via Graph API POST calls, bypassing the portal.
- **`AADSTS7000215: Invalid client secret`** → was reusing a secret's *Secret ID*
  (a GUID) instead of its actual *Value*; also had a rotated secret that no longer
  matched. Fixed by generating a clean secret and using the Value field exactly.
- **Python venv silently failing on Cloud Shell's mounted storage** → `.venv/bin`
  never got created because network file shares don't support the symlinks venvs
  rely on. Fixed by creating the venv on local ephemeral storage (`~`) instead of
  the persistent mount, and only keeping source code on the persistent drive.
- **Log Analytics ingestion delay** → `FunctionAppLogs` took ~15-20 minutes to
  start appearing after the diagnostic setting was created, even though `AzureMetrics`
  arrived immediately — normal Consumption-plan cold-start behavior for the logging
  pipeline, not a misconfiguration.
- **401 Unauthorized on live deployed endpoint** → function key was pasted with
  literal `<` `>` placeholder brackets left in by mistake; fixed by copying the
  raw value cleanly from the portal's "App keys" blade.

## 🧠 Key Concepts & Technologies Used

**Joiner-Mover-Leaver (JML) lifecycle** — the standard IAM model for an
identity's lifecycle events; this project automates the Joiner and Leaver halves
in code, the same concept underpinning enterprise tools like SailPoint and Okta.

**App Registration & Service Principal** — registering an app with Entra ID
creates both an App Registration (the definition) and a Service Principal (the
actual identity object permissions attach to) — a distinction that mattered when
debugging why granted permissions weren't taking effect.

**OAuth2 Client Credentials Flow (via MSAL)** — since the Function runs
unattended, it authenticates as itself (Client ID + Secret) rather than as a
signed-in user, using Microsoft's MSAL library to acquire Graph API tokens.

**Application vs Delegated Permissions & App Role Assignments** — Application
permissions let the app act with standing rights of its own; granting one
requires admin consent, which should create an App Role Assignment linking the
service principal to the permission — a step that failed silently in this
project and had to be fixed manually via Graph API.

**Azure Key Vault RBAC** — newer vaults require explicit role assignments
(`Key Vault Secrets Officer` / `Key Vault Secrets User`) rather than legacy
access policies, even for the vault owner.

**Managed Identity** — lets the Function App authenticate to Key Vault without
any stored credentials, using an identity Azure manages automatically.

**Terraform / IaC** — declarative infrastructure, including recovering from a
lost local Terraform state by using `terraform import` to reattach existing
Azure resources without recreating them.

**Azure Functions (Consumption Plan, Python v2 model)** — serverless, billed
only for execution time; the v2 model defines all functions via decorators in a
single `function_app.py`.

**GitHub Actions CI/CD** — automated deployment via a workflow triggered on push,
authenticating to Azure using an encrypted publish-profile secret.

**Log Analytics & KQL** — querying Function execution logs for an audit trail
of onboarding/offboarding events.

## 🔮 Future Enhancements

- Mover support: detect department/role changes and reassign group membership
- Manager approval step via Logic Apps before offboarding
- Teams/email notification via Graph `sendMail` on each lifecycle event
- CSV/Blob-triggered bulk onboarding to simulate a real HR feed

## 📄 License

MIT License
https://github.com/anuragjha2000/Azure-User-Lifecycle-Automation/blob/master/LICENSE
