"""
UI Framework Component Library

Contains framework-specific knowledge for AI test case generation,
including component selectors, interaction patterns, and best practices.
"""

FRAMEWORK_LIBRARY = {
    "react": {
        "name": "React",
        "category": "core",
        "description": "JavaScript library for building user interfaces",
        "selector_strategy": ["data-testid", "aria-label", "role", "text"],
        "common_patterns": [
            "useState for form inputs",
            "useEffect for side effects",
            "Component composition",
            "Controlled components for forms"
        ],
        "testing_tips": [
            "Prefer data-testid for stable selectors",
            "Use aria-label for accessibility-focused testing",
            "Wait for state updates before assertions"
        ]
    },
    "material-ui": {
        "name": "Material UI (MUI)",
        "category": "component-library",
        "version": "v5",
        "components": {
            "Button": {
                "selectors": [".MuiButton-root", "button.MuiButton-contained", "button.MuiButton-outlined"],
                "variants": ["contained", "outlined", "text"],
                "interactions": ["click", "hover", "focus"],
                "test_attributes": ["data-testid", "aria-label"],
                "notes": "Buttons may have loading state with CircularProgress"
            },
            "TextField": {
                "selectors": [".MuiTextField-root", ".MuiInputBase-input", ".MuiOutlinedInput-input"],
                "interactions": ["type", "clear", "focus", "blur"],
                "validation": ["error state via .Mui-error", "helper text via .MuiFormHelperText-root"],
                "notes": "Use input inside the wrapper for actual typing"
            },
            "Select": {
                "selectors": [".MuiSelect-select", "[role='combobox']", ".MuiInputBase-root"],
                "interactions": ["click to open", "select option from dropdown"],
                "dropdown": ".MuiMenu-paper .MuiMenuItem-root",
                "notes": "Click the select first, then click option in dropdown portal"
            },
            "Dialog": {
                "selectors": [".MuiDialog-root", "[role='dialog']", ".MuiDialog-paper"],
                "interactions": ["open", "close", "confirm", "cancel"],
                "buttons": ".MuiDialogActions-root button",
                "notes": "Dialog appears as a portal at body level"
            },
            "Table": {
                "selectors": [".MuiTable-root", ".MuiTableRow-root", ".MuiTableCell-root"],
                "interactions": ["sort via column header", "paginate", "select row"],
                "pagination": ".MuiTablePagination-root",
                "notes": "Use nth-child or data attributes for specific rows"
            },
            "Checkbox": {
                "selectors": [".MuiCheckbox-root", "input[type='checkbox']", ".MuiCheckbox-input"],
                "interactions": ["check", "uncheck"],
                "states": [".Mui-checked", ".Mui-disabled"],
                "notes": "Click the visible checkbox, not the hidden input"
            },
            "Switch": {
                "selectors": [".MuiSwitch-root", ".MuiSwitch-input", ".MuiSwitch-switchBase"],
                "interactions": ["toggle on", "toggle off"],
                "states": [".Mui-checked"]
            },
            "Tabs": {
                "selectors": [".MuiTabs-root", ".MuiTab-root", "[role='tab']"],
                "interactions": ["click tab", "verify active via aria-selected"],
                "panel": "[role='tabpanel']"
            },
            "Snackbar": {
                "selectors": [".MuiSnackbar-root", ".MuiAlert-root"],
                "interactions": ["wait for appearance", "dismiss via close button"],
                "notes": "Auto-dismisses after timeout, appears at bottom"
            },
            "Menu": {
                "selectors": [".MuiMenu-root", ".MuiMenuItem-root", "[role='menu']"],
                "interactions": ["open via trigger", "select item", "close"],
                "notes": "Menu renders as a portal"
            },
            "Autocomplete": {
                "selectors": [".MuiAutocomplete-root", ".MuiAutocomplete-input", ".MuiAutocomplete-option"],
                "interactions": ["type to search", "select from dropdown", "clear"],
                "dropdown": ".MuiAutocomplete-popper .MuiAutocomplete-listbox"
            },
            "DatePicker": {
                "selectors": [".MuiDatePicker-root", ".MuiPickersDay-root"],
                "interactions": ["click input to open", "select date", "navigate months"],
                "notes": "Calendar renders in a portal"
            },
            "Accordion": {
                "selectors": [".MuiAccordion-root", ".MuiAccordionSummary-root", ".MuiAccordionDetails-root"],
                "interactions": ["expand", "collapse"],
                "states": [".Mui-expanded"]
            }
        },
        "selector_priority": ["data-testid", ".Mui*-root", "aria-label", "role"],
        "global_notes": [
            "MUI components often render portals for overlays",
            "Use waitFor for animations and transitions",
            "Check for .Mui-disabled before interactions"
        ]
    },
    "ant-design": {
        "name": "Ant Design",
        "category": "component-library",
        "version": "5.x",
        "components": {
            "Button": {
                "selectors": [".ant-btn", "button.ant-btn-primary", "button.ant-btn-default"],
                "variants": ["primary", "default", "dashed", "link", "text"],
                "interactions": ["click", "hover"],
                "loading": ".ant-btn-loading"
            },
            "Input": {
                "selectors": [".ant-input", ".ant-input-affix-wrapper input", "input.ant-input"],
                "interactions": ["type", "clear via .ant-input-clear-icon", "focus"],
                "validation": [".ant-input-status-error"]
            },
            "Select": {
                "selectors": [".ant-select", ".ant-select-selector", ".ant-select-selection-search-input"],
                "dropdown": ".ant-select-dropdown .ant-select-item",
                "interactions": ["click to open", "search", "select option"],
                "notes": "Dropdown renders in body as portal"
            },
            "Modal": {
                "selectors": [".ant-modal", ".ant-modal-content", ".ant-modal-wrap"],
                "interactions": ["open", "close via .ant-modal-close", "confirm via footer buttons"],
                "footer": ".ant-modal-footer button"
            },
            "Table": {
                "selectors": [".ant-table", ".ant-table-row", ".ant-table-cell"],
                "interactions": ["sort via .ant-table-column-sorter", "filter via .ant-table-filter-trigger", "paginate"],
                "pagination": ".ant-pagination"
            },
            "Form": {
                "selectors": [".ant-form", ".ant-form-item", ".ant-form-item-control-input"],
                "validation": [".ant-form-item-explain-error", ".ant-form-item-has-error"],
                "notes": "Form items wrap inputs with labels and validation"
            },
            "Checkbox": {
                "selectors": [".ant-checkbox", ".ant-checkbox-input", ".ant-checkbox-wrapper"],
                "interactions": ["check", "uncheck"],
                "states": [".ant-checkbox-checked", ".ant-checkbox-disabled"]
            },
            "Radio": {
                "selectors": [".ant-radio", ".ant-radio-wrapper", ".ant-radio-group"],
                "interactions": ["select option"],
                "states": [".ant-radio-checked"]
            },
            "DatePicker": {
                "selectors": [".ant-picker", ".ant-picker-input input", ".ant-picker-dropdown"],
                "interactions": ["click to open calendar", "select date", "navigate months"],
                "calendar": ".ant-picker-cell-inner"
            },
            "Message": {
                "selectors": [".ant-message", ".ant-message-notice", ".ant-message-notice-content"],
                "interactions": ["wait for appearance"],
                "notes": "Auto-dismisses, appears at top center"
            },
            "Notification": {
                "selectors": [".ant-notification", ".ant-notification-notice"],
                "interactions": ["wait for appearance", "close via .ant-notification-notice-close"],
                "notes": "Appears at top-right by default"
            },
            "Drawer": {
                "selectors": [".ant-drawer", ".ant-drawer-content", ".ant-drawer-body"],
                "interactions": ["open", "close via .ant-drawer-close"],
                "notes": "Slides in from side"
            },
            "Dropdown": {
                "selectors": [".ant-dropdown", ".ant-dropdown-menu", ".ant-dropdown-menu-item"],
                "interactions": ["hover or click trigger", "select menu item"]
            },
            "Tabs": {
                "selectors": [".ant-tabs", ".ant-tabs-tab", ".ant-tabs-tabpane"],
                "interactions": ["click tab"],
                "active": ".ant-tabs-tab-active"
            },
            "Tree": {
                "selectors": [".ant-tree", ".ant-tree-treenode", ".ant-tree-node-content-wrapper"],
                "interactions": ["expand via .ant-tree-switcher", "select node"]
            }
        },
        "selector_priority": ["data-testid", ".ant-*", "aria-label", "role"],
        "global_notes": [
            "Ant Design uses portals extensively for overlays",
            "Animation duration is typically 300ms",
            "Use data-testid prop for stable selectors"
        ]
    },
    "tailwind": {
        "name": "Tailwind CSS",
        "category": "utility-framework",
        "description": "Utility-first CSS framework",
        "notes": "Uses standard HTML elements with utility classes - no component-specific selectors",
        "selector_strategy": [
            "data-testid (highly recommended)",
            "aria-label",
            "Semantic HTML elements (button, input, form, nav)",
            "Text content",
            "role attributes"
        ],
        "avoid_selectors": [
            "Tailwind utility classes (bg-*, text-*, p-*, m-*) - unstable across builds",
            "Dynamic class combinations"
        ],
        "common_patterns": [
            "Utility classes for styling (bg-*, text-*, p-*, m-*, flex, grid)",
            "Responsive prefixes (sm:, md:, lg:, xl:, 2xl:)",
            "State variants (hover:, focus:, active:, disabled:)",
            "Dark mode (dark:)",
            "Group and peer modifiers"
        ],
        "testing_tips": [
            "Always add data-testid to interactive elements",
            "Use semantic HTML (button not div with onClick)",
            "Rely on accessibility attributes (aria-*, role)",
            "Test responsive behavior at different viewport sizes"
        ]
    },
    "bootstrap": {
        "name": "Bootstrap",
        "category": "css-framework",
        "version": "5.x",
        "components": {
            "Button": {
                "selectors": [".btn", "button.btn-primary", ".btn-secondary", ".btn-success"],
                "variants": ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"],
                "sizes": [".btn-lg", ".btn-sm"]
            },
            "Form": {
                "selectors": [".form-control", ".form-select", ".form-check-input"],
                "validation": [".is-valid", ".is-invalid", ".invalid-feedback", ".valid-feedback"],
                "floating": [".form-floating"]
            },
            "Modal": {
                "selectors": [".modal", ".modal-dialog", ".modal-content", ".modal-body"],
                "interactions": ["show via data-bs-toggle", "hide via .btn-close"],
                "backdrop": ".modal-backdrop"
            },
            "Card": {
                "selectors": [".card", ".card-body", ".card-header", ".card-footer", ".card-title"]
            },
            "Navbar": {
                "selectors": [".navbar", ".nav-link", ".navbar-toggler", ".navbar-collapse"],
                "interactions": ["toggle on mobile via .navbar-toggler"]
            },
            "Alert": {
                "selectors": [".alert", ".alert-dismissible"],
                "interactions": ["dismiss via .btn-close"],
                "variants": [".alert-primary", ".alert-success", ".alert-danger", ".alert-warning"]
            },
            "Dropdown": {
                "selectors": [".dropdown", ".dropdown-toggle", ".dropdown-menu", ".dropdown-item"],
                "interactions": ["click toggle to open", "select item"]
            },
            "Toast": {
                "selectors": [".toast", ".toast-header", ".toast-body"],
                "interactions": ["wait for show", "dismiss"],
                "container": ".toast-container"
            },
            "Accordion": {
                "selectors": [".accordion", ".accordion-item", ".accordion-button", ".accordion-body"],
                "interactions": ["click header to expand/collapse"],
                "states": [".show", ".collapsed"]
            },
            "Offcanvas": {
                "selectors": [".offcanvas", ".offcanvas-header", ".offcanvas-body"],
                "interactions": ["open via data-bs-toggle", "close via .btn-close"]
            },
            "Pagination": {
                "selectors": [".pagination", ".page-item", ".page-link"],
                "states": [".active", ".disabled"]
            },
            "Progress": {
                "selectors": [".progress", ".progress-bar"],
                "notes": "Width indicates progress percentage"
            }
        },
        "selector_priority": ["data-testid", "id", ".btn-*", "aria-label", "data-bs-*"],
        "global_notes": [
            "Bootstrap 5 uses vanilla JS, not jQuery",
            "Modals and dropdowns use Popper.js for positioning",
            "Use data-bs-* attributes for JS interactions"
        ]
    },
    "chakra-ui": {
        "name": "Chakra UI",
        "category": "component-library",
        "version": "2.x",
        "components": {
            "Button": {
                "selectors": [".chakra-button", "button[class*='chakra-button']"],
                "variants": ["solid", "outline", "ghost", "link"],
                "sizes": ["xs", "sm", "md", "lg"],
                "notes": "Uses CSS-in-JS, class names may vary"
            },
            "Input": {
                "selectors": [".chakra-input", "input[class*='chakra-input']"],
                "interactions": ["type", "clear", "focus"],
                "group": ".chakra-input__group"
            },
            "Modal": {
                "selectors": [".chakra-modal__content", "[role='dialog']", ".chakra-modal__body"],
                "interactions": ["open", "close via .chakra-modal__close-btn"],
                "overlay": ".chakra-modal__overlay"
            },
            "Select": {
                "selectors": [".chakra-select", "select[class*='chakra-select']"],
                "interactions": ["click to open", "select option"],
                "notes": "Uses native select or custom menu"
            },
            "Toast": {
                "selectors": [".chakra-toast", "[role='alert']", ".chakra-alert"],
                "interactions": ["wait for appearance", "close via button"],
                "notes": "Appears at bottom by default"
            },
            "Menu": {
                "selectors": [".chakra-menu__menu-list", ".chakra-menu__menuitem", "[role='menu']"],
                "interactions": ["click trigger", "select item"]
            },
            "Drawer": {
                "selectors": [".chakra-modal__content", "[role='dialog']"],
                "interactions": ["open", "close"],
                "notes": "Uses same base as Modal"
            },
            "Checkbox": {
                "selectors": [".chakra-checkbox", ".chakra-checkbox__control"],
                "interactions": ["check", "uncheck"],
                "states": ["[data-checked]"]
            },
            "Switch": {
                "selectors": [".chakra-switch", ".chakra-switch__track"],
                "interactions": ["toggle"],
                "states": ["[data-checked]"]
            },
            "Tabs": {
                "selectors": [".chakra-tabs", ".chakra-tabs__tab", ".chakra-tabs__tabpanel"],
                "interactions": ["click tab"],
                "states": ["[aria-selected='true']"]
            },
            "Accordion": {
                "selectors": [".chakra-accordion", ".chakra-accordion__button", ".chakra-accordion__panel"],
                "interactions": ["click to expand/collapse"],
                "states": ["[aria-expanded='true']"]
            },
            "Popover": {
                "selectors": [".chakra-popover__content", ".chakra-popover__body"],
                "interactions": ["trigger to open", "click outside to close"]
            }
        },
        "selector_priority": ["data-testid", "aria-label", "role", "[class*='chakra-']"],
        "global_notes": [
            "Chakra uses CSS-in-JS with Emotion",
            "Class names include 'chakra-' prefix",
            "Heavily uses aria attributes for accessibility",
            "Portals used for overlays"
        ]
    }
}


def get_framework_info(framework_id: str) -> dict:
    """Get information about a specific framework."""
    return FRAMEWORK_LIBRARY.get(framework_id, {})


def get_all_frameworks() -> list:
    """Get list of all available frameworks."""
    return [
        {
            "id": key,
            "name": value["name"],
            "category": value.get("category", "general")
        }
        for key, value in FRAMEWORK_LIBRARY.items()
    ]


def get_framework_components(framework_id: str) -> dict:
    """Get component library for a specific framework."""
    framework = FRAMEWORK_LIBRARY.get(framework_id, {})
    return framework.get("components", {})


def build_framework_context(frameworks: list, primary_framework: str = None) -> str:
    """
    Build a context string for AI prompt enhancement.

    Args:
        frameworks: List of framework IDs
        primary_framework: Optional primary framework ID

    Returns:
        Formatted string with framework context for AI prompt
    """
    if not frameworks:
        return ""

    context_parts = ["\n\nUI FRAMEWORK CONTEXT:"]
    context_parts.append("Testing Library: Playwright")

    # Get framework names
    framework_names = []
    for fw_id in frameworks:
        fw_data = FRAMEWORK_LIBRARY.get(fw_id, {})
        framework_names.append(fw_data.get("name", fw_id))

    context_parts.append(f"Frameworks Used: {', '.join(framework_names)}")

    if primary_framework:
        primary_data = FRAMEWORK_LIBRARY.get(primary_framework, {})
        context_parts.append(f"Primary Component Library: {primary_data.get('name', primary_framework)}")

    # Add component reference for each framework
    for fw_id in frameworks:
        fw_data = FRAMEWORK_LIBRARY.get(fw_id)
        if not fw_data:
            continue

        context_parts.append(f"\n{fw_data['name']}:")

        # Add selector priority
        if 'selector_priority' in fw_data:
            priority = ' > '.join(fw_data['selector_priority'])
            context_parts.append(f"  Selector Priority: {priority}")
        elif 'selector_strategy' in fw_data:
            strategy = ' > '.join(fw_data['selector_strategy'][:4])
            context_parts.append(f"  Selector Strategy: {strategy}")

        # Add key components (limit to 6 most important)
        if 'components' in fw_data:
            context_parts.append("  Key Components:")
            component_items = list(fw_data['components'].items())[:6]
            for comp_name, comp_data in component_items:
                selectors = comp_data.get('selectors', [])[:2]
                if selectors:
                    context_parts.append(f"    - {comp_name}: {', '.join(selectors)}")

        # Add testing tips if available
        if 'testing_tips' in fw_data:
            tips = fw_data['testing_tips'][:2]
            context_parts.append("  Testing Tips:")
            for tip in tips:
                context_parts.append(f"    - {tip}")

        # Add global notes if available
        if 'global_notes' in fw_data:
            notes = fw_data['global_notes'][:1]
            for note in notes:
                context_parts.append(f"  Note: {note}")

    # Add important instructions
    context_parts.append("\nSELECTOR GUIDELINES:")
    context_parts.append("- ALWAYS prefer data-testid as the primary selector when available")
    context_parts.append("- Use aria-label and role attributes for accessibility-friendly selectors")
    context_parts.append("- Reference framework-specific component selectors for reliable targeting")
    context_parts.append("- Avoid relying on dynamic/generated class names or utility classes")

    return "\n".join(context_parts)
