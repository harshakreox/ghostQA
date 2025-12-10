"""
Framework Selectors - Pre-seeded Knowledge for UI Frameworks

Contains comprehensive selector patterns for major UI frameworks.
This is "Day 0" knowledge that works without any learning.
"""

from typing import Dict, List, Optional, Any


FRAMEWORK_SELECTORS: Dict[str, Dict[str, Any]] = {
    # ============================================================
    # MATERIAL UI (MUI) v5
    # ============================================================
    "material-ui": {
        "name": "Material UI",
        "version": "5.x",
        "prefix": "Mui",
        "components": {
            "button": {
                "base": ".MuiButton-root",
                "variants": {
                    "contained": ".MuiButton-contained",
                    "outlined": ".MuiButton-outlined",
                    "text": ".MuiButton-text"
                },
                "colors": {
                    "primary": ".MuiButton-containedPrimary, .MuiButton-outlinedPrimary, .MuiButton-textPrimary",
                    "secondary": ".MuiButton-containedSecondary, .MuiButton-outlinedSecondary",
                    "error": ".MuiButton-containedError",
                    "success": ".MuiButton-containedSuccess",
                    "warning": ".MuiButton-containedWarning"
                },
                "sizes": {
                    "small": ".MuiButton-sizeSmall",
                    "medium": ".MuiButton-sizeMedium",
                    "large": ".MuiButton-sizeLarge"
                },
                "states": {
                    "disabled": ".MuiButton-root.Mui-disabled",
                    "loading": ".MuiLoadingButton-loading"
                },
                "by_text": "button.MuiButton-root:has-text('{text}')",
                "by_icon": ".MuiButton-root:has(.MuiSvgIcon-root)",
                "icon_button": ".MuiIconButton-root"
            },
            "text_field": {
                "container": ".MuiTextField-root",
                "input": ".MuiInputBase-input",
                "outlined_input": ".MuiOutlinedInput-input",
                "filled_input": ".MuiFilledInput-input",
                "by_label": ".MuiFormControl-root:has(.MuiInputLabel-root:has-text('{label}')) .MuiInputBase-input",
                "by_placeholder": ".MuiInputBase-input[placeholder*='{text}']",
                "by_name": ".MuiInputBase-input[name='{name}']",
                "multiline": ".MuiInputBase-multiline textarea",
                "states": {
                    "error": ".MuiFormControl-root.Mui-error .MuiInputBase-input",
                    "disabled": ".MuiInputBase-input.Mui-disabled",
                    "focused": ".MuiInputBase-root.Mui-focused .MuiInputBase-input"
                },
                "helper_text": ".MuiFormHelperText-root",
                "error_text": ".MuiFormHelperText-root.Mui-error"
            },
            "select": {
                "trigger": ".MuiSelect-select",
                "native": "select.MuiNativeSelect-select",
                "by_label": ".MuiFormControl-root:has(.MuiInputLabel-root:has-text('{label}')) .MuiSelect-select",
                "dropdown": ".MuiMenu-paper, .MuiPopover-paper",
                "option": ".MuiMenuItem-root",
                "option_by_text": ".MuiMenuItem-root:has-text('{text}')",
                "selected_option": ".MuiMenuItem-root.Mui-selected",
                "open_sequence": [
                    {"action": "click", "selector": ".MuiSelect-select"},
                    {"action": "wait", "selector": ".MuiMenu-paper"}
                ]
            },
            "checkbox": {
                "base": ".MuiCheckbox-root",
                "input": ".MuiCheckbox-root input[type='checkbox']",
                "by_label": ".MuiFormControlLabel-root:has-text('{label}') .MuiCheckbox-root",
                "states": {
                    "checked": ".MuiCheckbox-root.Mui-checked",
                    "unchecked": ".MuiCheckbox-root:not(.Mui-checked)",
                    "indeterminate": ".MuiCheckbox-root.MuiCheckbox-indeterminate",
                    "disabled": ".MuiCheckbox-root.Mui-disabled"
                }
            },
            "radio": {
                "base": ".MuiRadio-root",
                "input": ".MuiRadio-root input[type='radio']",
                "group": ".MuiRadioGroup-root",
                "by_label": ".MuiFormControlLabel-root:has-text('{label}') .MuiRadio-root",
                "by_value": ".MuiRadio-root input[value='{value}']",
                "states": {
                    "checked": ".MuiRadio-root.Mui-checked",
                    "disabled": ".MuiRadio-root.Mui-disabled"
                }
            },
            "switch": {
                "base": ".MuiSwitch-root",
                "input": ".MuiSwitch-input",
                "thumb": ".MuiSwitch-thumb",
                "track": ".MuiSwitch-track",
                "by_label": ".MuiFormControlLabel-root:has-text('{label}') .MuiSwitch-root",
                "states": {
                    "checked": ".MuiSwitch-root.Mui-checked",
                    "disabled": ".MuiSwitch-root.Mui-disabled"
                }
            },
            "autocomplete": {
                "container": ".MuiAutocomplete-root",
                "input": ".MuiAutocomplete-input",
                "by_label": ".MuiFormControl-root:has(.MuiInputLabel-root:has-text('{label}')) .MuiAutocomplete-input",
                "dropdown": ".MuiAutocomplete-popper",
                "listbox": ".MuiAutocomplete-listbox",
                "option": ".MuiAutocomplete-option",
                "option_by_text": ".MuiAutocomplete-option:has-text('{text}')",
                "clear_button": ".MuiAutocomplete-clearIndicator",
                "loading": ".MuiAutocomplete-loading"
            },
            "dialog": {
                "container": ".MuiDialog-root",
                "paper": ".MuiDialog-paper",
                "title": ".MuiDialogTitle-root",
                "content": ".MuiDialogContent-root",
                "actions": ".MuiDialogActions-root",
                "close_button": ".MuiDialog-root button:has(.MuiSvgIcon-root[data-testid='CloseIcon'])",
                "backdrop": ".MuiBackdrop-root"
            },
            "snackbar": {
                "container": ".MuiSnackbar-root",
                "content": ".MuiSnackbarContent-root",
                "message": ".MuiSnackbarContent-message",
                "action": ".MuiSnackbarContent-action",
                "alert": ".MuiAlert-root"
            },
            "table": {
                "container": ".MuiTable-root",
                "head": ".MuiTableHead-root",
                "body": ".MuiTableBody-root",
                "row": ".MuiTableRow-root",
                "cell": ".MuiTableCell-root",
                "header_cell": ".MuiTableCell-head",
                "row_by_index": ".MuiTableBody-root .MuiTableRow-root:nth-child({index})",
                "cell_by_column": ".MuiTableRow-root .MuiTableCell-root:nth-child({col})",
                "sortable_header": ".MuiTableSortLabel-root",
                "pagination": ".MuiTablePagination-root",
                "pagination_next": ".MuiTablePagination-actions button:last-child",
                "pagination_prev": ".MuiTablePagination-actions button:first-child"
            },
            "tabs": {
                "container": ".MuiTabs-root",
                "tab": ".MuiTab-root",
                "tab_by_text": ".MuiTab-root:has-text('{text}')",
                "tab_by_index": ".MuiTab-root:nth-child({index})",
                "selected": ".MuiTab-root.Mui-selected",
                "panel": "[role='tabpanel']",
                "indicator": ".MuiTabs-indicator"
            },
            "accordion": {
                "container": ".MuiAccordion-root",
                "summary": ".MuiAccordionSummary-root",
                "details": ".MuiAccordionDetails-root",
                "expanded": ".MuiAccordion-root.Mui-expanded",
                "by_title": ".MuiAccordion-root:has(.MuiAccordionSummary-root:has-text('{title}'))"
            },
            "drawer": {
                "container": ".MuiDrawer-root",
                "paper": ".MuiDrawer-paper",
                "left": ".MuiDrawer-paperAnchorLeft",
                "right": ".MuiDrawer-paperAnchorRight",
                "backdrop": ".MuiDrawer-root .MuiBackdrop-root"
            },
            "menu": {
                "container": ".MuiMenu-root",
                "paper": ".MuiMenu-paper",
                "list": ".MuiMenu-list",
                "item": ".MuiMenuItem-root",
                "item_by_text": ".MuiMenuItem-root:has-text('{text}')",
                "divider": ".MuiDivider-root"
            },
            "chip": {
                "base": ".MuiChip-root",
                "by_text": ".MuiChip-root:has-text('{text}')",
                "delete_icon": ".MuiChip-deleteIcon",
                "clickable": ".MuiChip-clickable"
            },
            "avatar": {
                "base": ".MuiAvatar-root",
                "image": ".MuiAvatar-img",
                "group": ".MuiAvatarGroup-root"
            },
            "progress": {
                "linear": ".MuiLinearProgress-root",
                "circular": ".MuiCircularProgress-root"
            },
            "tooltip": {
                "popper": ".MuiTooltip-popper",
                "tooltip": ".MuiTooltip-tooltip"
            },
            "date_picker": {
                "input": ".MuiDatePicker-root input, .MuiPickersTextField-root input",
                "calendar_button": ".MuiInputAdornment-root button",
                "calendar": ".MuiDateCalendar-root",
                "day": ".MuiPickersDay-root",
                "day_by_date": ".MuiPickersDay-root:has-text('{date}')",
                "selected_day": ".MuiPickersDay-root.Mui-selected",
                "month_switch": ".MuiPickersCalendarHeader-switchViewButton",
                "prev_month": ".MuiPickersArrowSwitcher-button:first-child",
                "next_month": ".MuiPickersArrowSwitcher-button:last-child"
            }
        },
        "global_patterns": {
            "any_button": "button.MuiButton-root, .MuiIconButton-root",
            "any_input": ".MuiInputBase-input",
            "any_clickable": ".MuiButton-root, .MuiIconButton-root, .MuiMenuItem-root, .MuiListItemButton-root",
            "loading_indicator": ".MuiCircularProgress-root, .MuiLinearProgress-root",
            "error_state": ".Mui-error",
            "disabled_state": ".Mui-disabled",
            "focused_state": ".Mui-focused"
        }
    },

    # ============================================================
    # ANT DESIGN v5
    # ============================================================
    "ant-design": {
        "name": "Ant Design",
        "version": "5.x",
        "prefix": "ant",
        "components": {
            "button": {
                "base": ".ant-btn",
                "variants": {
                    "primary": ".ant-btn-primary",
                    "default": ".ant-btn-default",
                    "dashed": ".ant-btn-dashed",
                    "text": ".ant-btn-text",
                    "link": ".ant-btn-link"
                },
                "sizes": {
                    "large": ".ant-btn-lg",
                    "small": ".ant-btn-sm"
                },
                "states": {
                    "loading": ".ant-btn-loading",
                    "disabled": ".ant-btn[disabled]"
                },
                "by_text": ".ant-btn:has-text('{text}')",
                "icon_only": ".ant-btn-icon-only"
            },
            "input": {
                "base": ".ant-input",
                "wrapper": ".ant-input-affix-wrapper",
                "by_placeholder": ".ant-input[placeholder*='{text}']",
                "by_id": ".ant-input#{id}",
                "password": ".ant-input-password input",
                "search": ".ant-input-search input",
                "textarea": ".ant-input-textarea textarea",
                "number": ".ant-input-number input",
                "states": {
                    "error": ".ant-input-status-error",
                    "disabled": ".ant-input-disabled",
                    "focused": ".ant-input-focused"
                },
                "prefix": ".ant-input-prefix",
                "suffix": ".ant-input-suffix",
                "clear": ".ant-input-clear-icon"
            },
            "select": {
                "container": ".ant-select",
                "trigger": ".ant-select-selector",
                "search_input": ".ant-select-selection-search-input",
                "by_placeholder": ".ant-select:has(.ant-select-selection-placeholder:has-text('{text}'))",
                "dropdown": ".ant-select-dropdown",
                "option": ".ant-select-item-option",
                "option_by_text": ".ant-select-item-option:has-text('{text}')",
                "selected": ".ant-select-item-option-selected",
                "clear": ".ant-select-clear",
                "arrow": ".ant-select-arrow",
                "multiple_tag": ".ant-select-selection-item"
            },
            "checkbox": {
                "base": ".ant-checkbox",
                "wrapper": ".ant-checkbox-wrapper",
                "input": ".ant-checkbox-input",
                "by_label": ".ant-checkbox-wrapper:has-text('{label}')",
                "group": ".ant-checkbox-group",
                "states": {
                    "checked": ".ant-checkbox-checked",
                    "disabled": ".ant-checkbox-disabled",
                    "indeterminate": ".ant-checkbox-indeterminate"
                }
            },
            "radio": {
                "base": ".ant-radio",
                "wrapper": ".ant-radio-wrapper",
                "input": ".ant-radio-input",
                "by_label": ".ant-radio-wrapper:has-text('{label}')",
                "group": ".ant-radio-group",
                "button": ".ant-radio-button-wrapper",
                "states": {
                    "checked": ".ant-radio-checked",
                    "disabled": ".ant-radio-disabled"
                }
            },
            "switch": {
                "base": ".ant-switch",
                "by_label": ".ant-form-item:has(.ant-form-item-label:has-text('{label}')) .ant-switch",
                "states": {
                    "checked": ".ant-switch-checked",
                    "disabled": ".ant-switch-disabled",
                    "loading": ".ant-switch-loading"
                }
            },
            "date_picker": {
                "container": ".ant-picker",
                "input": ".ant-picker-input input",
                "by_placeholder": ".ant-picker:has(input[placeholder*='{text}'])",
                "calendar": ".ant-picker-dropdown",
                "cell": ".ant-picker-cell",
                "cell_by_date": ".ant-picker-cell[title='{date}']",
                "today": ".ant-picker-cell-today",
                "selected": ".ant-picker-cell-selected",
                "prev_month": ".ant-picker-header-prev-btn",
                "next_month": ".ant-picker-header-next-btn",
                "clear": ".ant-picker-clear",
                "range": ".ant-picker-range"
            },
            "time_picker": {
                "container": ".ant-picker-time",
                "input": ".ant-picker-time input",
                "panel": ".ant-picker-time-panel",
                "column": ".ant-picker-time-panel-column",
                "cell": ".ant-picker-time-panel-cell"
            },
            "table": {
                "container": ".ant-table",
                "wrapper": ".ant-table-wrapper",
                "head": ".ant-table-thead",
                "body": ".ant-table-tbody",
                "row": ".ant-table-row",
                "cell": ".ant-table-cell",
                "header_cell": ".ant-table-thead .ant-table-cell",
                "row_by_index": ".ant-table-tbody .ant-table-row:nth-child({index})",
                "sorter": ".ant-table-column-sorter",
                "filter": ".ant-table-filter-trigger",
                "pagination": ".ant-pagination",
                "empty": ".ant-empty",
                "loading": ".ant-table-loading"
            },
            "modal": {
                "container": ".ant-modal",
                "content": ".ant-modal-content",
                "header": ".ant-modal-header",
                "title": ".ant-modal-title",
                "body": ".ant-modal-body",
                "footer": ".ant-modal-footer",
                "close": ".ant-modal-close",
                "mask": ".ant-modal-mask",
                "confirm": ".ant-modal-confirm",
                "ok_button": ".ant-modal-footer .ant-btn-primary",
                "cancel_button": ".ant-modal-footer .ant-btn-default"
            },
            "drawer": {
                "container": ".ant-drawer",
                "content": ".ant-drawer-content",
                "header": ".ant-drawer-header",
                "body": ".ant-drawer-body",
                "footer": ".ant-drawer-footer",
                "close": ".ant-drawer-close",
                "mask": ".ant-drawer-mask"
            },
            "tabs": {
                "container": ".ant-tabs",
                "nav": ".ant-tabs-nav",
                "tab": ".ant-tabs-tab",
                "tab_by_text": ".ant-tabs-tab:has-text('{text}')",
                "active": ".ant-tabs-tab-active",
                "content": ".ant-tabs-content",
                "pane": ".ant-tabs-tabpane",
                "add_button": ".ant-tabs-nav-add"
            },
            "form": {
                "container": ".ant-form",
                "item": ".ant-form-item",
                "label": ".ant-form-item-label",
                "control": ".ant-form-item-control",
                "input_by_label": ".ant-form-item:has(.ant-form-item-label:has-text('{label}')) input",
                "error": ".ant-form-item-explain-error",
                "required": ".ant-form-item-required"
            },
            "message": {
                "container": ".ant-message",
                "notice": ".ant-message-notice",
                "content": ".ant-message-notice-content",
                "success": ".ant-message-success",
                "error": ".ant-message-error",
                "warning": ".ant-message-warning",
                "info": ".ant-message-info"
            },
            "notification": {
                "container": ".ant-notification",
                "notice": ".ant-notification-notice",
                "message": ".ant-notification-notice-message",
                "description": ".ant-notification-notice-description",
                "close": ".ant-notification-notice-close"
            },
            "dropdown": {
                "trigger": ".ant-dropdown-trigger",
                "menu": ".ant-dropdown-menu",
                "item": ".ant-dropdown-menu-item",
                "item_by_text": ".ant-dropdown-menu-item:has-text('{text}')"
            },
            "menu": {
                "container": ".ant-menu",
                "item": ".ant-menu-item",
                "item_by_text": ".ant-menu-item:has-text('{text}')",
                "submenu": ".ant-menu-submenu",
                "selected": ".ant-menu-item-selected"
            },
            "tree": {
                "container": ".ant-tree",
                "node": ".ant-tree-treenode",
                "title": ".ant-tree-node-content-wrapper",
                "switcher": ".ant-tree-switcher",
                "checkbox": ".ant-tree-checkbox",
                "selected": ".ant-tree-node-selected"
            },
            "upload": {
                "container": ".ant-upload",
                "button": ".ant-upload button, .ant-upload-select",
                "list": ".ant-upload-list",
                "item": ".ant-upload-list-item",
                "drag": ".ant-upload-drag"
            },
            "progress": {
                "line": ".ant-progress-line",
                "circle": ".ant-progress-circle",
                "text": ".ant-progress-text"
            },
            "spin": {
                "container": ".ant-spin",
                "dot": ".ant-spin-dot",
                "text": ".ant-spin-text"
            },
            "tooltip": {
                "container": ".ant-tooltip",
                "content": ".ant-tooltip-inner"
            },
            "popover": {
                "container": ".ant-popover",
                "content": ".ant-popover-content",
                "inner": ".ant-popover-inner"
            },
            "card": {
                "container": ".ant-card",
                "head": ".ant-card-head",
                "title": ".ant-card-head-title",
                "body": ".ant-card-body",
                "actions": ".ant-card-actions"
            },
            "collapse": {
                "container": ".ant-collapse",
                "panel": ".ant-collapse-item",
                "header": ".ant-collapse-header",
                "content": ".ant-collapse-content",
                "active": ".ant-collapse-item-active"
            },
            "tag": {
                "base": ".ant-tag",
                "by_text": ".ant-tag:has-text('{text}')",
                "close": ".ant-tag-close-icon",
                "checkable": ".ant-tag-checkable"
            },
            "badge": {
                "container": ".ant-badge",
                "count": ".ant-badge-count",
                "dot": ".ant-badge-dot"
            },
            "avatar": {
                "base": ".ant-avatar",
                "image": ".ant-avatar-image",
                "group": ".ant-avatar-group"
            },
            "pagination": {
                "container": ".ant-pagination",
                "item": ".ant-pagination-item",
                "prev": ".ant-pagination-prev",
                "next": ".ant-pagination-next",
                "active": ".ant-pagination-item-active",
                "page_by_number": ".ant-pagination-item:has-text('{number}')"
            }
        },
        "global_patterns": {
            "any_button": ".ant-btn",
            "any_input": ".ant-input, .ant-input-number input, .ant-picker input",
            "loading_indicator": ".ant-spin, .ant-btn-loading",
            "error_state": ".ant-form-item-has-error",
            "disabled_state": "[disabled], .ant-input-disabled, .ant-btn-disabled"
        }
    },

    # ============================================================
    # BOOTSTRAP v5
    # ============================================================
    "bootstrap": {
        "name": "Bootstrap",
        "version": "5.x",
        "prefix": "btn, form",
        "components": {
            "button": {
                "base": ".btn",
                "variants": {
                    "primary": ".btn-primary",
                    "secondary": ".btn-secondary",
                    "success": ".btn-success",
                    "danger": ".btn-danger",
                    "warning": ".btn-warning",
                    "info": ".btn-info",
                    "light": ".btn-light",
                    "dark": ".btn-dark",
                    "link": ".btn-link",
                    "outline_primary": ".btn-outline-primary",
                    "outline_secondary": ".btn-outline-secondary"
                },
                "sizes": {
                    "large": ".btn-lg",
                    "small": ".btn-sm"
                },
                "states": {
                    "active": ".btn.active",
                    "disabled": ".btn:disabled, .btn.disabled"
                },
                "by_text": ".btn:has-text('{text}')",
                "close": ".btn-close"
            },
            "input": {
                "base": ".form-control",
                "by_label": "label:has-text('{label}') + input, label:has-text('{label}') + .form-control",
                "by_placeholder": ".form-control[placeholder*='{text}']",
                "by_id": ".form-control#{id}",
                "textarea": "textarea.form-control",
                "select": ".form-select",
                "states": {
                    "valid": ".form-control.is-valid",
                    "invalid": ".form-control.is-invalid"
                },
                "feedback_valid": ".valid-feedback",
                "feedback_invalid": ".invalid-feedback",
                "floating_label": ".form-floating"
            },
            "checkbox": {
                "base": ".form-check-input[type='checkbox']",
                "wrapper": ".form-check",
                "by_label": ".form-check:has-text('{label}') .form-check-input",
                "switch": ".form-switch .form-check-input"
            },
            "radio": {
                "base": ".form-check-input[type='radio']",
                "wrapper": ".form-check",
                "by_label": ".form-check:has-text('{label}') .form-check-input"
            },
            "select": {
                "base": ".form-select",
                "by_label": "label:has-text('{label}') + .form-select",
                "option": ".form-select option",
                "option_by_text": ".form-select option:has-text('{text}')",
                "sizes": {
                    "large": ".form-select-lg",
                    "small": ".form-select-sm"
                }
            },
            "modal": {
                "container": ".modal",
                "dialog": ".modal-dialog",
                "content": ".modal-content",
                "header": ".modal-header",
                "title": ".modal-title",
                "body": ".modal-body",
                "footer": ".modal-footer",
                "close": ".btn-close, [data-bs-dismiss='modal']",
                "backdrop": ".modal-backdrop",
                "by_title": ".modal:has(.modal-title:has-text('{title}'))"
            },
            "toast": {
                "container": ".toast-container",
                "toast": ".toast",
                "header": ".toast-header",
                "body": ".toast-body",
                "close": ".btn-close[data-bs-dismiss='toast']"
            },
            "alert": {
                "base": ".alert",
                "variants": {
                    "primary": ".alert-primary",
                    "secondary": ".alert-secondary",
                    "success": ".alert-success",
                    "danger": ".alert-danger",
                    "warning": ".alert-warning",
                    "info": ".alert-info"
                },
                "dismissible": ".alert-dismissible",
                "close": ".btn-close[data-bs-dismiss='alert']"
            },
            "dropdown": {
                "toggle": ".dropdown-toggle, [data-bs-toggle='dropdown']",
                "menu": ".dropdown-menu",
                "item": ".dropdown-item",
                "item_by_text": ".dropdown-item:has-text('{text}')",
                "divider": ".dropdown-divider",
                "header": ".dropdown-header"
            },
            "navbar": {
                "container": ".navbar",
                "brand": ".navbar-brand",
                "toggler": ".navbar-toggler",
                "collapse": ".navbar-collapse",
                "nav": ".navbar-nav",
                "link": ".nav-link",
                "link_by_text": ".nav-link:has-text('{text}')"
            },
            "nav": {
                "container": ".nav",
                "item": ".nav-item",
                "link": ".nav-link",
                "tabs": ".nav-tabs",
                "pills": ".nav-pills",
                "active": ".nav-link.active"
            },
            "tabs": {
                "container": ".nav-tabs",
                "tab": ".nav-link[data-bs-toggle='tab']",
                "tab_by_text": ".nav-link[data-bs-toggle='tab']:has-text('{text}')",
                "content": ".tab-content",
                "pane": ".tab-pane",
                "active": ".tab-pane.active"
            },
            "accordion": {
                "container": ".accordion",
                "item": ".accordion-item",
                "header": ".accordion-header",
                "button": ".accordion-button",
                "body": ".accordion-body",
                "collapse": ".accordion-collapse",
                "expanded": ".accordion-button:not(.collapsed)",
                "by_title": ".accordion-item:has(.accordion-button:has-text('{title}'))"
            },
            "card": {
                "container": ".card",
                "header": ".card-header",
                "body": ".card-body",
                "title": ".card-title",
                "text": ".card-text",
                "footer": ".card-footer",
                "img": ".card-img, .card-img-top, .card-img-bottom"
            },
            "table": {
                "container": ".table",
                "head": "thead",
                "body": "tbody",
                "row": "tr",
                "header_cell": "th",
                "cell": "td",
                "row_by_index": "tbody tr:nth-child({index})",
                "striped": ".table-striped",
                "hover": ".table-hover"
            },
            "pagination": {
                "container": ".pagination",
                "item": ".page-item",
                "link": ".page-link",
                "active": ".page-item.active",
                "disabled": ".page-item.disabled",
                "prev": ".page-item:first-child .page-link",
                "next": ".page-item:last-child .page-link"
            },
            "progress": {
                "container": ".progress",
                "bar": ".progress-bar"
            },
            "spinner": {
                "border": ".spinner-border",
                "grow": ".spinner-grow"
            },
            "offcanvas": {
                "container": ".offcanvas",
                "header": ".offcanvas-header",
                "title": ".offcanvas-title",
                "body": ".offcanvas-body",
                "close": ".btn-close[data-bs-dismiss='offcanvas']",
                "backdrop": ".offcanvas-backdrop"
            },
            "collapse": {
                "trigger": "[data-bs-toggle='collapse']",
                "content": ".collapse",
                "show": ".collapse.show"
            },
            "badge": {
                "base": ".badge",
                "variants": {
                    "primary": ".badge.bg-primary",
                    "secondary": ".badge.bg-secondary",
                    "success": ".badge.bg-success",
                    "danger": ".badge.bg-danger"
                },
                "pill": ".rounded-pill"
            }
        },
        "global_patterns": {
            "any_button": ".btn, button",
            "any_input": ".form-control, .form-select",
            "loading_indicator": ".spinner-border, .spinner-grow",
            "error_state": ".is-invalid",
            "success_state": ".is-valid",
            "disabled_state": ":disabled, .disabled"
        }
    },

    # ============================================================
    # CHAKRA UI v2
    # ============================================================
    "chakra-ui": {
        "name": "Chakra UI",
        "version": "2.x",
        "prefix": "chakra",
        "components": {
            "button": {
                "base": ".chakra-button, button[class*='chakra-button']",
                "by_text": ".chakra-button:has-text('{text}')",
                "variants": {
                    "solid": ".chakra-button[data-variant='solid']",
                    "outline": ".chakra-button[data-variant='outline']",
                    "ghost": ".chakra-button[data-variant='ghost']",
                    "link": ".chakra-button[data-variant='link']"
                },
                "states": {
                    "loading": ".chakra-button[data-loading]",
                    "disabled": ".chakra-button:disabled"
                },
                "icon_button": ".chakra-button[aria-label]"
            },
            "input": {
                "base": ".chakra-input, input[class*='chakra-input']",
                "by_placeholder": ".chakra-input[placeholder*='{text}']",
                "by_aria_label": ".chakra-input[aria-label*='{label}']",
                "group": ".chakra-input__group",
                "left_element": ".chakra-input__left-element",
                "right_element": ".chakra-input__right-element",
                "states": {
                    "invalid": ".chakra-input[aria-invalid='true']",
                    "disabled": ".chakra-input:disabled"
                }
            },
            "select": {
                "base": ".chakra-select, select[class*='chakra-select']",
                "by_placeholder": ".chakra-select:has(option[value='']:has-text('{text}'))",
                "option": ".chakra-select option",
                "option_by_text": ".chakra-select option:has-text('{text}')"
            },
            "checkbox": {
                "base": ".chakra-checkbox",
                "input": ".chakra-checkbox__input",
                "control": ".chakra-checkbox__control",
                "by_label": ".chakra-checkbox:has-text('{label}')",
                "states": {
                    "checked": ".chakra-checkbox[data-checked]",
                    "disabled": ".chakra-checkbox[data-disabled]"
                }
            },
            "radio": {
                "base": ".chakra-radio",
                "input": ".chakra-radio__input",
                "control": ".chakra-radio__control",
                "group": ".chakra-radio-group",
                "by_label": ".chakra-radio:has-text('{label}')",
                "states": {
                    "checked": ".chakra-radio[data-checked]"
                }
            },
            "switch": {
                "base": ".chakra-switch",
                "input": ".chakra-switch__input",
                "track": ".chakra-switch__track",
                "thumb": ".chakra-switch__thumb",
                "by_label": ".chakra-form-control:has(label:has-text('{label}')) .chakra-switch",
                "states": {
                    "checked": ".chakra-switch[data-checked]"
                }
            },
            "modal": {
                "overlay": ".chakra-modal__overlay",
                "content": ".chakra-modal__content",
                "header": ".chakra-modal__header",
                "body": ".chakra-modal__body",
                "footer": ".chakra-modal__footer",
                "close_button": ".chakra-modal__close-btn"
            },
            "drawer": {
                "overlay": ".chakra-modal__overlay",
                "content": ".chakra-modal__content",
                "header": ".chakra-modal__header",
                "body": ".chakra-modal__body",
                "close_button": ".chakra-modal__close-btn"
            },
            "menu": {
                "button": ".chakra-menu__menu-button",
                "list": ".chakra-menu__menu-list",
                "item": ".chakra-menu__menuitem",
                "item_by_text": ".chakra-menu__menuitem:has-text('{text}')",
                "divider": ".chakra-menu__divider"
            },
            "tabs": {
                "container": ".chakra-tabs",
                "list": ".chakra-tabs__tablist",
                "tab": ".chakra-tabs__tab",
                "tab_by_text": ".chakra-tabs__tab:has-text('{text}')",
                "panels": ".chakra-tabs__tabpanels",
                "panel": ".chakra-tabs__tabpanel",
                "selected": ".chakra-tabs__tab[aria-selected='true']"
            },
            "accordion": {
                "container": ".chakra-accordion",
                "item": ".chakra-accordion__item",
                "button": ".chakra-accordion__button",
                "panel": ".chakra-accordion__panel",
                "expanded": ".chakra-accordion__button[aria-expanded='true']"
            },
            "toast": {
                "container": ".chakra-toast",
                "alert": ".chakra-alert",
                "close_button": ".chakra-toast button[aria-label='Close']"
            },
            "alert": {
                "container": ".chakra-alert",
                "icon": ".chakra-alert__icon",
                "title": ".chakra-alert__title",
                "description": ".chakra-alert__desc"
            },
            "form": {
                "control": ".chakra-form-control",
                "label": ".chakra-form__label",
                "helper": ".chakra-form__helper-text",
                "error": ".chakra-form__error-message",
                "input_by_label": ".chakra-form-control:has(.chakra-form__label:has-text('{label}')) input"
            },
            "table": {
                "container": ".chakra-table__container",
                "table": ".chakra-table",
                "head": "thead",
                "body": "tbody",
                "row": "tr",
                "header_cell": "th",
                "cell": "td"
            },
            "spinner": {
                "base": ".chakra-spinner"
            },
            "skeleton": {
                "base": ".chakra-skeleton"
            },
            "tooltip": {
                "container": ".chakra-tooltip"
            },
            "popover": {
                "trigger": ".chakra-popover__trigger",
                "content": ".chakra-popover__content",
                "header": ".chakra-popover__header",
                "body": ".chakra-popover__body",
                "close_button": ".chakra-popover__close-btn"
            },
            "tag": {
                "container": ".chakra-tag",
                "label": ".chakra-tag__label",
                "close_button": ".chakra-tag__close-button"
            },
            "avatar": {
                "container": ".chakra-avatar",
                "image": ".chakra-avatar__img",
                "group": ".chakra-avatar__group"
            },
            "badge": {
                "base": ".chakra-badge"
            }
        },
        "global_patterns": {
            "any_button": ".chakra-button",
            "any_input": ".chakra-input, .chakra-select, .chakra-textarea",
            "loading_indicator": ".chakra-spinner, .chakra-skeleton",
            "error_state": "[aria-invalid='true']",
            "disabled_state": ":disabled, [data-disabled]"
        }
    },

    # ============================================================
    # TAILWIND CSS (Headless UI patterns)
    # ============================================================
    "tailwind": {
        "name": "Tailwind CSS",
        "version": "3.x",
        "note": "Tailwind uses utility classes, so selectors rely on semantic HTML, ARIA, and data attributes",
        "components": {
            "button": {
                "by_text": "button:has-text('{text}')",
                "by_type": "button[type='{type}']",
                "submit": "button[type='submit'], input[type='submit']",
                "by_aria_label": "button[aria-label*='{label}']",
                "icon_button": "button:has(svg)"
            },
            "input": {
                "by_label": "label:has-text('{label}') + input, label:has-text('{label}') input",
                "by_placeholder": "input[placeholder*='{text}']",
                "by_name": "input[name='{name}']",
                "by_type": "input[type='{type}']",
                "email": "input[type='email']",
                "password": "input[type='password']",
                "search": "input[type='search']",
                "textarea": "textarea"
            },
            "select": {
                "native": "select",
                "by_label": "label:has-text('{label}') + select, label:has-text('{label}') select",
                "option": "select option",
                "option_by_text": "select option:has-text('{text}')",
                "headless_trigger": "[data-headlessui-state] button, button[aria-haspopup='listbox']",
                "headless_options": "[role='listbox'] [role='option']",
                "headless_option_by_text": "[role='option']:has-text('{text}')"
            },
            "checkbox": {
                "base": "input[type='checkbox']",
                "by_label": "label:has-text('{label}') input[type='checkbox']"
            },
            "radio": {
                "base": "input[type='radio']",
                "by_label": "label:has-text('{label}') input[type='radio']",
                "headless_group": "[role='radiogroup']",
                "headless_option": "[role='radio']"
            },
            "switch": {
                "headless": "button[role='switch']",
                "by_label": "label:has-text('{label}') ~ button[role='switch']",
                "checked": "button[role='switch'][aria-checked='true']"
            },
            "modal": {
                "headless": "[role='dialog']",
                "panel": "[role='dialog'] > div",
                "title": "[role='dialog'] [id*='title']",
                "close_button": "[role='dialog'] button:has-text('Close'), [role='dialog'] button[aria-label='Close']"
            },
            "dropdown": {
                "headless_trigger": "button[aria-haspopup='menu']",
                "headless_menu": "[role='menu']",
                "headless_item": "[role='menuitem']",
                "headless_item_by_text": "[role='menuitem']:has-text('{text}')"
            },
            "tabs": {
                "headless_list": "[role='tablist']",
                "headless_tab": "[role='tab']",
                "headless_tab_by_text": "[role='tab']:has-text('{text}')",
                "headless_panel": "[role='tabpanel']",
                "selected": "[role='tab'][aria-selected='true']"
            },
            "accordion": {
                "headless_trigger": "button[aria-expanded]",
                "headless_panel": "[aria-labelledby]",
                "expanded": "button[aria-expanded='true']"
            },
            "combobox": {
                "headless_input": "[role='combobox']",
                "headless_options": "[role='listbox']",
                "headless_option": "[role='option']"
            },
            "popover": {
                "headless_trigger": "button[aria-haspopup='dialog']",
                "headless_panel": "[data-headlessui-state] > div"
            }
        },
        "global_patterns": {
            "any_button": "button, [role='button'], a.btn",
            "any_input": "input, textarea, select",
            "any_clickable": "button, a, [role='button'], [onclick]",
            "loading_indicator": "[aria-busy='true'], .animate-spin",
            "disabled_state": ":disabled, [aria-disabled='true']",
            "by_data_testid": "[data-testid='{id}']",
            "by_aria_label": "[aria-label*='{label}']"
        }
    }
}


# ============================================================
# UNIVERSAL PATTERNS (Work across all frameworks)
# ============================================================
UNIVERSAL_PATTERNS = {
    "buttons": {
        "by_text": [
            "button:has-text('{text}')",
            "[role='button']:has-text('{text}')",
            "a:has-text('{text}')",
            "input[type='submit'][value*='{text}']",
            "input[type='button'][value*='{text}']"
        ],
        "by_type": {
            "submit": "button[type='submit'], input[type='submit']",
            "reset": "button[type='reset'], input[type='reset']",
            "button": "button[type='button'], button:not([type])"
        },
        "by_aria": "button[aria-label*='{label}'], [role='button'][aria-label*='{label}']",
        "by_testid": "button[data-testid='{id}'], [data-testid='{id}']",
        "close_buttons": [
            "button[aria-label='Close']",
            "button[aria-label='close']",
            "button:has-text('Close')",
            "button:has-text('×')",
            ".close-button",
            ".btn-close"
        ]
    },
    "inputs": {
        "by_label": [
            "label:has-text('{label}') + input",
            "label:has-text('{label}') input",
            "input[aria-label*='{label}']",
            "[aria-labelledby]:has-text('{label}') input",
            ".form-group:has(label:has-text('{label}')) input"
        ],
        "by_placeholder": [
            "input[placeholder*='{text}']",
            "textarea[placeholder*='{text}']"
        ],
        "by_type": {
            "email": "input[type='email']",
            "password": "input[type='password']",
            "text": "input[type='text'], input:not([type])",
            "number": "input[type='number']",
            "tel": "input[type='tel']",
            "url": "input[type='url']",
            "search": "input[type='search'], [role='searchbox']",
            "date": "input[type='date']",
            "file": "input[type='file']"
        },
        "by_name": "input[name='{name}'], textarea[name='{name}'], select[name='{name}']",
        "by_id": "#{id}"
    },
    "links": {
        "by_text": "a:has-text('{text}')",
        "by_href": "a[href*='{href}']",
        "by_title": "a[title*='{title}']"
    },
    "common_actions": {
        "login": [
            "button:has-text('Log in')",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
            "button:has-text('Sign In')",
            "input[type='submit'][value*='Log']",
            "input[type='submit'][value*='Sign']"
        ],
        "logout": [
            "button:has-text('Log out')",
            "button:has-text('Logout')",
            "button:has-text('Sign out')",
            "a:has-text('Log out')",
            "a:has-text('Sign out')"
        ],
        "submit": [
            "button:has-text('Submit')",
            "button[type='submit']",
            "input[type='submit']"
        ],
        "save": [
            "button:has-text('Save')",
            "button:has-text('Update')",
            "button:has-text('Apply')"
        ],
        "cancel": [
            "button:has-text('Cancel')",
            "button:has-text('Close')",
            "button:has-text('Dismiss')"
        ],
        "delete": [
            "button:has-text('Delete')",
            "button:has-text('Remove')",
            "button[aria-label*='delete']"
        ],
        "edit": [
            "button:has-text('Edit')",
            "button[aria-label*='edit']",
            "a:has-text('Edit')"
        ],
        "add": [
            "button:has-text('Add')",
            "button:has-text('Create')",
            "button:has-text('New')"
        ],
        "search": [
            "button:has-text('Search')",
            "button[type='submit']:has(svg)",
            "input[type='search'] + button"
        ],
        "next": [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button[aria-label*='next']"
        ],
        "previous": [
            "button:has-text('Previous')",
            "button:has-text('Back')",
            "button[aria-label*='previous']",
            "button[aria-label*='back']"
        ],
        "confirm": [
            "button:has-text('Confirm')",
            "button:has-text('OK')",
            "button:has-text('Yes')"
        ]
    },
    "form_elements": {
        "email_field": [
            "input[type='email']",
            "input[name*='email']",
            "input[placeholder*='email']",
            "input[autocomplete='email']"
        ],
        "password_field": [
            "input[type='password']",
            "input[name*='password']",
            "input[autocomplete*='password']"
        ],
        "username_field": [
            "input[name*='username']",
            "input[name*='user']",
            "input[placeholder*='username']",
            "input[autocomplete='username']"
        ],
        "search_field": [
            "input[type='search']",
            "input[name*='search']",
            "input[placeholder*='search']",
            "[role='searchbox']"
        ]
    },
    "navigation": {
        "main_nav": "nav, [role='navigation']",
        "menu": "[role='menu'], .menu, .nav",
        "menu_item": "[role='menuitem'], .menu-item, .nav-item",
        "breadcrumb": "[aria-label*='breadcrumb'], .breadcrumb",
        "pagination": "[aria-label*='pagination'], .pagination"
    },
    "dialogs": {
        "any_dialog": "[role='dialog'], [role='alertdialog'], .modal",
        "dialog_close": "[role='dialog'] button[aria-label*='close'], .modal .close, .modal-close"
    },
    "tables": {
        "any_table": "table, [role='table'], [role='grid']",
        "header": "thead, [role='rowgroup']:first-child",
        "body": "tbody, [role='rowgroup']:last-child",
        "row": "tr, [role='row']",
        "cell": "td, th, [role='cell'], [role='columnheader']"
    },
    "loading_states": {
        "spinner": ".spinner, .loading, [aria-busy='true'], .animate-spin",
        "skeleton": ".skeleton, [aria-hidden='true'][class*='skeleton']",
        "progress": "progress, [role='progressbar']"
    },
    "messages": {
        "error": ".error, [role='alert'], .alert-danger, .alert-error",
        "success": ".success, .alert-success",
        "warning": ".warning, .alert-warning",
        "info": ".info, .alert-info"
    }
}


def get_framework_selectors(framework: str) -> Optional[Dict]:
    """Get selector patterns for a specific framework"""
    return FRAMEWORK_SELECTORS.get(framework)


def get_component_selector(
    framework: str,
    component: str,
    variant: Optional[str] = None,
    text: Optional[str] = None,
    label: Optional[str] = None
) -> Optional[str]:
    """
    Get a selector for a specific component

    Args:
        framework: Framework name (material-ui, ant-design, etc.)
        component: Component name (button, input, select, etc.)
        variant: Optional variant (primary, outlined, etc.)
        text: Optional text content to match
        label: Optional label to match

    Returns:
        Selector string or None
    """
    fw = FRAMEWORK_SELECTORS.get(framework)
    if not fw:
        return None

    comp = fw.get("components", {}).get(component)
    if not comp:
        return None

    # Try specific variant first
    if variant and "variants" in comp:
        selector = comp["variants"].get(variant)
        if selector:
            return selector

    # Try by_text if text provided
    if text and "by_text" in comp:
        return comp["by_text"].replace("{text}", text)

    # Try by_label if label provided
    if label and "by_label" in comp:
        return comp["by_label"].replace("{label}", label)

    # Return base selector
    return comp.get("base")


def get_universal_selector(
    category: str,
    action: Optional[str] = None,
    text: Optional[str] = None,
    label: Optional[str] = None
) -> List[str]:
    """
    Get universal selectors that work across frameworks

    Args:
        category: Category (buttons, inputs, common_actions, etc.)
        action: Optional action name (login, submit, etc.)
        text: Optional text to substitute
        label: Optional label to substitute

    Returns:
        List of selector strings
    """
    cat = UNIVERSAL_PATTERNS.get(category, {})

    if action:
        selectors = cat.get(action, [])
    elif "by_text" in cat and text:
        selectors = cat["by_text"]
    elif "by_label" in cat and label:
        selectors = cat["by_label"]
    else:
        return []

    # Substitute placeholders
    result = []
    for sel in selectors:
        if text:
            sel = sel.replace("{text}", text)
        if label:
            sel = sel.replace("{label}", label)
        result.append(sel)

    return result
