"""
Generic Step Definition Library
Maps Gherkin steps to executable Playwright/Selenium actions using regex patterns
NO AI REQUIRED AT RUNTIME
"""

import re
from typing import Dict, Callable, Optional, Any, Tuple
from playwright.sync_api import Page, expect
from test_data_resolver import get_resolver, configure_resolver, resolve_test_value


class StepDefinitionLibrary:
    """
    Library of generic step definitions that map Gherkin text to executable actions.
    Uses regex patterns to match natural language steps to browser automation.
    """
    
    def __init__(self, page: Page, base_url: str = ""):
        self.page = page
        self.base_url = base_url
        self.context = {}  # Store variables across steps
        
        # Register all step definitions
        self.step_definitions = self._register_steps()
    
    def _register_steps(self) -> Dict[str, Callable]:
        """Register all step definition patterns"""
        return {
            # ============ NAVIGATION ============
            r"I (?:am on|navigate to|visit|go to) the (.+) page": self.navigate_to_page,
            r"I open the application": self.open_application,
            r"I (?:am on|visit) \"(.+)\"": self.navigate_to_url,
            r"I refresh the page": self.refresh_page,
            r"I go back": self.go_back,
            
            # ============ AUTHENTICATION ============
            r"I am (?:a )?(?:an )?(.+) user": self.set_user_type,
            r"I am logged in(?:to the application)?": self.verify_logged_in,
            r"I am not logged in(?:to the application)?": self.verify_not_logged_in,
            r"I log(?:in|ged) in with username \"(.+)\" and password \"(.+)\"": self.login_with_credentials,
            r"I log out": self.logout,
            
            # ============ CLICKING ============
            r"I click (?:on )?the \"(.+)\" (?:button|link|element|option|item|menu item|app)": self.click_element_by_text,
            r"I click (?:on )?\"(.+)\"": self.click_element_by_text,
            r"I click the (.+) button": self.click_button,
            r"I select \"(.+)\" from the (.+) (?:menu|dropdown|list)": self.select_from_dropdown,
            
            # ============ TYPING / INPUT ============
            r"I enter \"(.+)\" in(?:to)? the (.+) (?:field|input|textbox)": self.type_in_field,
            r"I type \"(.+)\" in(?:to)? (.+)": self.type_in_field,
            r"I fill (?:in )?the (.+) (?:field )?with \"(.+)\"": self.fill_field,
            r"I clear the (.+) field": self.clear_field,
            
            # ============ CHECKBOXES / RADIO ============
            r"I check the \"(.+)\" checkbox": self.check_checkbox,
            r"I uncheck the \"(.+)\" checkbox": self.uncheck_checkbox,
            r"I select the \"(.+)\" radio button": self.select_radio,
            
            # ============ VISIBILITY ASSERTIONS ============
            r"I should see (?:a |an )?(?:section|element|button|page|menu item|option) (?:titled |labeled |called |named )?\"(.+)\"": self.assert_visible_by_text,
            r"I should see \"(.+)\"": self.assert_visible_by_text,
            r"the \"(.+)\" (?:should|is) (?:be )?(?:visible|displayed|shown)": self.assert_visible_by_text,
            r"the (.+) section (?:should|is) (?:be )?(?:visible|displayed)": self.assert_section_visible,
            r"I should not see \"(.+)\"": self.assert_not_visible_by_text,
            
            # ============ STATE ASSERTIONS ============
            r"the \"(.+)\" (?:should )?(?:be )?(?:appears? as )?(?:active|highlighted)": self.assert_element_active,
            r"the \"(.+)\" (?:should )?(?:be )?clickable": self.assert_clickable,
            r"the \"(.+)\" (?:should )?(?:be )?disabled": self.assert_disabled,
            r"the \"(.+)\" (?:should )?(?:be )?enabled": self.assert_enabled,
            
            # ============ TEXT ASSERTIONS ============
            r"I should see (?:the )?text \"(.+)\"": self.assert_text_visible,
            r"the page (?:should )?contain(?:s)? \"(.+)\"": self.assert_text_visible,
            r"I should see an? (.+) message": self.assert_message_type,
            r"I should see an? (.+) message (?:indicating|stating|that says) (?:that )?\"(.+)\"": self.assert_specific_message,
            
            # ============ URL ASSERTIONS ============
            r"I should be (?:on|redirected to) the (.+) page": self.assert_on_page,
            r"the URL should (?:be|contain) \"(.+)\"": self.assert_url_contains,
            
            # ============ APPLICATION STATE ============
            r"the (.+) (?:should|is) available": self.assert_element_available,
            r"I have (.+) in the (.+) system": self.setup_test_data,
            r"I have no (.+) in the \"(.+)\" system": self.setup_empty_state,
            r"the (.+) service is experiencing technical difficulties": self.simulate_service_error,
            
            # ============ MENU / NAVIGATION ============
            r"the (.+) menu(?: section)? is (?:visible|displayed)": self.assert_menu_visible,
            r"the (.+) menu is collapsed": self.assert_menu_collapsed,
            r"I (?:click|expand) the menu expand button": self.expand_menu,
            r"I view the (.+) menu options": self.view_menu_options,
            
            # ============ LOADING / WAITING ============
            r"the (.+) (?:should )?(?:open|load)(?:s)?(?: successfully)?": self.wait_for_load,
            r"the (.+) (?:should )?(?:be )?fully loaded": self.wait_for_full_load,
            r"I wait (?:for )?(\d+) seconds?": self.wait_seconds,
            
            # ============ LISTS / TABLES ============
            r"I should see (?:my )?(.+) listed in the \"(.+)\" section": self.assert_items_in_section,
            r"each (.+) should display (.+)": self.assert_list_item_properties,
            r"the (.+) should be (.+)": self.assert_element_property,
            
            # ============ EMPTY STATES ============
            r"I should see an empty state message": self.assert_empty_state,
            r"the empty state message should (.+)": self.assert_empty_state_content,
        }
    
    # ==================== IMPLEMENTATION METHODS ====================
    
    def navigate_to_page(self, page_name: str) -> None:
        """Navigate to a named page"""
        page_map = {
            "login": f"{self.base_url}/login",
            "home": f"{self.base_url}/",
            "dashboard": f"{self.base_url}/dashboard",
            "recruit": f"{self.base_url}/recruit",
        }
        url = page_map.get(page_name.lower(), f"{self.base_url}/{page_name.lower()}")
        self.page.goto(url)
    
    def open_application(self) -> None:
        """Open the base application URL"""
        self.page.goto(self.base_url)
    
    def navigate_to_url(self, url: str) -> None:
        """Navigate to a specific URL"""
        if not url.startswith("http"):
            url = f"{self.base_url}/{url}"
        self.page.goto(url)
    
    def refresh_page(self) -> None:
        """Refresh the current page"""
        self.page.reload()
    
    def go_back(self) -> None:
        """Navigate back in browser history"""
        self.page.go_back()
    
    def set_user_type(self, user_type: str) -> None:
        """Set user type in context (for conditional logic)"""
        self.context['user_type'] = user_type
    
    def verify_logged_in(self) -> None:
        """Verify user is logged in"""
        # Check for common logged-in indicators
        try:
            self.page.wait_for_selector('[data-testid="user-menu"], .user-profile, #logout-button', timeout=5000)
        except:
            raise AssertionError("User does not appear to be logged in")
    
    def verify_not_logged_in(self) -> None:
        """Verify user is not logged in"""
        # Check for login button/form
        try:
            self.page.wait_for_selector('[data-testid="login-form"], #login-button, .login-form', timeout=5000)
        except:
            raise AssertionError("User appears to be logged in")
    
    def login_with_credentials(self, username: str, password: str) -> None:
        """Perform login with credentials"""
        self.page.fill('input[name="username"], input[type="email"], #username', username)
        self.page.fill('input[name="password"], input[type="password"], #password', password)
        self.page.click('button[type="submit"], #login-button, .login-button')
    
    def logout(self) -> None:
        """Perform logout"""
        self.page.click('[data-testid="logout"], #logout-button, .logout-button')
    
    def click_element_by_text(self, text: str) -> None:
        """Click an element containing specific text"""
        # Try multiple strategies
        selectors = [
            f'button:has-text("{text}")',
            f'a:has-text("{text}")',
            f'[role="button"]:has-text("{text}")',
            f'//*[contains(text(), "{text}")]',
            f'text="{text}"',
        ]
        
        for selector in selectors:
            try:
                self.page.click(selector, timeout=2000)
                return
            except:
                continue
        
        raise Exception(f"Could not find clickable element with text: {text}")
    
    def click_button(self, button_name: str) -> None:
        """Click a button by name/label"""
        self.click_element_by_text(button_name)
    
    def select_from_dropdown(self, option: str, dropdown_name: str) -> None:
        """Select an option from a dropdown"""
        # Find dropdown by label
        label = self.page.locator(f'label:has-text("{dropdown_name}")')
        dropdown_id = label.get_attribute('for')
        
        if dropdown_id:
            self.page.select_option(f'#{dropdown_id}', label=option)
        else:
            # Try to find select nearby
            self.page.select_option(f'select:near(:text("{dropdown_name}"))', label=option)
    

    def _simulate_real_typing(self, locator, value: str) -> bool:
        """
        Simulate REAL user typing behavior to trigger proper form validation.

        THIS IS THE KEY DIFFERENCE vs fill():
        - fill() sets value directly, may not trigger React/Vue/Angular change events
        - This method clicks, types char-by-char, tabs out - exactly like a human

        Steps:
        1. Wait for element to be visible and stable
        2. Click to focus the field (triggers focus event)
        3. Select all existing content (Ctrl+A)
        4. Type each character with delay (triggers input/change events)
        5. Tab out to trigger blur/validation
        """
        try:
            # Step 0: WAIT for element to be visible and stable FIRST!
            locator.wait_for(state="visible", timeout=5000)
            self.page.wait_for_timeout(200)  # Extra buffer for any animations
            
            # Step 1: Click to focus - CRITICAL for React/Vue/Angular forms!
            locator.click(timeout=2000)

            # Step 2: Wait for focus to register
            self.page.wait_for_timeout(150)

            # Step 3: Clear existing content using keyboard
            # This triggers proper change events that frameworks expect
            locator.press("Control+a")
            self.page.wait_for_timeout(100)

            # Step 4: Type the value CHARACTER BY CHARACTER
            # This triggers input events for each keystroke like a real user
            # The delay allows frameworks to process each input event
            if value:
                locator.press_sequentially(value, delay=50)  # Slower typing for reliability
            else:
                # If clearing, just press backspace/delete
                locator.press("Backspace")

            # Step 5: Wait then tab out to trigger blur validation
            self.page.wait_for_timeout(150)
            locator.press("Tab")
            
            # Step 6: Wait for validation to complete
            self.page.wait_for_timeout(200)

            return True
        except Exception as e:
            print(f"[DEBUG] _simulate_real_typing failed: {e}")
            return False

    def type_in_field(self, value: str, field_name: str) -> None:
        """
        Type text into a field with REAL user simulation.

        This method simulates actual human typing behavior:
        - Click to focus
        - Type character by character (triggers all input events)
        - Tab out to trigger blur/validation

        This fixes issues where fill() does not trigger form validation properly
        in React/Vue/Angular applications.
        """
        print("=" * 60)
        print(f"[TYPE_IN_FIELD] Starting - field='{field_name}', raw_value='{value}'")
        print("=" * 60)
        
        # Use the resolver to get the actual value
        try:
            resolved_value, source = resolve_test_value(value, field_name)
            value = resolved_value
            print(f"[RESOLVER] Resolved to: '{value}' (source: {source})")
        except Exception as e:
            print(f"[RESOLVER ERROR] {e}")
            raise

        print(f"[DEBUG] type_in_field: field='{field_name}', value='{value}', source='{source}'")

        # Normalize field name for matching
        field_normalized = field_name.lower().replace(" ", "")

        # Strategy 1: Use Playwright get_by_label (most robust for labeled fields)
        # Try exact match first to avoid ambiguous matches
        try:
            locator = self.page.get_by_label(field_name, exact=True)
            if locator.count() > 0:
                if self._simulate_real_typing(locator, value):
                    print(f"[DEBUG] SUCCESS: Filled '{field_name}' using get_by_label (exact)")
                    return
        except Exception as e:
            print(f"[DEBUG] get_by_label exact failed: {e}")

        # Strategy 2: get_by_label non-exact (only if single match)
        try:
            locator = self.page.get_by_label(field_name, exact=False)
            if locator.count() == 1:
                if self._simulate_real_typing(locator, value):
                    print(f"[DEBUG] SUCCESS: Filled '{field_name}' using get_by_label (non-exact)")
                    return
        except Exception as e:
            print(f"[DEBUG] get_by_label non-exact failed: {e}")

        # Strategy 3: Try by placeholder text (common in modern forms)
        try:
            locator = self.page.get_by_placeholder(field_name, exact=False)
            if locator.count() > 0:
                if self._simulate_real_typing(locator.first, value):
                    print(f"[DEBUG] SUCCESS: Filled '{field_name}' using get_by_placeholder")
                    return
        except Exception as e:
            print(f"[DEBUG] get_by_placeholder failed: {e}")

        # Strategy 4: Try by label element with for attribute
        try:
            label = self.page.locator(f'label:has-text("{field_name}")').first
            field_id = label.get_attribute('for', timeout=1000)
            if field_id:
                locator = self.page.locator(f'#{field_id}')
                if self._simulate_real_typing(locator, value):
                    print(f"[DEBUG] SUCCESS: Filled '{field_name}' using label[for] -> #{field_id}")
                    return
        except Exception as e:
            print(f"[DEBUG] label[for] strategy failed: {e}")

        # Strategy 5: CSS selectors with case-insensitive matching
        selectors = [
            f'input[placeholder*="{field_name}" i]',
            f'input[name*="{field_normalized}" i]',
            f'input[name*="{field_name}" i]',
            f'input[id*="{field_normalized}" i]',
            f'input[aria-label*="{field_name}" i]',
            f'textarea[placeholder*="{field_name}" i]',
            f'textarea[name*="{field_normalized}" i]',
        ]

        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.is_visible(timeout=500):
                    if self._simulate_real_typing(locator, value):
                        print(f"[DEBUG] SUCCESS: Filled '{field_name}' using selector: {selector}")
                        return
            except:
                continue

        # Strategy 6: Find by partial text match in any parent container
        try:
            locator = self.page.locator(f'input:near(:text("{field_name}"))').first
            if self._simulate_real_typing(locator, value):
                print(f"[DEBUG] SUCCESS: Filled '{field_name}' using :near selector")
                return
        except:
            pass

        print(f"[FATAL ERROR] All strategies exhausted. Could not find field: {field_name}")
        print(f"[DEBUG] Page URL: {self.page.url}")
        print(f"[DEBUG] Taking debug screenshot...")
        try:
            self.page.screenshot(path=f"debug_field_not_found_{field_name.replace(' ', '_')}.png")
        except:
            pass
        raise Exception(f"Could not find input field: {field_name}")

    
    def fill_field(self, field_name: str, value: str) -> None:
        """Fill a field with a value (reverse param order)"""
        self.type_in_field(value, field_name)
    
    def clear_field(self, field_name: str) -> None:
        """Clear a field"""
        self.type_in_field("", field_name)
    
    def check_checkbox(self, checkbox_name: str) -> None:
        """Check a checkbox"""
        checkbox = self.page.locator(f'input[type="checkbox"]:near(:text("{checkbox_name}"))').first
        checkbox.check()
    
    def uncheck_checkbox(self, checkbox_name: str) -> None:
        """Uncheck a checkbox"""
        checkbox = self.page.locator(f'input[type="checkbox"]:near(:text("{checkbox_name}"))').first
        checkbox.uncheck()
    
    def select_radio(self, radio_name: str) -> None:
        """Select a radio button"""
        radio = self.page.locator(f'input[type="radio"]:near(:text("{radio_name}"))').first
        radio.check()
    
    def assert_visible_by_text(self, text: str) -> None:
        """Assert an element with text is visible"""
        expect(self.page.locator(f'text="{text}"').first).to_be_visible()
    
    def assert_section_visible(self, section_name: str) -> None:
        """Assert a section is visible"""
        section = self.page.locator(f'[data-testid*="{section_name.lower()}"], section:has-text("{section_name}")').first
        expect(section).to_be_visible()
    
    def assert_not_visible_by_text(self, text: str) -> None:
        """Assert an element with text is not visible"""
        expect(self.page.locator(f'text="{text}"').first).not_to_be_visible()
    
    def assert_element_active(self, element_name: str) -> None:
        """Assert element is active/highlighted"""
        element = self.page.locator(f'text="{element_name}"').first
        # Check for active class or aria-current
        expect(element).to_have_class(re.compile('active|selected|current'))
    
    def assert_clickable(self, element_name: str) -> None:
        """Assert element is clickable"""
        element = self.page.locator(f'text="{element_name}"').first
        expect(element).to_be_enabled()
    
    def assert_disabled(self, element_name: str) -> None:
        """Assert element is disabled"""
        element = self.page.locator(f'text="{element_name}"').first
        expect(element).to_be_disabled()
    
    def assert_enabled(self, element_name: str) -> None:
        """Assert element is enabled"""
        element = self.page.locator(f'text="{element_name}"').first
        expect(element).to_be_enabled()
    
    def assert_text_visible(self, text: str) -> None:
        """Assert specific text is visible on page"""
        expect(self.page.locator(f'text="{text}"')).to_be_visible()
    
    def assert_message_type(self, message_type: str) -> None:
        """Assert a message of certain type is shown (error, success, etc)"""
        self.page.wait_for_selector(f'.{message_type}-message, [role="alert"]', timeout=5000)
    
    def assert_specific_message(self, message_type: str, message_text: str) -> None:
        """Assert a specific message is shown"""
        message = self.page.locator(f'.{message_type}-message:has-text("{message_text}"), [role="alert"]:has-text("{message_text}")')
        expect(message).to_be_visible()
    
    def assert_on_page(self, page_name: str) -> None:
        """Assert user is on a specific page"""
        expected_url = f"/{page_name.lower()}"
        expect(self.page).to_have_url(re.compile(expected_url))
    
    def assert_url_contains(self, url_part: str) -> None:
        """Assert URL contains a specific string"""
        expect(self.page).to_have_url(re.compile(url_part))
    
    def assert_element_available(self, element_name: str) -> None:
        """Assert element is available"""
        self.assert_visible_by_text(element_name)
    
    def setup_test_data(self, data_type: str, system: str) -> None:
        """Setup test data (this would call API to create data)"""
        # Placeholder - implement based on your needs
        self.context[f'{data_type}_created'] = True
    
    def setup_empty_state(self, data_type: str, system: str) -> None:
        """Setup empty state (clear all data)"""
        # Placeholder - implement based on your needs
        self.context[f'{data_type}_empty'] = True
    
    def simulate_service_error(self, service: str) -> None:
        """Simulate service error (for testing error handling)"""
        # This might require mocking at network level
        self.context[f'{service}_error'] = True
    
    def assert_menu_visible(self, menu_name: str) -> None:
        """Assert menu is visible"""
        menu = self.page.locator(f'[data-testid*="{menu_name.lower()}-menu"], nav:has-text("{menu_name}")')
        expect(menu.first).to_be_visible()
    
    def assert_menu_collapsed(self, menu_name: str) -> None:
        """Assert menu is collapsed"""
        menu = self.page.locator(f'[data-testid*="{menu_name.lower()}-menu"]')
        expect(menu.first).to_have_class(re.compile('collapsed|minimized'))
    
    def expand_menu(self) -> None:
        """Expand collapsed menu"""
        self.page.click('[data-testid="menu-expand"], .menu-toggle, .expand-button')
    
    def view_menu_options(self, menu_name: str) -> None:
        """View menu options"""
        self.assert_menu_visible(menu_name)
    
    def wait_for_load(self, element_name: str) -> None:
        """Wait for element to load"""
        self.page.wait_for_selector(f'text="{element_name}"', timeout=10000)
    
    def wait_for_full_load(self, element_name: str) -> None:
        """Wait for element to fully load"""
        self.page.wait_for_load_state('networkidle')
        self.wait_for_load(element_name)
    
    def wait_seconds(self, seconds: str) -> None:
        """Wait for specific number of seconds"""
        self.page.wait_for_timeout(int(seconds) * 1000)
    
    def assert_items_in_section(self, items: str, section: str) -> None:
        """Assert items are listed in a section"""
        section_elem = self.page.locator(f'text="{section}"')
        items_elem = section_elem.locator(f'text="{items}"')
        expect(items_elem.first).to_be_visible()
    
    def assert_list_item_properties(self, item_type: str, properties: str) -> None:
        """Assert list items have certain properties"""
        # This is generic - might need customization per app
        items = self.page.locator(f'[data-testid*="{item_type}"]')
        expect(items.first).to_be_visible()
    
    def assert_element_property(self, element: str, property: str) -> None:
        """Assert element has a property"""
        elem = self.page.locator(f'text="{element}"').first
        expect(elem).to_be_visible()
    
    def assert_empty_state(self) -> None:
        """Assert empty state is shown"""
        empty_state = self.page.locator('[data-testid="empty-state"], .empty-state, .no-results')
        expect(empty_state.first).to_be_visible()
    
    def assert_empty_state_content(self, expected_content: str) -> None:
        """Assert empty state contains specific content"""
        empty_state = self.page.locator(f'.empty-state:has-text("{expected_content}")')
        expect(empty_state.first).to_be_visible()
    
    # ==================== MATCHER ====================
    
    def match_and_execute(self, step_text: str) -> bool:
        """
        Match a Gherkin step text to a step definition and execute it.
        Returns True if matched and executed, False otherwise.
        """
        print(f'[MATCH] Trying to match: "{step_text}"', flush=True)
        for pattern, handler in self.step_definitions.items():
            match = re.match(pattern, step_text, re.IGNORECASE)
            if match:
                print(f'[MATCH] FOUND! Pattern: {pattern[:50]}... Handler: {handler.__name__}', flush=True)
                try:
                    # Extract captured groups and pass to handler
                    args = match.groups()
                    handler(*args)
                    return True
                except Exception as e:
                    raise Exception(f"Error executing step '{step_text}': {str(e)}")
        
        print(f'[MATCH] NO PATTERN MATCHED for: "{step_text}"', flush=True)
        return False