# -*- coding: utf-8 -*-

import frappe
from frappe import _


# ---------------------------------------------
# Request-level caches (safe per request)
# ---------------------------------------------

_RULE_CACHE = {}
_ALLOWED_GROUPS_CACHE = {}


def validate_warehouse_item_groups(doc, method=None):
    """
    Main enforcement entry point.
    Runs on before_save (soft) and before_submit (hard).
    Collects ALL violations and shows them at once.
    """

    # Global feature toggle
    if not is_feature_enabled():
        return

    # Ignore non-stock-impacting invoices
    if doc.doctype in ("Sales Invoice", "Purchase Invoice") and not doc.update_stock:
        return

    errors = []

    for idx, row in enumerate(doc.items or [], start=1):
        if not row.item_code:
            continue

        item_group = get_item_group(row.item_code)
        if not item_group:
            continue

        warehouses = get_row_warehouses(row, doc.doctype)

        for warehouse in warehouses:
            if not warehouse:
                continue

            if not is_item_group_allowed(
                warehouse=warehouse,
                item_group=item_group,
                company=doc.company,
            ):
                errors.append(
                    {
                        "row": idx,
                        "item": row.item_code,
                        "item_group": item_group,
                        "warehouse": warehouse,
                    }
                )

    if errors:
        throw_combined_error(doc, errors)


# ---------------------------------------------
# Core checks
# ---------------------------------------------


def is_item_group_allowed(warehouse, item_group, company):
    """
    Returns True if the item group is allowed in the warehouse
    according to an active rule, otherwise False.
    """
    rule = get_active_rule(warehouse, company)

    # No active rule -> allow
    if not rule:
        return True

    allowed_groups = get_allowed_item_groups(rule)
    return item_group in allowed_groups


def get_row_warehouses(row, doctype):
    """
    Detect warehouses per transaction row.
    """
    if doctype == "Stock Entry":
        return [row.s_warehouse, row.t_warehouse]

    return [row.warehouse]


# ---------------------------------------------
# Cached helpers
# ---------------------------------------------


def get_item_group(item_code):
    """
    Cached Item -> Item Group lookup (per request)
    """
    if not hasattr(frappe.local, "_item_group_cache"):
        frappe.local._item_group_cache = {}

    if item_code not in frappe.local._item_group_cache:
        frappe.local._item_group_cache[item_code] = frappe.db.get_value(
            "Item", item_code, "item_group"
        )

    return frappe.local._item_group_cache[item_code]


def get_active_rule(warehouse, company):
    """
    Cached active rule lookup per (warehouse, company)
    """
    key = (warehouse, company)

    if key not in _RULE_CACHE:
        _RULE_CACHE[key] = frappe.get_value(
            "Warehouse Item Group Rule",
            {
                "warehouse": warehouse,
                "company": company,
                "is_active": 1,
            },
            "name",
        )

    return _RULE_CACHE[key]


def get_allowed_item_groups(rule_name):
    """
    Cached allowed item groups per rule
    """
    if rule_name not in _ALLOWED_GROUPS_CACHE:
        _ALLOWED_GROUPS_CACHE[rule_name] = set(
            frappe.get_all(
                "Allowed Item Group",
                filters={"parent": rule_name},
                pluck="item_group",
            )
        )

    return _ALLOWED_GROUPS_CACHE[rule_name]


def is_feature_enabled():
    """
    Check if Warehouse Item Group Rules feature is enabled globally
    """
    return bool(
        frappe.db.get_single_value(
            "Stock Settings",
            "custom_enable_warehouse_item_group_rules",
        )
    )


# ---------------------------------------------
# Error handling
# ---------------------------------------------


def throw_combined_error(doc, errors):
    """
    Throw a single, readable error containing all violations.
    """

    lines = []
    for e in errors:
        lines.append(
            f"- Row {e['row']}: "
            f"Item <b>{e['item']}</b> "
            f"(Item Group: <b>{e['item_group']}</b>) "
            f"is not allowed in Warehouse "
            f"<b>{e['warehouse']}</b>"
        )

    message = (
        f"<b>{doc.doctype}</b> cannot be processed due to warehouse restrictions.<br><br>"
        + "<br>".join(lines)
        + "<br><br>"
        "This restriction is defined by an active Warehouse Item Group Rule.<br>"
        "Please adjust the warehouse, item, or contact your system administrator."
    )

    frappe.throw(
        message,
        title=_("Warehouse Item Group Restriction"),
    )
