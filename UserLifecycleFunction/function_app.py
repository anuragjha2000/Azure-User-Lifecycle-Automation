import azure.functions as func
import logging
import json
import os
import requests
from msal import ConfidentialClientApplication

app = func.FunctionApp()

TENANT_ID = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


def get_graph_token():
    msal_app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    result = msal_app.acquire_token_for_client(scopes=GRAPH_SCOPE)
    if "access_token" not in result:
        raise Exception(f"Token acquisition failed: {result.get('error_description')}")
    return result["access_token"]


@app.route(route="onboard", auth_level=func.AuthLevel.FUNCTION)
def onboard(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Onboard function triggered.")

    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid or missing JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    required_fields = ["displayName", "mailNickname", "userPrincipalName"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return func.HttpResponse(
            json.dumps({"error": f"Missing required fields: {missing}"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        token = get_graph_token()
    except Exception as e:
        logging.error(f"Token acquisition failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to authenticate with Microsoft Graph"}),
            status_code=500,
            mimetype="application/json"
        )

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    user_payload = {
        "accountEnabled": True,
        "displayName": data["displayName"],
        "mailNickname": data["mailNickname"],
        "userPrincipalName": data["userPrincipalName"],
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": "TempPassword@123"
        }
    }

    resp = requests.post(
        "https://graph.microsoft.com/v1.0/users",
        headers=headers,
        json=user_payload
    )

    if resp.status_code != 201:
        logging.error(f"Graph user creation failed: {resp.text}")
        return func.HttpResponse(resp.text, status_code=resp.status_code, mimetype="application/json")

    created_user = resp.json()
    user_id = created_user["id"]
    logging.info(f"User created: {user_id}")

    group_id = data.get("groupId")
    group_result = None
    if group_id:
        group_resp = requests.post(
            f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref",
            headers=headers,
            json={"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"}
        )
        group_result = "added" if group_resp.status_code == 204 else group_resp.text

    return func.HttpResponse(
        json.dumps({
            "status": "created",
            "userId": user_id,
            "userPrincipalName": created_user["userPrincipalName"],
            "groupAssignment": group_result
        }),
        status_code=201,
        mimetype="application/json"
    )


@app.route(route="offboard", auth_level=func.AuthLevel.FUNCTION)
def offboard(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Offboard function triggered.")

    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid or missing JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    user_id = data.get("userId") or data.get("userPrincipalName")
    if not user_id:
        return func.HttpResponse(
            json.dumps({"error": "Provide userId or userPrincipalName"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        token = get_graph_token()
    except Exception as e:
        logging.error(f"Token acquisition failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to authenticate with Microsoft Graph"}),
            status_code=500,
            mimetype="application/json"
        )

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    disable_resp = requests.patch(
        f"https://graph.microsoft.com/v1.0/users/{user_id}",
        headers=headers,
        json={"accountEnabled": False}
    )

    if disable_resp.status_code != 204:
        logging.error(f"Graph disable failed: {disable_resp.text}")
        return func.HttpResponse(disable_resp.text, status_code=disable_resp.status_code, mimetype="application/json")

    revoke_resp = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{user_id}/revokeSignInSessions",
        headers=headers
    )

    return func.HttpResponse(
        json.dumps({
            "status": "disabled",
            "userId": user_id,
            "sessionsRevoked": revoke_resp.status_code == 200
        }),
        status_code=200,
        mimetype="application/json"
    )