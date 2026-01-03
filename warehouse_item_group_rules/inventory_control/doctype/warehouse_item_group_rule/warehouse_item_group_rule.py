import frappe
from frappe.model.document import Document
from frappe import _


class WarehouseItemGroupRule(Document):

    def validate(self):
        self.validate_unique_active_rule()
        self.validate_unique_item_groups()

    def validate_unique_active_rule(self):
        """
        Only one ACTIVE rule per Warehouse + Company
        """
        if not self.is_active:
            return

        existing = frappe.get_all(
            "Warehouse Item Group Rule",
            filters={
                "warehouse": self.warehouse,
                "company": self.company,
                "is_active": 1,
                "name": ["!=", self.name],
            },
            limit=1,
        )

        if existing:
            frappe.throw(
                _(
                    "An active Warehouse Item Group Rule already exists for "
                    "Warehouse <b>{0}</b> and Company <b>{1}</b>."
                ).format(self.warehouse, self.company)
            )

    def validate_unique_item_groups(self):
        """
        Prevent duplicate Item Groups in child table
        """
        seen = set()

        for row in self.allowed_item_group or []:
            if not row.item_group:
                continue

            if row.item_group in seen:
                frappe.throw(
                    _(
                        "Item Group <b>{0}</b> is duplicated in the Allowed Item Groups table."
                    ).format(row.item_group)
                )

            seen.add(row.item_group)
