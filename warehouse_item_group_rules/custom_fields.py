from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def get_custom_fields():
    """
    Custom fields required by Warehouse Item Group Rules app
    """
    return {
        "Stock Settings": [
            {
                "fieldname": "custom_item_group_rules",
                "fieldtype": "Section Break",
                "label": "Item Group Rules",
                "insert_after": "validate_material_transfer_warehouses",
            },
            {
                "fieldname": "custom_enable_warehouse_item_group_rules",
                "fieldtype": "Check",
                "label": "Enable Warehouse Item Group Rules",
                "default": 1,
                "insert_after": "custom_item_group_rules",
                "description": (
                    "If enabled, stock transactions will be validated to ensure that "
                    "only allowed Item Groups can be used in each Warehouse. "
                    "Disable this option to temporarily bypass all Item Group rules."
                ),
            },
        ]
    }
