"""Orbyte platform adapter (mocked, spec §11).

Responses copy the shapes of Orbyte's own endpoints so GreenReady can be
dropped into the Orbyte shell without translation:

  /api/menus                  -> menus_for()       {id, parentId, menuType, menuName, icon, url, status, appId}
  /api/dashboard/action-items -> action_items()    {itemType, module, actionType, status, title, webPath, ...}
  /api/wallet                 -> wallet()          {walletId, balance, status}
  /api/wallet/transactions    -> wallet_transactions()
"""

from typing import Any, Dict, List

from marketplace.store import BoardStore

GREENREADY_APP_ID = 7
ORGANIZATION = {"id": 128, "name": "Kilang Contoh Sdn Bhd"}
WALLET_ID = 9
LOW_BALANCE_MYR = 4.0

# (menuName, Tabler icon, url) per role, rendered under one "GreenReady" category.
_ROLE_MENUS = {
    "sme_owner": [
        ("Bills", "tabler-receipt", "/sme/bills"),
        ("My listing", "tabler-layout-board", "/sme/listing"),
        ("Requests", "tabler-inbox", "/sme/requests"),
        ("Activity", "tabler-history", "/sme/activity"),
        ("Wallet", "tabler-wallet", "/sme/wallet"),
    ],
    "sme_staff": [
        ("Bills", "tabler-receipt", "/sme/bills"),
        ("My listing", "tabler-layout-board", "/sme/listing"),
        ("Requests", "tabler-inbox", "/sme/requests"),
        ("Activity", "tabler-history", "/sme/activity"),
    ],
    "investor": [
        ("Opportunity Board", "tabler-layout-grid", "/investor/board"),
        ("Connections", "tabler-plug-connected", "/investor/connections"),
        ("Billing", "tabler-file-invoice", "/investor/billing"),
    ],
    "supplier": [
        ("Opportunity Board", "tabler-layout-grid", "/supplier/board"),
        ("My requests", "tabler-send", "/supplier/requests"),
        ("Accepted leads", "tabler-user-check", "/supplier/leads"),
        ("Billing", "tabler-file-invoice", "/supplier/billing"),
    ],
    "ops": [
        ("Audit log", "tabler-list-search", "/ops/audit"),
    ],
}


def menus_for(role: str) -> Dict[str, Any]:
    category = {
        "id": 900, "parentId": 0, "menuType": "Category", "menuName": "GreenReady",
        "icon": "tabler-leaf", "url": "", "status": "Active", "appId": GREENREADY_APP_ID,
    }
    items = [
        {
            "id": 901 + index, "parentId": category["id"], "menuType": "Menu", "menuName": name,
            "icon": icon, "url": url, "status": "Active", "appId": GREENREADY_APP_ID,
        }
        for index, (name, icon, url) in enumerate(_ROLE_MENUS.get(role, []))
    ]
    data = [category] + items
    return {
        "success": True,
        "message": "Menus retrieved successfully",
        "data": data,
        "meta": {"page": 1, "limit": len(data), "total": len(data), "totalPages": 1},
    }


def action_items(store: BoardStore, role: str) -> Dict[str, Any]:
    """Pending GreenReady approvals, in the shape of Orbyte's dashboard action items."""
    items: List[Dict[str, Any]] = []
    if role in {"sme_owner", "sme_staff"}:
        for request in store.requests.values():
            partner = store.partners[request["partner_id"]]
            if request["status"] == "requested":
                items.append({
                    "id": f"greenready-{request['id']}",
                    "itemType": "Approval",
                    "module": "GreenReady",
                    "actionType": "Approve",
                    "status": "PendingApproval",
                    "reason": "ConnectionRequest",
                    "title": f"{partner['name']} wants to connect on {request['listing_id']}",
                    "requestedBy": partner["name"],
                    "dueAt": None,
                    "webPath": f"/sme/requests?open={request['id']}",
                    "organizationId": ORGANIZATION["id"],
                    "organizationName": ORGANIZATION["name"],
                    "isCurrentOrganization": True,
                })
            for document_id in request["document_ids"]:
                document = store.documents[document_id]
                if document["type"] == "eoi" and document["status"] == "sent":
                    items.append({
                        "id": f"greenready-{document_id}",
                        "itemType": "Review",
                        "module": "GreenReady",
                        "actionType": "Review",
                        "status": "PendingReview",
                        "reason": "ExpressionOfInterest",
                        "title": f"{partner['name']} sent an EOI ({document['reference']})",
                        "requestedBy": partner["name"],
                        "dueAt": None,
                        "webPath": f"/sme/requests?open={request['id']}",
                        "organizationId": ORGANIZATION["id"],
                        "organizationName": ORGANIZATION["name"],
                        "isCurrentOrganization": True,
                    })
    counts = {
        "pendingSubmission": 0,
        "pendingReview": sum(item["status"] == "PendingReview" for item in items),
        "pendingApproval": sum(item["status"] == "PendingApproval" for item in items),
    }
    return {
        "message": "Dashboard action items retrieved successfully",
        "data": {"activeOrganizationId": ORGANIZATION["id"], "counts": counts, "items": items},
    }


def wallet(store: BoardStore) -> Dict[str, Any]:
    balance = store.wallet_balance()
    return {
        "message": "Wallet fetched successfully",
        "data": {
            "walletId": WALLET_ID,
            "balance": balance,
            "status": "ACTIVE",
            "lowBalance": balance < LOW_BALANCE_MYR,
        },
    }


def wallet_transactions(store: BoardStore) -> Dict[str, Any]:
    data = [
        {"id": index + 1, "walletId": WALLET_ID, "module": "GreenReady", **entry}
        for index, entry in enumerate(store.wallet_ledger)
    ][::-1]
    return {
        "success": True,
        "message": "Wallet transactions fetched successfully",
        "data": data,
        "meta": {"page": 1, "limit": len(data), "total": len(data), "totalPages": 1},
    }
